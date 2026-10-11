"""hprc/vine_hprc.py -- the VINE run on FASTER (TAMU HPRC), in three stages.

    retrieval : the retrieval check on the 154 DEV cases (with the gate),
                then Kq for every question                          (1 GPU)
    parse     : the parser (Qwen3.8-27B-FP8, xhigh) writes every plan, with
                one vLLM server per GPU, one question at a time each (N GPUs)
    execute   : the checkers (Claude Sonnet 5.5) execute every plan, and the
                answers are written                                  (1 GPU)

Each stage is one Slurm job (hprc/run.sh submits them). The steps and helpers
are the ones in notebooks/VINE_Run.ipynb. Every stage saves as it goes and,
run again, carries on where it stopped.

Results go to $SCRATCH/Beyond_RAG/parser_runs_faster/ and
$SCRATCH/Beyond_RAG/retrieval_dev_results_faster/, apart from the Colab runs.

The questions: the 11 DEV cases plus the 20 sample questions (their TEXT only,
read from notebooks/VINE_Run.ipynb so there is one copy). For the sealed
questions later: VINE_QUESTIONS=/path/to/file.json ({id: text}).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "evaluation"))
os.environ.setdefault("MRAG_ENV", "hprc")

from mrag.config import CFG  # noqa: E402
import parser_check as pc  # noqa: E402
import execution_check as ec  # noqa: E402
import retrieval_check as rc  # noqa: E402
import vine_run as vr  # noqa: E402
from mrag.vine.parser import PARSER_TASK, PARSER_CONTRACT, build_parser_prompt  # noqa: E402

# the parser, as on Colab (docs/PARSER_TEST_2026-10-07.md)
MODEL_ID = "Qwen/Qwen3.8-27B-FP8"
REVISION = "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"
VLLM_VERSION = "0.31.0"
SEED, EFFORT = 42, "xhigh"
GPU_UTIL = 0.90
# the checkers, as in the notebook
CHECKER_MODEL, CHECKER_EFFORT, CHECKER_MAX_TOKENS = "claude-sonnet-5-5", "high", 32000
MAX_IMAGES = 4
FIG_KEYS = ("figure_id", "caption", "n_sheets", "image_paths", "image_path", "page_pdf", "source")
SETTING_NAMES = (
    "top_k_fused", "top_k_after_graph", "top_k_compile_chunks", "expansion_source_chunks",
    "expansion_reserved_slots", "compile_closure_budget", "compile_find_provisions",
    "compile_sentence_queries", "compile_list_depth", "compile_term_queries", "compile_term_candidates",
    "compile_heading_sections", "compile_heading_candidates", "compile_heading_paragraphs",
    "compile_pool_cap")


def say(*a) -> None:
    print(*a, flush=True)


def sample_questions() -> dict:
    """The 20 sample questions (text only), from the notebook's CELL 4."""
    nb = json.loads((REPO / "notebooks" / "VINE_Run.ipynb").read_text())
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if "\nSAMPLE = {" not in "\n" + src:
            continue
        for node in ast.parse(src).body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and getattr(node.targets[0], "id", "") == "SAMPLE"):
                return ast.literal_eval(node.value)
    raise RuntimeError("the SAMPLE questions are not in notebooks/VINE_Run.ipynb")


class Run:
    """The questions and where this run keeps its results (the notebook's CELL 4)."""

    def __init__(self) -> None:
        self.commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                                     capture_output=True, text=True).stdout.strip() or "nocommit"
        self.dev_all = rc.load_cases()            # 154 DEV cases: the retrieval check
        self.dev = pc.load_dev_cases()            # the 11 DEV cases answered end to end
        qfile = os.environ.get("VINE_QUESTIONS", "").strip()
        if qfile:
            self.answer_set, self.set_name = json.loads(Path(qfile).read_text()), "sealed"
        else:
            self.answer_set, self.set_name = sample_questions(), "sample"
        self.questions = {**{c["case_id"]: c["text"] for c in self.dev}, **self.answer_set}
        self.dev_ids = [c["case_id"] for c in self.dev]
        self.case = {c["case_id"]: c for c in self.dev}
        assert not set(self.dev_ids) & set(self.answer_set), "a question id is used twice"
        self.retr_commit = vr.retrieval_commit(str(REPO))
        self.store_tag = vr.store_tag(CFG.base_dir)
        self.instructions_sha = hashlib.sha256((PARSER_TASK + PARSER_CONTRACT).encode()).hexdigest()
        self.runs = Path(CFG.base_dir) / "parser_runs_faster"
        self.kq_file = self.runs / f"kq_r{self.retr_commit}_s{self.store_tag}.json"
        self.run_dir = self.runs / f"e2e_r{self.retr_commit}_s{self.store_tag}_p{self.instructions_sha[:8]}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.plans_file = self.run_dir / "plans.json"
        self.settings = {k: getattr(CFG, k) for k in SETTING_NAMES}
        self.job = os.environ.get("SLURM_JOB_ID", "nojob")
        say(f"code commit {self.commit} | retrieval code {self.retr_commit} | store {self.store_tag} "
            f"| parser instructions {self.instructions_sha[:12]}")
        say(f"{len(self.questions)} questions: {len(self.dev)} DEV + {len(self.answer_set)} {self.set_name}")
        say(f"run folder: {self.run_dir}")


