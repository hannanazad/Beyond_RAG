"""compare40/run_qwen_rag.py -- VINE as plain RAG, answered by Qwen3.8-27B on FASTER's GPUs.

    $RETR_ENV/bin/python -u compare40/run_qwen_rag.py --kq KQ_FILE [--only SAMPLE002,SAMPLE022] [--tag qwen_v1]

Run inside a Slurm job (compare40/qwen_rag_job.slurm, submitted by run_qwen_rag.sh).
This is system 2 (run_vine_rag.py: the same evidence, GEMS-RAG's answer prompt, up to
4 images), with Qwen3.8-27B as the answer model in place of Sonnet 5.5 or Fable 5:

  1. The model: the same files the VINE parser uses (same model and revision, read from
     hprc/vine_hprc.py), copied once to this node's own disk. The job stops if the
     files hold no vision part.
  2. One vLLM server per GPU, started with VINE's own vllm_client.launch and the
     parser's flags and environment (hprc/vine_hprc.py: PARSER_SERVER and
     parser_server_env), with one difference: the vision part is ON. The parser starts
     the model with --language-model-only, which leaves the vision part out; here it is
     left in, with up to 4 images a prompt (VINE's limit) and no video.
     Memory: 0.95 of the GPU (0.90 for the parser), so that the window (prompt plus
     thinking) is as large as the GPU allows; if that runs out of memory at start, 0.90.
     The window asked for is 131,072 tokens (or the model's own maximum, if smaller); vLLM
     says how much fits, and the server is started again with that (at least 49,152).
     Every question then gets the smallest window of the servers, as the parser does.
  3. Each server is first asked what colour a small red picture is. A server that
     cannot see it is not used.
  4. The questions are shared among the servers, one at a time: each question is one run
     of run_vine_rag.py --local-server (the settings are in compare40/qwen_local.py).
     A server that stops takes no more questions; the question it was on goes to another.
  5. The servers are stopped, and all answers go into one file:
     $SCRATCH/Beyond_RAG/compare40_runs/vine_rag/answers_<tag>.jsonl
     with the settings in qwen_rag_<tag>_manifest.json next to it.
Run again, it answers only the questions that have no answer yet.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import qwen_local as ql  # noqa: E402

MAX_IMAGES = 4                 # VINE's image limit (run_vine_rag.MAX_IMAGES)
WINDOW, MIN_WINDOW = 131072, 49152
GPU_UTILS = (0.95, 0.90)
SEED = 42
READY_TIMEOUT = 5400           # as PARSER_SERVER: 90 minutes for a server to start


def say(*a) -> None:
    print(*a, flush=True)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def hprc_constant(name: str) -> str:
    """A constant of hprc/vine_hprc.py, read from its text (importing it would load VINE's
    whole pipeline), so this run uses exactly the parser's model and revision."""
    m = re.search(rf'^{name} = "([^"]+)"', (REPO / "hprc" / "vine_hprc.py").read_text(), re.M)
    assert m, f"{name} not found in hprc/vine_hprc.py"
    return m.group(1)


MODEL_ID = hprc_constant("MODEL_ID")
REVISION = hprc_constant("REVISION")
VLLM_VERSION = hprc_constant("VLLM_VERSION")
PIN_DIR = REPO / "hprc" / "pin_tuning"


def model_path() -> Path:
    p = (Path(os.environ["HF_HUB_CACHE"]) / ("models--" + MODEL_ID.replace("/", "--"))
         / "snapshots" / REVISION)
    assert (p / "config.json").exists(), f"the model is not at {p} -- run hprc/setup.sh"
    return p


def vision_part(p: Path) -> dict:
    """How much of the vision part the model files hold."""
    cfg = json.loads((p / "config.json").read_text())
    names = []
    idx = p / "model.safetensors.index.json"
    if idx.exists():
        names = list(json.loads(idx.read_text()).get("weight_map", {}))
    vis = [n for n in names if re.search(r"visual|vision", n)]
    return {"vision_config": "vision_config" in cfg, "vision_tensors": len(vis),
            "architectures": cfg.get("architectures")}


def model_max_len(p: Path) -> int:
    """The model's own longest input (max_position_embeddings), 0 if not given."""
    cfg = json.loads((p / "config.json").read_text())
    for c in (cfg.get("text_config") or {}, cfg):
        v = c.get("max_position_embeddings")
        if isinstance(v, int) and v > 0:
            return v
    return 0


