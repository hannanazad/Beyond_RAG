"""hprc/repeat_probe.py -- why does the parser's reply change from one server start to the next?

    bash hprc/run.sh ACCOUNT 4 probe NAME          (one Slurm job, 4 GPUs, no API cost)

On 12 October the repeat run (hprc/compare_plans.py r1) found that the same
prompt, with the same settings and seed, gave a different reply in 10 of 11 DEV
cases when the server had been started again. The Colab check (3 of 3 the same)
had asked one running server twice; it never started a server again.

This job starts parser servers in several set-ups and asks each the same prompts,
so the replies can be compared byte for byte:

    A1 twice      the same server, asked twice               does one server repeat itself?
    A1 / A2       two servers started fresh, as now          the problem itself
    A1 / A3       A3 starts from a COPY of A1's caches       fix: tune once, reuse every time
    B1 / B2       two fresh servers, VLLM_BATCH_INVARIANT=1  fix: vLLM's own repeatable mode
    C1 / C2       two fresh servers, --enforce-eager         fix: no compiling and no CUDA graphs

Every server runs exactly as the parse stage runs it (vine_hprc.PARSER_SERVER and
parser_server_env), plus TRITON_CACHE_AUTOTUNING=1 so that tuning results are
written to the caches, which A3 needs. The prompts are the ones the 11 October run
sent, read back from its model cache, for the three DEV cases that changed earliest
on 12 October. Each reply is cut at PROBE_TOKENS tokens: on 12 October every reply
that changed had changed by about 500 tokens.

Results: $SCRATCH/Beyond_RAG/parser_runs_faster/probe_NAME/ (probe.json, the
replies, the server logs). The job prints the comparison at the end of its log.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

PROBE_CASES = ("P44-scenario", "P47-scenario", "P18-scenario")
PROBE_TOKENS = 4096
COMMON_ENV = {"TRITON_CACHE_AUTOTUNING": "1"}
SETUPS = {
    "default": ({}, []),
    "batch_invariant": ({"VLLM_BATCH_INVARIANT": "1"}, []),
    "eager": ({}, ["--enforce-eager"]),
}
# each GPU's servers, one after the other: (label, set-up, copy the caches of)
SCHEDULE = [
    [("A1", "default", None)],
    [("A2", "default", None), ("A3", "default", "A1")],
    [("B1", "batch_invariant", None), ("C1", "eager", None)],
    [("B2", "batch_invariant", None), ("C2", "eager", None)],
]
ROUNDS = {"A1": 2}            # A1 is asked twice
COMPARISONS = [
    ("the same server, asked twice", ("A1", 1), ("A1", 2)),
    ("two servers started fresh, as now", ("A1", 1), ("A2", 1)),
    ("a server started from a copy of A1's caches", ("A1", 1), ("A3", 1)),
    ("two fresh servers, VLLM_BATCH_INVARIANT=1", ("B1", 1), ("B2", 1)),
    ("two fresh servers, --enforce-eager", ("C1", 1), ("C2", 1)),
]
LOG_SIGNS = ("torch.compile took", "Directly load", "loaded", "Using cache directory", "batch invariant",
             "Batch invariant", "batch_invariant", "enforce_eager=True", "Cudagraph is disabled",
             "Using FLASH", "Selected ", "Using Triton", "Traceback", "Error")


def common_prefix(a: str, b: str) -> int:
    a, b = a or "", b or ""
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def same_reply(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (a["reasoning"], a["content"], a["tokens"], a["finish"]) == \
           (b["reasoning"], b["content"], b["tokens"], b["finish"])


def earlier_replies(runs: Path, folder: str, qid: str) -> Dict[str, Dict[str, Any]]:
    """The full replies the earlier runs got for this case: {"first run": rec,
    "repeat_r1": rec, ...}, read from their model caches."""
    out = {}
    places = [("first run", runs)] + [(d.name, d) for d in sorted(runs.glob("repeat_*")) if d.is_dir()]
    for name, root in places:
        plans_file = root / folder / "plans.json"
        try:
            call = json.loads(plans_file.read_text())[qid]["calls"][0]
            rec = json.loads((root / "model_cache" / f"{call['cache_key']}.json").read_text())
        except (OSError, ValueError, KeyError, IndexError):
            continue
        rec["prompt_sha256_in_plan"] = call.get("prompt_sha256")
        out[name] = rec
    return out


def load_prompts(runs: Path, folder: str, say: Callable = print) -> Dict[str, Dict[str, Any]]:
    """The prompt the first run sent for each probe case, checked against the
    SHA-256 its plan recorded."""
    prompts = {}
    for qid in PROBE_CASES:
        first = earlier_replies(runs, folder, qid).get("first run")
        assert first, (f"the first run's reply for {qid} is not in {runs / 'model_cache'} -- "
                       f"the probe needs the prompt it was sent")
        prompt = first["prompt"]
        sha = hashlib.sha256(prompt.encode()).hexdigest()
        assert sha == first["prompt_sha256_in_plan"], f"{qid}: the cached prompt is not the one the plan recorded"
        prompts[qid] = {"prompt": prompt, "sha256": sha, "max_tokens_first_run": first.get("max_tokens")}
        say(f"  prompt {qid}: {len(prompt):,} characters, sha256 {sha[:12]}")
    return prompts


def run_probe(name: str, runs: Path, folder: str, gpus: List[str], *, launch: Callable, stop: Callable,
              make_ask: Callable, server_env: Callable, server_kwargs: Dict[str, Any], vllm_bin: str,
              model_path: str, tmp: Path, port0: int, ask_kwargs: Dict[str, Any],
              say: Callable = print, settle: float = 20.0) -> Dict[str, Any]:
    """Start the servers of SCHEDULE (one list per GPU, run side by side), ask
    each the probe prompts, compare, save probe.json and return the report."""
    out_dir = runs / f"probe_{name}"
    # a used name would read its old replies back from their caches instead of asking the servers
    assert not (out_dir / "replies").exists(), f"{out_dir} has been used already -- choose a new NAME"
    out_dir.mkdir(parents=True, exist_ok=True)
    assert len(gpus) >= len(SCHEDULE), f"the probe needs {len(SCHEDULE)} GPUs, this job has {len(gpus)}"
    prompts = load_prompts(runs, folder, say)
    earlier = {qid: earlier_replies(runs, folder, qid) for qid in PROBE_CASES}
    replies: Dict[str, Dict[int, Dict[str, Any]]] = {}
    servers: Dict[str, Dict[str, Any]] = {}
    a1_ready = threading.Event()          # A1's caches are complete once its first round is done
    lock = threading.Lock()
    ports = iter(range(port0, port0 + 10))
    port_of = {label: next(ports) for lane in SCHEDULE for label, _, _ in lane}

    def one_server(slot: int, label: str, setup: str, copy_from: Optional[str]) -> None:
        try:
            _one_server(slot, label, setup, copy_from)
        except Exception as e:                                        # noqa: BLE001
            with lock:
                servers.setdefault(label, {"label": label, "setup": setup})["error"] = f"stopped: {e!r}"[:1500]
            say(f"[{label}] stopped: {e!r}"[:300])
        finally:
            if label == "A1":
                a1_ready.set()        # however A1 ended, nothing waits for it for ever

    def _one_server(slot: int, label: str, setup: str, copy_from: Optional[str]) -> None:
        own = tmp / f"probe_{label}"
        info: Dict[str, Any] = {"label": label, "setup": setup, "gpu_slot": slot, "copied_caches_of": copy_from}
        with lock:
            servers[label] = info
        if copy_from:
            a1_ready.wait()
            src = tmp / f"probe_{copy_from}"
            if not src.exists():
                info["error"] = f"no caches of {copy_from} to copy"
                say(f"[{label}] {info['error']}")
                return
            shutil.copytree(src, own, dirs_exist_ok=True)
            info["copied_files"] = sum(1 for p in own.rglob("*") if p.is_file())
        extra_env, extra_args = SETUPS[setup]
        env = {**server_env(gpus[slot], own), **COMMON_ENV, **extra_env}
        log = out_dir / "server_logs" / f"{label}.log"
        t0 = time.time()
        try:
            server = launch(vllm_bin, model_path, log_path=str(log), port=port_of[label], env=env,
                            say=lambda m: say(f"[{label}] {m}"), extra=list(extra_args), **server_kwargs)
        except Exception as e:                                        # noqa: BLE001
            info["error"] = f"the server did not start: {str(e)[:1500]}"
            say(f"[{label}] {info['error'][:300]}")
            return
        info.update(start_seconds=round(time.time() - t0), max_model_len=server.get("max_model_len"),
                    env={k: env[k] for k in sorted({**COMMON_ENV, **extra_env})}, extra_args=extra_args)
        say(f"[{label}] ready in {info['start_seconds']}s ({setup}"
            + (f", from a copy of {copy_from}'s caches, {info.get('copied_files')} files" if copy_from else "") + ")")
        try:
            for rnd in range(1, ROUNDS.get(label, 1) + 1):
                cache = out_dir / "replies" / f"{label}_round{rnd}"
                ask = make_ask(server["base_url"], cache_dir=str(cache), **ask_kwargs)
                for qid in PROBE_CASES:
                    t1 = time.time()
                    content = ask(prompts[qid]["prompt"], [])
                    rec = json.loads((cache / f"{ask.last['cache_key']}.json").read_text())
                    secs = time.time() - t1
                    tokens = (rec.get("usage") or {}).get("completion_tokens")
                    r = {"content": content, "reasoning": rec.get("reasoning") or "", "tokens": tokens,
                         "finish": rec.get("finish_reason"), "seconds": round(secs, 1),
                         "tokens_per_second": round(tokens / secs, 1) if tokens and secs else None,
                         "prompt_sha256": rec.get("prompt_sha256")}
                    assert r["prompt_sha256"] == prompts[qid]["sha256"], "the prompt sent is not the probe prompt"
                    with lock:
                        replies.setdefault(label, {}).setdefault(rnd, {})[qid] = r
                    say(f"[{label}] round {rnd} {qid:14s} {tokens} tokens, {r['tokens_per_second']} tokens/s, "
                        f"finish {r['finish']}")
                if label == "A1" and rnd == 1:
                    a1_ready.set()
        except Exception as e:                                        # noqa: BLE001
            info["error"] = f"a request failed: {str(e)[:1500]}"
            say(f"[{label}] {info['error'][:300]}")
        finally:
            stop(server)
            info["log_lines"] = _log_signs(log)
            time.sleep(settle)            # let the GPU's memory go before the next server on it

    def lane(slot: int) -> None:
        for label, setup, copy_from in SCHEDULE[slot]:
            one_server(slot, label, setup, copy_from)

    threads = [threading.Thread(target=lane, args=(i,)) for i in range(len(SCHEDULE))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    report = compare(replies, servers, earlier)
    _print_report(report, say)
    (out_dir / "probe.json").write_text(json.dumps(
        {"name": name, "cases": PROBE_CASES, "probe_tokens": PROBE_TOKENS, "schedule": SCHEDULE,
         "common_env": COMMON_ENV, "servers": servers, "report": report,
         "prompts": {q: {k: v for k, v in p.items() if k != "prompt"} for q, p in prompts.items()},
         "replies": replies}, indent=1))
    say(f"\nsaved -> {out_dir / 'probe.json'}")
    return report


def _log_signs(log: Path) -> List[str]:
    try:
        lines = log.read_text(errors="replace").splitlines()
    except OSError:
        return []
    return [l[-220:] for l in lines if any(s in l for s in LOG_SIGNS)][:40]


def compare(replies, servers, earlier) -> Dict[str, Any]:
    rows = []
    for title, (la, ra), (lb, rb) in COMPARISONS:
        row = {"title": title, "a": f"{la} round {ra}", "b": f"{lb} round {rb}", "cases": {}}
        problems = [f"{l}: {servers[l]['error']}" for l in (la, lb) if l in servers and servers[l].get("error")]
        A, B = replies.get(la, {}).get(ra, {}), replies.get(lb, {}).get(rb, {})
        for qid in PROBE_CASES:
            if qid not in A or qid not in B:
                row["cases"][qid] = "not run"
                continue
            if same_reply(A[qid], B[qid]):
                row["cases"][qid] = "same"
            else:
                part = "reasoning" if A[qid]["reasoning"] != B[qid]["reasoning"] else "content"
                row["cases"][qid] = f"differs at {part} character {common_prefix(A[qid][part], B[qid][part]):,}"
        done = [v for v in row["cases"].values() if v != "not run"]
        row["same"], row["of"] = sum(1 for v in done if v == "same"), len(done)
        row["problems"] = problems
        rows.append(row)
    # how far each probe reply agrees with the full replies of the earlier runs
    agree = {}
    for label, rounds in sorted(replies.items()):
        for rnd, by_case in sorted(rounds.items()):
            for qid, r in by_case.items():
                agree.setdefault(qid, {})[f"{label} round {rnd}"] = {
                    name: common_prefix(r["reasoning"], rec.get("reasoning") or "")
                    for name, rec in earlier.get(qid, {}).items()}
    speed = {}
    for label, rounds in replies.items():
        tps = [r["tokens_per_second"] for by_case in rounds.values() for r in by_case.values() if r["tokens_per_second"]]
        speed[label] = round(sum(tps) / len(tps), 1) if tps else None
    return {"comparisons": rows, "agreement_with_earlier_runs": agree, "tokens_per_second": speed,
            "servers": {l: {k: v for k, v in s.items() if k in ("setup", "start_seconds", "error",
                                                                  "copied_files", "max_model_len")}
                        for l, s in servers.items()}}


def _print_report(report: Dict[str, Any], say: Callable) -> None:
    say("\n" + "=" * 100)
    say(f"RESULT: the same prompt, seed and settings; the first {PROBE_TOKENS} tokens of each reply, byte for byte")
    say("=" * 100)
    for row in report["comparisons"]:
        verdict = f"{row['same']} of {row['of']} the same" if row["of"] else "could not be compared"
        say(f"\n{row['title']}  ({row['a']} / {row['b']}): {verdict}")
        for qid, v in row["cases"].items():
            say(f"    {qid:14s} {v}")
        for p in row["problems"]:
            say(f"    ! {p[:400]}")
    say("\nspeed, tokens a second: " + ", ".join(f"{l} {v}" for l, v in sorted(report["tokens_per_second"].items())))
    say("server start, seconds : " + ", ".join(f"{l} {s.get('start_seconds')}" for l, s in sorted(report["servers"].items())))
    for l, s in sorted(report["servers"].items()):
        if s.get("max_model_len") not in (None, 73728):
            say(f"  note: {l} started with max_model_len {s['max_model_len']}, not 73728")
    say("\nhow many characters of each reply's reasoning agree with the earlier runs' full replies:")
    for qid, by_reply in report["agreement_with_earlier_runs"].items():
        for who, d in by_reply.items():
            say(f"    {qid:14s} {who:12s} " + ", ".join(f"{k} {v:,}" for k, v in d.items()))