def load_retrieval():
    """The retrieval stack on the GPU (the notebook's CELL 3), with a check that
    neither model fell back to a substitute."""
    from mrag.ask import init_pipeline
    p = init_pipeline(load_image_embedder=False, load_vlm=False)
    assert type(p.kg).__name__ == "VineKG", "retrieval is not on the VINE graph -- check CFG.graph_backend"
    mode = getattr(p.text, "_mode", "?")
    reranker = type(getattr(p.rerank, "_model", None)).__name__
    say(f"text encoder : {CFG.bge_m3_model} ({mode}) | reranker: {CFG.reranker_model} ({reranker})")
    assert mode in ("bge-m3", "bge-m3-direct"), f"the encoder fell back to {mode} (no sparse half)"
    assert reranker == "MxbaiRerankV2", f"the reranker fell back to {reranker}"
    return p


def gpu_names() -> list:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# Stage 1: the retrieval check on DEV, then Kq for every question
# --------------------------------------------------------------------------- #
def stage_retrieval(R: Run) -> int:
    say("GPU:", gpu_names())
    pipeline = load_retrieval()
    n_store = pipeline.store.client.count(CFG.coll_chunks, exact=True).count
    say(f"graph        : {pipeline.kg.g.number_of_nodes():,} nodes, {pipeline.kg.g.number_of_edges():,} edges")
    say(f"vector store : {n_store:,} items")
    _, sp = pipeline.text.encode_both(["minimum mounting height of a sign"])
    say(f"sparse weights in a query: {len(sp[0])}  (0 = the sparse half of search is not working)")
    assert len(sp[0]) > 0, "the sparse half of search is not working"
    say("retrieval    :", R.settings)
    assert CFG.compile_find_provisions, "CFG.compile_find_provisions is off -- this run is for the new retrieval"

    # --- the retrieval check (the notebook's CELL 5) ---
    out_dir = Path(CFG.base_dir) / "retrieval_dev_results_faster"
    check_file = out_dir / f"retrieval_check_r{R.retr_commit}_s{R.store_tag}.json"
    before_file = out_dir / f"retrieval_before_r{R.retr_commit}_s{R.store_tag}.json"
    t0 = time.time()
    now = vr.run_check_resumable(lambda c: rc.run_case(pipeline.retriever, c), R.dev_all, check_file)
    say(f"\nnew retrieval: {len(now)} cases, median {sorted(r['seconds'] for r in now)[len(now) // 2]:.1f}s a case")
    rc.print_summary(rc.summarize(now))

    def run_old(case):
        CFG.compile_find_provisions = False
        try:
            return rc.run_case(pipeline.retriever, case)
        finally:
            CFG.compile_find_provisions = True

    earlier = vr.load_json(Path(CFG.base_dir) / vr.EARLIER_RETRIEVAL_TEST, {})
    if earlier:
        say(f"\nearlier run: {vr.EARLIER_RETRIEVAL_TEST} | store {earlier.get('store_chunks')} items "
            f"(now {n_store}) | commit {earlier.get('commit')}")
        if earlier.get("store_chunks") not in (None, n_store):
            say("WARNING: the vector store has changed since the earlier run; 'before' is run again here for every case")
            earlier = {}
    else:
        say("\nno earlier run; 'before' is run here for every case")
    before = vr.results_before(R.dev_all, earlier.get("results"), run_old, out_path=before_file)
    gate = rc.gate(now, before)
    say("\n=== before -> after (target provisions reach what the parser reads) ===")
    rc.print_gate(gate)
    say("\nper style, before:")
    rc.print_summary(rc.summarize(before))
    miss_now = {r["case_id"] for r in now if not rc.passes(r)}
    miss_before = {r["case_id"] for r in before if not rc.passes(r)}
    show = [c["case_id"] for c in R.dev_all if c["case_id"] in miss_now | miss_before]
    say(f"\n=== {len(show)} cases that miss now or missed before: where each target came from ===")
    rc.print_targets(now, show)
    vr.save_json(check_file, {"commit": R.commit, "retrieval_commit": R.retr_commit, "settings": R.settings,
                              "store_items": n_store, "summary": rc.summarize(now), "gate": gate,
                              "results": now, "machine": "FASTER", "gpu": gpu_names()})
    say("\nsaved ->", check_file, f"| {time.time() - t0:.0f}s")
    if not gate["ok"]:
        say(f"\nSTOPPED: the new retrieval finds the target provisions for FEWER DEV cases than before "
            f"({gate['pass_before']} -> {gate['pass_now']}). The parser jobs will not start. Send this log.")
        return 1

    # --- Kq for every question (the notebook's CELL 6) ---
    kq = vr.load_json(R.kq_file, {})
    changed = [q for q in R.questions if q in kq and kq[q].get("question") != R.questions[q]]
    missing = [q for q in R.questions if q not in kq] + changed
    say(f"\n{R.kq_file.name}: {len(kq)} questions already retrieved, {len(missing)} to retrieve")
    for i, qid in enumerate(missing, 1):
        q = R.questions[qid]
        t1 = time.time()
        res = pipeline.retriever.retrieve_for_compile(q)
        find = res.debug.get("find") or {}
        kq[qid] = vr.plain({"question": q, "chunks": res.chunks,
                            "figures": [{k: f.get(k) for k in FIG_KEYS if k in f} for f in res.figures],
                            "closure": res.debug.get("closure", {}),
                            "find": {k: find.get(k) for k in ("sentences", "terms", "headings", "pool")},
                            "seconds": round(time.time() - t1, 1)})
        vr.save_json(R.kq_file, kq)
        say(f"  {i:2d}/{len(missing)} {qid:26s} Kq {len(res.chunks):3d} items, {len(res.figures)} figures, "
            f"{time.time() - t1:4.1f}s")
    for qid in R.dev_ids:
        t = pc.target_check(None, R.case[qid], kq[qid]["chunks"])
        say(f"  DEV {qid:26s} the provision the case was written from reaches the parser: {t['target_chunk_in_kq']}")
    sizes = {qid: len(build_parser_prompt(kq[qid]["question"], kq[qid]["chunks"], "", None, kq[qid]["figures"]))
             for qid in R.questions}
    longest = max(sizes, key=sizes.get)
    say(f"longest parser prompt: {sizes[longest]:,} characters (about {sizes[longest] // 4:,} tokens)")
    say("\nRETRIEVAL STAGE FINISHED")
    return 0