def local_model_copy(src: Path, tmp: Path) -> Path:
    """The model copied once to this node's own disk (as hprc/vine_hprc.local_model_copy:
    the same bytes, checked by size); the shared copy if there is no room or it fails."""
    from concurrent.futures import ThreadPoolExecutor
    files = sorted(q for q in src.rglob("*") if q.is_file())
    size = sum(q.stat().st_size for q in files)
    dst = tmp / "model" / src.name
    try:
        tmp.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(tmp).free
        if free < size * 1.2:
            say(f"the node's own disk has {free / 1e9:.0f} GB free, the model needs {size / 1e9:.0f} GB: "
                f"the servers read it from {src}")
            return src
        say(f"copying the model to this node's own disk: {len(files)} files, {size / 1e9:.1f} GB ...")
        t0 = time.time()

        def copy_one(q: Path) -> None:
            out = dst / q.relative_to(src)
            out.parent.mkdir(parents=True, exist_ok=True)
            if not out.exists() or out.stat().st_size != q.stat().st_size:
                shutil.copyfile(q, out)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(copy_one, files))
        bad = [q.name for q in files if (dst / q.relative_to(src)).stat().st_size != q.stat().st_size]
        assert not bad, f"copied with the wrong size: {bad[:5]}"
        say(f"  copied in {time.time() - t0:.0f}s -> {dst}")
        return dst
    except Exception as e:                                                  # noqa: BLE001
        say(f"the copy to the node's own disk failed ({e!r}): the servers read the model from {src}")
        return src


def server_env(gpu: str, own: Path) -> dict:
    """As hprc/vine_hprc.parser_server_env: its GPU, its compile caches on the node's own
    disk, the tuning pin (the same kernels on every start)."""
    return {"CUDA_VISIBLE_DEVICES": gpu, "HF_HUB_OFFLINE": "1",
            "PYTHONPATH": str(PIN_DIR), "VINE_PIN_TUNING": "1",
            "VLLM_USE_FLASHINFER_SAMPLER": "0",
            "VLLM_CACHE_ROOT": str(own / "vllm"), "TRITON_CACHE_DIR": str(own / "triton"),
            "TORCHINDUCTOR_CACHE_DIR": str(own / "inductor"), "FLASHINFER_WORKSPACE_BASE": str(own)}


def with_vision(vc):
    """vllm_client.serve_command, but the whole model (vision part ON), up to MAX_IMAGES
    images a prompt and no video. Everything else as the parser's command."""
    original = vc.serve_command

    def serve_command(vllm_bin, model, served_name="parser", port=8000, max_model_len=40960,
                      gpu_memory_utilization=0.90, seed=42, language_only="flag", extra=()):
        return original(vllm_bin, model, served_name=served_name, port=port, max_model_len=max_model_len,
                        gpu_memory_utilization=gpu_memory_utilization, seed=seed, language_only="",
                        extra=list(extra) + ["--limit-mm-per-prompt",
                                             json.dumps({"image": MAX_IMAGES, "video": 0})])
    vc.serve_command = serve_command        # vllm_client.launch looks this name up when it runs
    return vc


def red_png() -> str:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (220, 20, 20)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def probe(base_url: str) -> dict:
    """Ask the server what colour a red picture is; also the same question without it, so
    the picture's share of the prompt is known."""
    import requests
    q = "What colour fills this picture? Answer with one word."

    def ask(content):
        body = {"model": MODEL_ID, "messages": [{"role": "user", "content": content}], "max_tokens": 2048,
                "seed": SEED, "temperature": 0.0, "chat_template_kwargs": {"enable_thinking": False}}
        try:
            r = requests.post(f"{base_url}/v1/chat/completions", json=body, timeout=900)
        except requests.RequestException as e:
            return {"status": "no reply", "text": repr(e)[:400]}
        if r.status_code != 200:
            return {"status": r.status_code, "text": r.text[:400]}
        d = r.json()
        msg = ((d.get("choices") or [{}])[0].get("message") or {})
        thought = msg.get("reasoning_content") or msg.get("reasoning") or ""
        return {"status": 200, "reply": (msg.get("content") or "").strip()[:200],
                "reasoning_says_red": bool(re.search(r"\bred\b", thought.lower())),
                "prompt_tokens": (d.get("usage") or {}).get("prompt_tokens")}

    img = ask([{"type": "text", "text": q},
               {"type": "image_url", "image_url": {"url": "data:image/png;base64," + red_png()}}])
    txt = ask([{"type": "text", "text": q}])
    sees = (img.get("status") == 200
            and (re.search(r"\bred\b", img.get("reply", "").lower())
                 or (not img.get("reply") and img.get("reasoning_says_red")))
            and (img.get("prompt_tokens") or 0) > (txt.get("prompt_tokens") or 0))
    return {"with_picture": img, "without_picture": txt, "sees_the_picture": sees}