# --------------------------------------------------------------------------- #
# Stage 2: the plans, one vLLM server per GPU
# --------------------------------------------------------------------------- #
def stage_parse(R: Run) -> int:
    from mrag.kg_vine import VineKG
    from mrag.vine import table_data, vllm_client as vc
    from mrag.vine.parser import make_semantic_parser
    from mrag.vine.compile import instantiate

    kq = vr.load_json(R.kq_file, {})
    no_kq = [q for q in R.questions if q not in kq or kq[q].get("question") != R.questions[q]]
    assert not no_kq, f"no Kq yet for {no_kq[:5]} -- the retrieval stage has not finished"
    records = vr.load_json(R.plans_file, {})
    to_parse = [q for q in R.questions if vr.plan_needs_retry(records.get(q), R.questions[q])]
    say(f"plans: {len(R.questions) - len(to_parse)} already made (from {R.plans_file.name}), {len(to_parse)} to make")
    if not to_parse:
        say("PARSE STAGE FINISHED (nothing to do)")
        return 0

    # the GPUs Slurm gave this job; this process itself never uses them
    gpus = [g for g in os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",") if g.strip()]
    assert gpus, "no GPUs in this job"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    names = gpu_names()
    say(f"GPUs: {len(gpus)} -> {names}")
    n = min(len(gpus), len(to_parse))

    # the parser's checks read the graph and the tables (CPU only, no search models)
    kg = VineKG(CFG.vine_graph, figures_path=CFG.figures_jsonl, sign_codes_path=CFG.sign_codes_json,
                items_path=CFG.vine_items, tables_path=CFG.tables_jsonl,
                table_rows_in_closure=getattr(CFG, "closure_table_rows", 15))
    tables = {}
    for t in table_data.load(Path(CFG.tables_jsonl)):
        tables.setdefault(t.table_id, []).append(t)

    vllm_env = Path(os.environ["VLLM_ENV"])
    model_path = (Path(os.environ["HF_HUB_CACHE"]) / ("models--" + MODEL_ID.replace("/", "--"))
                  / "snapshots" / REVISION)
    assert (model_path / "config.json").exists(), f"the parser's model is not at {model_path} -- run hprc/setup.sh"
    tmp = Path(os.environ.get("TMPDIR") or f"/tmp/vine_{R.job}")
    port0 = 20000 + (int(R.job) % 400) * 10 if R.job.isdigit() else 20000
    log_dir = R.run_dir / "server_logs"

    servers = [None] * n
    errors = []

    def start(i: int) -> None:
        own = tmp / f"server{i}"          # each server's compile caches on the node's own disk
        try:
            servers[i] = vc.launch(
                str(vllm_env / "bin" / "vllm"), str(model_path),
                log_path=str(log_dir / f"vllm_{R.job}_gpu{i}.log"), port=port0 + i,
                env={"CUDA_VISIBLE_DEVICES": gpus[i], "HF_HUB_OFFLINE": "1",
                     # FlashInfer's sampler failed to build on Colab; seeded requests never use it
                     "VLLM_USE_FLASHINFER_SAMPLER": "0",
                     "VLLM_CACHE_ROOT": str(own / "vllm"), "TRITON_CACHE_DIR": str(own / "triton"),
                     "TORCHINDUCTOR_CACHE_DIR": str(own / "inductor"), "FLASHINFER_WORKSPACE_BASE": str(own)},
                say=lambda m, i=i: say(f"[gpu{i}] {m}"),
                served_name="parser", max_model_len=73728, min_model_len=65536,
                gpu_memory_utilization=GPU_UTIL, seed=SEED, stop_others=False)
        except Exception as e:                                   # noqa: BLE001
            errors.append((i, e))

    say(f"starting {n} parser servers (5-15 minutes) ...")
    starters = [threading.Thread(target=start, args=(i,)) for i in range(n)]
    for t in starters:
        t.start()
    for t in starters:
        t.join()
    live = [s for s in servers if s]
    if errors:
        for i, e in errors:
            say(f"[gpu{i}] the server did not start: {e}")
    if not live:
        say("STOPPED: no parser server started. Send this log.")
        return 1
    max_len = min(s["max_model_len"] for s in live)
    max_tokens = min(49152, max_len - 21504)
    engine = f"vllm {VLLM_VERSION}"
    say(f"{len(live)} servers ready | max_model_len {max_len} | max_tokens {max_tokens}")

    asks = []
    for i, s in enumerate(servers):
        if not s:
            continue
        probe = vc.make_ask_vllm(s["base_url"], "parser", model_id=MODEL_ID, revision=REVISION, engine=engine,
                                 seed=SEED, max_tokens=2048, reasoning_effort="low")
        reply = probe('Reply with this JSON object and nothing else: {"ok": true}', [])
        say(f"[gpu{i}] probe reply: {reply[:60]!r} | {probe.last['finish_reason']}")
        if '"ok"' not in reply:
            say(f"[gpu{i}] answered, but not with the JSON asked for: not used")
            continue

        def make_ask(mt, url=s["base_url"]):
            return vc.make_ask_vllm(url, "parser", model_id=MODEL_ID, revision=REVISION, engine=engine,
                                    seed=SEED, max_tokens=mt, reasoning_effort=EFFORT,
                                    cache_dir=str(R.runs / "model_cache"))
        asks.append((i, vr.BudgetedAsk(make_ask, s["base_url"], "parser", max_len=max_len, max_tokens=max_tokens,
                                       template_kwargs={"enable_thinking": True, "reasoning_effort": EFFORT})))
    if not asks:
        for s in live:
            vc.stop_server(s)
        say("STOPPED: no server answered the probe. Send this log.")
        return 1

    vr.save_json(R.run_dir / "parse_manifest.json", {
        "commit": R.commit, "model": MODEL_ID, "revision": REVISION, "vllm": VLLM_VERSION,
        "server_command": live[0]["cmd"], "servers": len(asks), "gpu": names, "seed": SEED,
        "sampling": vc.QWEN_THINKING, "reasoning_effort": EFFORT, "max_tokens": max_tokens,
        "max_model_len": max_len, "max_attempts": 3, "fallback": False, "instructions": "fix5",
        "instructions_sha256": R.instructions_sha, "kq_file": R.kq_file.name,
        "retrieval_settings": R.settings, "machine": "FASTER", "slurm_job": R.job,
        "one_request_at_a_time": True})

    order = [q for q in R.dev_ids if q in to_parse] + [q for q in to_parse if q not in R.dev_ids]
    work: "queue.Queue[str]" = queue.Queue()
    for q in order:
        work.put(q)
    lock = threading.Lock()
    done = [0]

    def worker(i: int, ask) -> None:
        parse = make_semantic_parser(ask, max_attempts=3, fall_back_to_baseline=False,
                                     check_ref=kg.is_known_citation, tables=tables)
        while True:
            try:
                qid = work.get_nowait()
            except queue.Empty:
                return
            v = kq[qid]
            t0 = time.time()
            try:
                spec, rep = parse(v["question"], v["chunks"], "", v["figures"])
                net = instantiate(spec)[0] if spec is not None else None
                rec = pc.make_record(qid, v["question"], v, spec, rep, net, time.time() - t0,
                                     case=R.case.get(qid))
            except Exception as e:                               # noqa: BLE001
                rec = vr.failed_plan_record(qid, v["question"], f"the parse stopped: {e!r}", kq=v)
            rec["gpu_slot"] = i
            with lock:
                records[qid] = rec
                vr.save_json(R.plans_file, records)
                done[0] += 1
                s = rec["stats"]
                say(f"  {done[0]:2d}/{len(order)} [gpu{i}] {qid:26s} {rec['outcome']:19s} attempts {rec['attempts']} "
                    f"checks {s.get('obligations', 0):2d} merges {s.get('merges', 0)} | {rec['seconds']:5.0f}s "
                    f"| finish {[c.get('finish_reason') for c in rec['calls']]} "
                    f"| prompt tokens {[c.get('prompt_tokens') for c in rec['calls']]}")

    t_all = time.time()
    workers = [threading.Thread(target=worker, args=(i, a)) for i, a in asks]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    for s in live:
        vc.stop_server(s)
    say(f"all plans in {(time.time() - t_all) / 60:.0f} minutes")

    dev_plans = [records[q] for q in R.dev_ids if q in records]
    say("\n=== DEV plans ===")
    pc.print_summary(pc.summarize(dev_plans))
    others = [records[q] for q in R.questions if q not in R.dev_ids and q in records]
    say(f"{R.set_name} plans: " + ", ".join(f"{k} {sum(1 for r in others if r['outcome'] == k)}"
                                          for k in ("valid first time", "valid after repair", "failed")))
    for r in dev_plans:
        say()
        pc.print_plan(r)
    broken = [q for q in R.questions if vr.plan_needs_retry(records.get(q), R.questions[q])]
    if broken:
        say(f"\nSTOPPED: {len(broken)} plans broke (the model call or the run, not the plan): {broken}. "
            "Submit the parse stage again; it makes only those.")
        return 1
    say("\nPARSE STAGE FINISHED")
    return 0