def gpu_names() -> list:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [x.strip() for x in out.splitlines() if x.strip()]


def first_port(job: str) -> int:
    return 20000 + (int(job) % 400) * 10 if job.isdigit() else 20000


def read_jsonl(path: Path) -> list:
    """The lines of a .jsonl file; a line cut off (a job stopped while writing) is skipped."""
    out = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def part_files(out_dir: Path, tag: str) -> list:
    """answers_<tag>_s<N>.jsonl only (not the files of a longer tag that starts the same)."""
    rx = re.compile(rf"answers_{re.escape(tag)}_s\d+\.jsonl")
    return sorted(f for f in out_dir.glob(f"answers_{tag}_s*.jsonl") if rx.fullmatch(f.name))


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def counts(r: dict, kq_name: str) -> bool:
    """An answer of this model, from this evidence file."""
    return r.get("model_id") == MODEL_ID and r.get("kq_file") == kq_name


def merge(out_dir: Path, tag: str, ids: list, kq_name: str) -> dict:
    """All answers of this tag in one file, in question order: for each question its last
    answer that worked, else its last error (this model, this evidence file only)."""
    best = {}
    for f in part_files(out_dir, tag):
        for r in read_jsonl(f):
            if not counts(r, kq_name):
                continue
            old = best.get(r["question_id"])
            if (old is None or (r.get("status") == "ok") > (old.get("status") == "ok")
                    or ((r.get("status") == "ok") == (old.get("status") == "ok")
                        and str(r.get("completed_at")) >= str(old.get("completed_at")))):
                best[r["question_id"]] = r
    write_atomic(out_dir / f"answers_{tag}.jsonl",
                 "".join(json.dumps(best[q], ensure_ascii=False) + "\n" for q in ids if q in best))
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kq", required=True, help="VINE's evidence file (the job script passes it)")
    ap.add_argument("--questions", default=str(HERE / "questions_40.json"))
    ap.add_argument("--only", default="", help="comma-separated question ids (a smoke test)")
    ap.add_argument("--tag", default="qwen_v1")
    args = ap.parse_args()

    job = os.environ.get("SLURM_JOB_ID", "local")
    scratch = Path(os.environ["SCRATCH"])
    out_dir = scratch / "Beyond_RAG" / "compare40_runs" / "vine_rag"
    out_dir.mkdir(parents=True, exist_ok=True)
    questions = json.loads(Path(args.questions).read_text())
    ids = [q.strip() for q in args.only.split(",") if q.strip()] or list(questions)
    assert all(q in questions for q in ids), f"unknown question ids: {[q for q in ids if q not in questions]}"
    kq = json.loads(Path(args.kq).read_text())
    missing = [q for q in ids if q not in kq or kq[q].get("question") != questions[q]]
    assert not missing, f"no VINE evidence for {missing[:5]} in {args.kq}"

    kq_name = Path(args.kq).name
    for f in part_files(out_dir, args.tag):     # a line cut off by a stopped job would stop run_vine_rag.py
        lines = [x for x in f.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
        good = read_jsonl(f)
        if len(good) != len(lines):
            say(f"{f.name}: {len(lines) - len(good)} cut-off line(s) removed")
            write_atomic(f, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in good))
    done = {r["question_id"] for f in part_files(out_dir, args.tag) for r in read_jsonl(f)
            if r.get("status") == "ok" and counts(r, kq_name)}
    todo = [q for q in ids if q not in done]
    say(f"job {job} | {MODEL_ID} @ {REVISION[:12]} | vLLM {VLLM_VERSION} | tag {args.tag}")
    say(f"questions: {len(ids)} | already answered: {len(ids) - len(todo)} | to answer: {len(todo)}")
    if not todo:
        merge(out_dir, args.tag, ids, kq_name)
        say(f"nothing to do; answers -> {out_dir / f'answers_{args.tag}.jsonl'}")
        return 0

    # 1. the model, with its vision part
    src = model_path()
    vis = vision_part(src)
    say(f"model files: {vis}")
    if not vis["vision_config"] or (vis["vision_tensors"] == 0 and (src / "model.safetensors.index.json").exists()):
        say("STOPPED: these model files hold no vision part, so the model cannot read the figures.")
        return 1
    gpus = [g for g in os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",") if g.strip()]
    assert gpus, "no GPUs in this job"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""            # this process never uses them
    names = gpu_names()
    n = min(len(gpus), len(todo))
    say(f"GPUs: {len(gpus)} -> {names} | servers: {n}")
    tmp = Path(os.environ.get("TMPDIR") or f"/tmp/qwen_rag_{job}")
    model = local_model_copy(src, tmp)
    own_max = model_max_len(src)
    window = min(WINDOW, own_max) if own_max else WINDOW
    say(f"window asked for: {window:,} tokens (the model's own maximum: {own_max or 'not given'})")

    # 2. the servers, vision on
    vc = with_vision(ql.vine_vllm_client())
    vllm_bin = str(Path(os.environ["VLLM_ENV"]) / "bin" / "vllm")
    log_dir = out_dir / f"server_logs_{args.tag}"
    log_dir.mkdir(parents=True, exist_ok=True)
    port0 = first_port(job)
    servers, errors = [None] * n, []

    def start(i: int) -> None:
        log = log_dir / f"vllm_{job}_gpu{i}.log"
        for util in GPU_UTILS:
            try:
                s = vc.launch(vllm_bin, str(model), log_path=str(log), port=port0 + i,
                              env=server_env(gpus[i], tmp / f"server{i}"),
                              say=lambda m, i=i: say(f"[gpu{i}] {m}"),
                              min_model_len=MIN_WINDOW, stop_others=False, ready_timeout=READY_TIMEOUT,
                              served_name=MODEL_ID, max_model_len=window,
                              gpu_memory_utilization=util, seed=SEED)
                s["gpu_memory_utilization"] = util
                servers[i] = s
                return
            except Exception as e:                                       # noqa: BLE001
                text = (str(e) + "\n" + vc.log_tail(str(log), 400)).lower()
                if util != GPU_UTILS[-1] and ("out of memory" in text or "less than desired gpu memory" in text):
                    say(f"[gpu{i}] not enough memory at {util} of the GPU: starting again at {GPU_UTILS[-1]}")
                    time.sleep(20)             # let the stopped server's processes free the GPU
                    continue
                errors.append((i, e))
                return

    say(f"starting {n} servers (usually 10-25 minutes; the limit is {READY_TIMEOUT // 60} minutes) ...")
    t_start = time.time()
    threads = [threading.Thread(target=start, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for i, e in errors:
        say(f"[gpu{i}] the server did not start: {e}")
    live = [(i, s) for i, s in enumerate(servers) if s]
    say(f"{len(live)} of {n} servers started in {time.time() - t_start:.0f}s")
    try:
        return answer_all(args, ids, todo, kq_name, out_dir, job, names, vis, model, vc, log_dir, live)
    finally:
        for _, s in live:                       # stop the servers, whatever happened
            vc.stop_server(s)


def answer_all(args, ids, todo, kq_name, out_dir, job, names, vis, model, vc, log_dir, live) -> int:

    # 3. can each one see a picture?
    usable, probes = [], {}
    for i, s in live:
        p = probe(s["base_url"])
        probes[i] = p
        pinned = "Triton tuning pinned" in vc.log_tail(str(log_dir / f"vllm_{job}_gpu{i}.log"), 100000)
        p["tuning_pin_loaded"] = pinned
        say(f"[gpu{i}] window {s['max_model_len']:,} tokens at {s['gpu_memory_utilization']} of the GPU | "
            f"tuning pin {'loaded' if pinned else 'NOT loaded'} | picture: {p['with_picture']} | "
            f"without: {p['without_picture']}")
        if p["sees_the_picture"]:
            usable.append((i, s))
        else:
            say(f"[gpu{i}] cannot see the picture: not used")
            vc.stop_server(s)
    if not usable:
        say("STOPPED: no server can see a picture (see the lines above). Send this log.")
        return 1
    window = min(s["max_model_len"] for _, s in usable)       # the same room for every question
    say(f"{len(usable)} servers in use | every question gets a window of {window:,} tokens")

    manifest = out_dir / f"qwen_rag_{args.tag}_manifest.json"
    try:
        runs = json.loads(manifest.read_text()).get("runs", []) if manifest.exists() else []
    except ValueError:
        runs = []
    runs.append({"job": job, "started": now(), "model": MODEL_ID, "revision": REVISION, "vllm": VLLM_VERSION,
                 "model_path_used": str(model), "vision_part": vis, "gpus": names,
                 "window_used": window,
                 "servers": [{"gpu": i, "cmd": s["cmd"], "window": s["max_model_len"],
                              "gpu_memory_utilization": s["gpu_memory_utilization"], "probe": probes[i]}
                             for i, s in usable],
                 "request_settings": ql.settings(), "kq_file": kq_name,
                 "questions": todo, "repo_commit": subprocess.run(
                     ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                     capture_output=True, text=True).stdout.strip()})
    write_atomic(manifest, json.dumps({"runs": runs}, indent=1))

    # 4. the questions, one at a time on each server
    work: queue.Queue = queue.Queue()
    for q in todo:
        work.put(q)
    child_env = dict(os.environ, CUDA_VISIBLE_DEVICES="", NO_PROXY="localhost,127.0.0.1",
                     no_proxy="localhost,127.0.0.1")
    lock = threading.Lock()
    busy = [0]                                  # questions being answered now
    handed_back: dict = {}                      # a question is handed back once at most

    def worker(i: int, s: dict) -> None:
        log = out_dir / f"qwen_rag_{args.tag}_gpu{i}.log"
        while True:
            if s["proc"].poll() is not None:
                say(f"[gpu{i}] the server has stopped (exit {s['proc'].returncode}): it takes no more questions")
                return
            with lock:
                try:
                    q = work.get_nowait()
                    busy[0] += 1
                except queue.Empty:
                    q = None
                    if busy[0] == 0:            # nothing left, and nothing that could come back
                        return
            if q is None:
                time.sleep(5)                   # another server may yet hand a question back
                continue
            back = False
            try:
                cmd = [sys.executable, "-u", str(HERE / "run_vine_rag.py"), "--kq", args.kq,
                       "--questions", args.questions, "--models", MODEL_ID, "--only", q,
                       "--tag", f"{args.tag}_s{i}", "--out", str(out_dir),
                       "--local-server", s["base_url"] + "/v1", "--local-max-len", str(window)]
                t0 = time.time()
                with log.open("a", encoding="utf-8") as lf:
                    lf.write(f"\n----- {q} | {now()} -----\n")
                    lf.flush()
                    rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=child_env,
                                        cwd=str(REPO)).returncode
                stopped = rc != 0 and s["proc"].poll() is not None   # the server stopped under it
                back = stopped and handed_back.get(q, 0) == 0
                say(f"[gpu{i}] {q} {'OK ' if rc == 0 else 'ERR'} in {time.time() - t0:.0f}s"
                    + (" | back in the queue: this server has stopped" if back else "")
                    + (" | this server has stopped, and it was handed back once already: not asked again"
                       if stopped and not back else ""))
            except Exception as e:                                  # noqa: BLE001
                say(f"[gpu{i}] {q}: {e!r}")
            finally:
                with lock:
                    if back:
                        handed_back[q] = handed_back.get(q, 0) + 1
                        work.put(q)
                    busy[0] -= 1
                    try:
                        merge(out_dir, args.tag, ids, kq_name)  # the one file is current if the job is stopped
                    except Exception as e:                      # noqa: BLE001
                        say(f"merge failed for now ({e!r}); it is made again at the end")
                    say(f"  {work.qsize()} in the queue, {busy[0]} being answered")

    t_run = time.time()
    workers = [threading.Thread(target=worker, args=(i, s)) for i, s in usable]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    say(f"answering took {time.time() - t_run:.0f}s")
    best = merge(out_dir, args.tag, ids, kq_name)
    ok = [q for q in ids if best.get(q, {}).get("status") == "ok"]
    not_ok = [q for q in ids if q not in ok]
    say("")
    for q in ids:
        r = best.get(q)
        if r is None:
            say(f"  {q}  not asked (the servers stopped first)")
            continue
        calls = (r.get("local_server") or {}).get("calls") or []
        c = calls[-1] if calls else {}
        u = c.get("usage") or {}
        say(f"  {q}  {r.get('status'):5s} | prompt {c.get('prompt_tokens')} tokens | limit {c.get('max_tokens')} | "
            f"out {u.get('completion_tokens')} | {c.get('finish_reason')} | {r.get('latency_s')}s | "
            f"{len(r.get('answer') or '')} chars")
    say(f"\nanswered {len(ok)} of {len(ids)} | not answered: {not_ok or 'none'}")
    say(f"answers -> {out_dir / f'answers_{args.tag}.jsonl'}")
    say(f"reasoning -> {out_dir}/reasoning_{args.tag}_s*.jsonl | manifest -> {manifest}")
    return 0 if not not_ok else 1


if __name__ == "__main__":
    sys.exit(main())