# --------------------------------------------------------------------------- #
# Stage 3: the checkers execute every plan; the answers
# --------------------------------------------------------------------------- #
def stage_execute(R: Run) -> int:
    from mrag.vine import anthropic_client as ac
    from mrag.vine import table_data
    from mrag.vine.lookup import ManualView, Lookups, TOOL_SPECS, tools_digest
    from mrag.vine.compile import NetworkSpec, instantiate
    from mrag.vine.run import build_verifiers
    from mrag.vine.execute import execute
    from mrag.vine.answer import compose
    from mrag.vine.model_verifiers import READING_RULES, LOOKUP_RULES

    records = vr.load_json(R.plans_file, {})
    no_plan = [q for q in R.questions if q not in records]
    assert not no_plan, f"no plan yet for {no_plan[:5]} -- the parse stage has not finished"
    assert os.environ.get("ANTHROPIC_API_KEY"), "no Anthropic key (see hprc/README.md)"

    say("GPU:", gpu_names())
    pipeline = load_retrieval()
    retriever, kg = pipeline.retriever, pipeline.kg
    table_list = list(table_data.load(Path(CFG.tables_jsonl)))

    ask0 = ac.make_ask_anthropic(CHECKER_MODEL, effort=CHECKER_EFFORT, max_tokens=CHECKER_MAX_TOKENS,
                                 cache_dir=str(R.runs / "checker_cache"))
    reply = ask0('Reply with this JSON object and nothing else: {"ok": true}', [])
    say("text probe  :", repr(reply[:80]), "|", ask0.last["finish_reason"], "|", ask0.last["model"])
    assert '"ok"' in reply, "the API answered, but not with the JSON asked for"
    fig = kg.figure("Figure 2B-1")
    assert fig, "Figure 2B-1 is not in the graph"
    img = kg.g.nodes[fig].get("image_path") or (kg.g.nodes[fig].get("image_paths") or [""])[0]
    assert os.path.exists(img), f"the figure image is not on disk: {img}"
    say("figure file :", img)
    reply = ask0('Reply with one JSON object and nothing else: {"shape": "<the shape of the first '
                 'sign shown, in one or two words>"}', [img])
    say("image probe :", repr(reply[:120]), "|", ask0.last["finish_reason"])
    view = ManualView.from_retriever(retriever)
    assert view is not None, "the labels and lookups need the VINE graph"
    probe = Lookups(view, max_lookups=2)
    reply, tr = ask0.converse(
        'Use the open_section tool to open Section 1C.01, then reply with one JSON object and nothing '
        'else: {"title": "<the section title>"}', [], probe.specs(), probe.run, max_lookups=2)
    say("lookup probe:", repr(reply[:120]), "| lookups", [e["tool"] for e in probe.log], "| turns", tr["turns"])
    assert probe.log and '"title"' in reply, "the tool-use conversation did not work"

    plans = {}
    for qid in R.questions:
        d = records[qid].get("spec")
        spec = NetworkSpec.from_dict(d) if d else None
        net, problems = instantiate(spec) if spec is not None else (None, ["no plan"])
        plans[qid] = {"spec": spec, "net": net, "problems": problems}
    say(f"{sum(1 for p in plans.values() if p['net'] is not None and not p['problems'])} of {len(plans)} plans can be executed")

    model_options = {"use_pointers": True, "max_pointed_chunks": 8, "max_images": MAX_IMAGES,
                     "labels": True, "use_lookups": True, "max_lookups": 12,
                     "named_exceptions": True, "max_named_exceptions": 6}
    exec_file = R.run_dir / f"exec_{R.commit}.json"
    manifest = {"commit": R.commit, "plans_file": str(R.plans_file), "instructions_sha256": R.instructions_sha,
                "checker_model": CHECKER_MODEL, "checker_effort": CHECKER_EFFORT,
                "checker_max_tokens": CHECKER_MAX_TOKENS, "checker_temperature": "not settable (model default)",
                "model_options": model_options, "hand_over": True, "kq_file": R.kq_file.name,
                "checker_tools": tools_digest(TOOL_SPECS),
                "checker_rules_sha256": hashlib.sha256((READING_RULES + LOOKUP_RULES).encode()).hexdigest(),
                "machine": "FASTER", "slurm_job": R.job}
    vr.save_json(R.run_dir / f"exec_manifest_{R.commit}.json", manifest)

    def run_case(qid: str) -> dict:
        q = R.questions[qid]
        plan = plans[qid]
        n0 = len(ask0.calls)
        t0 = time.time()
        if plan["net"] is None or plan["problems"]:
            return ec.make_exec_record(qid, q, plan["spec"], plan["net"], None, None, [], 0.0, None)
        verifiers = build_verifiers(tables=table_list, kg=kg, retriever=retriever, ask=ask0,
                                    query=q, hand_over=True, model_options=model_options)
        trace = execute(plan["net"], verifiers)
        answer = compose(q, plan["net"], trace)
        rec = ec.make_exec_record(qid, q, plan["spec"], plan["net"], trace, answer,
                                  ask0.calls[n0:], time.time() - t0, None)
        rec["cost_usd"] = ac.cost_usd(ask0.calls[n0:], CHECKER_MODEL)
        return rec

    done = {r["case_id"]: r for r in vr.load_json(exec_file, {}).get("records", [])
            if r["case_id"] in R.questions and r.get("question") == R.questions[r["case_id"]]
            and vr.same_json(r.get("spec"), records[r["case_id"]].get("spec")) and not r.get("error")}
    todo = ([q for q in R.dev_ids if q not in done]
            + [q for q in R.questions if q not in R.dev_ids and q not in done])
    say(f"{len(done)} already executed (from {exec_file.name}), {len(todo)} to execute")
    for i, qid in enumerate(todo, 1):
        try:
            r = run_case(qid)
        except Exception as e:                                   # noqa: BLE001
            r = {"case_id": qid, "question": R.questions[qid], "spec": records[qid].get("spec"),
                 "certificates": [], "waves": [], "terminal": None, "answer": None, "calls": [],
                 "seconds": 0.0, "error": repr(e)}
        done[qid] = r
        vr.save_json(exec_file, {"manifest": manifest, "records": [done[q] for q in R.questions if q in done]})
        who = "DEV" if qid in R.case else R.set_name
        say(f"  {i:2d}/{len(todo)} {who:6s} {qid:26s} decision {str(r.get('terminal')):8s} "
            f"checks {sum(1 for x in r['certificates'] if x['kind'] == 'check'):2d} "
            f"lookups {sum(len(x.get('lookups') or []) for x in r['certificates']):3d} "
            f"| {r['seconds']:5.0f}s | ${r.get('cost_usd', 0):.3f}" + (f" | ERROR {r['error']}" if r.get("error") else ""))

    dev_exec = [done[q] for q in R.dev_ids]
    say("\n=== DEV ===")
    ec.print_exec_summary(ec.summarize_execution([r for r in dev_exec if not r.get("error")]))
    say(f"cost of new checker calls in this job: ${ac.cost_usd(ask0.calls, CHECKER_MODEL):.3f}\n")
    for r in dev_exec:
        if r.get("error"):
            say("=" * 110)
            say(r["case_id"], "ERROR:", r["error"])
            continue
        ec.print_execution(r)
        say(f"cost: ${r.get('cost_usd', 0):.4f}\n")

    # the answers to the other questions, for scoring outside the pipeline (the notebook's CELL 14)
    other = [done[q] for q in R.questions if q not in R.dev_ids]
    say(f"=== {R.set_name} questions: {len(other)} ===")
    vr.print_answers(other)
    stamp = time.strftime("%Y%m%d_%H%M")
    answers_file = R.run_dir / f"answers_{R.set_name}_{stamp}.txt"
    answers_file.write_text("\n".join(vr.answer_line(r) for r in other) + "\n")
    result_file = R.run_dir / f"vine_run_{stamp}.json"
    check_file = Path(CFG.base_dir) / "retrieval_dev_results_faster" / f"retrieval_check_r{R.retr_commit}_s{R.store_tag}.json"
    vr.save_json(result_file, {
        "commit": R.commit, "retrieval_commit": R.retr_commit, "store": R.store_tag,
        "retrieval_settings": R.settings,
        "retrieval_check": {"file": check_file.name, "gate": vr.load_json(check_file, {}).get("gate")},
        "parse_manifest": vr.load_json(R.run_dir / "parse_manifest.json", {}), "exec_manifest": manifest,
        "plans": {q: records[q] for q in R.questions}, "executions": {q: done[q] for q in R.questions}})
    say("\nsaved ->", answers_file)
    say("saved ->", result_file)
    errors = [q for q in R.questions if done[q].get("error")]
    if errors:
        say(f"\n{len(errors)} questions stopped with an error: {errors}. Submit the execute stage again; "
            "it runs only those.")
        return 1
    say("\nEXECUTE STAGE FINISHED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=("retrieval", "parse", "execute"))
    args = ap.parse_args()
    say(f"=== VINE on FASTER: {args.stage} | {time.strftime('%Y-%m-%d %H:%M:%S')} | job {os.environ.get('SLURM_JOB_ID', '-')} "
        f"| node {os.uname().nodename} ===")
    R = Run()
    return {"retrieval": stage_retrieval, "parse": stage_parse, "execute": stage_execute}[args.stage](R)


if __name__ == "__main__":
    sys.exit(main())
