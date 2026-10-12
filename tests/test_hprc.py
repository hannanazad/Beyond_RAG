"""hprc/: the FASTER run. Made-up data only."""
import importlib
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def test_local_data_path_finds_colab_files_under_this_base():
    from mrag.config import CFG
    with tempfile.TemporaryDirectory() as d:
        old = CFG.base_dir
        CFG.base_dir = Path(d)
        try:
            (Path(d) / "figures").mkdir()
            (Path(d) / "figures" / "f.png").write_bytes(b"x")
            colab = "/content/drive/MyDrive/Beyond_RAG/figures/f.png"
            assert CFG.local_data_path(colab) == str(Path(d) / "figures" / "f.png")
            # a path that exists, a path elsewhere, and an empty one are unchanged
            here = str(Path(d) / "figures" / "f.png")
            assert CFG.local_data_path(here) == here
            assert CFG.local_data_path("/elsewhere/f.png") == "/elsewhere/f.png"
            assert CFG.local_data_path("") == ""
        finally:
            CFG.base_dir = old


def test_launch_can_leave_other_servers_running():
    from mrag.vine import vllm_client as vc
    calls = []
    saved = (vc.stop_servers, vc.start_server, vc.wait_until_ready)

    class P:
        pid, returncode = 12345, None
        def poll(self): return None

    try:
        vc.stop_servers = lambda *a, **k: calls.append("stop_all")
        vc.start_server = lambda cmd, log, env=None: P()
        vc.wait_until_ready = lambda *a, **k: 1.0
        vc.launch("vllm", "M", "/tmp/none.log", port=8001, say=lambda m: None, stop_others=False)
        assert calls == []
        vc.launch("vllm", "M", "/tmp/none.log", port=8001, say=lambda m: None)
        assert calls == ["stop_all"]           # the Colab default is unchanged
    finally:
        vc.stop_servers, vc.start_server, vc.wait_until_ready = saved


def test_vllm_pids_are_only_this_users():
    from mrag.vine import vllm_client as vc
    uid = os.getuid()
    for pid in vc._vllm_pids():
        assert Path(f"/proc/{pid}").stat().st_uid == uid


def test_sample_questions_come_from_the_notebook_text_only():
    sys.path.insert(0, str(REPO / "hprc"))
    sys.path.insert(0, str(REPO / "evaluation"))
    V = importlib.import_module("vine_hprc")
    s = V.sample_questions()
    assert sorted(s) == [f"SAMPLE{i:03d}" for i in range(2, 22)]
    assert all(isinstance(v, str) and len(v) > 100 for v in s.values())


# --------------------------------------------------------------------------- #
# The repeat run (VINE_REPEAT): same Kq, its own folder and model cache, DEV only
# --------------------------------------------------------------------------- #
class _Patched:
    """Set attributes and environment variables; put them all back after."""

    def __init__(self, attrs=(), env=None):
        self.attrs, self.env, self.saved, self.saved_env = list(attrs), dict(env or {}), [], {}

    def __enter__(self):
        for obj, name, value in self.attrs:
            self.saved.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)
        for k, v in self.env.items():
            self.saved_env[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for obj, name, value in reversed(self.saved):
            setattr(obj, name, value)
        for k, v in self.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _vine_hprc():
    sys.path.insert(0, str(REPO / "hprc"))
    sys.path.insert(0, str(REPO / "evaluation"))
    return importlib.import_module("vine_hprc")


def _run(base, repeat=None, questions=None):
    from mrag.config import CFG
    V = _vine_hprc()
    with _Patched([(CFG, "base_dir", Path(base))], {"VINE_REPEAT": repeat, "VINE_QUESTIONS": questions}):
        return V.Run()


def test_repeat_run_has_its_own_folder_and_cache_but_the_same_kq():
    with tempfile.TemporaryDirectory() as d:
        first = _run(d)
        assert first.repeat == "" and first.runs == Path(d) / "parser_runs_faster"
        assert first.model_cache == first.runs / "model_cache"
        assert len(first.questions) == 31 and len(first.dev_ids) == 11
        rep = _run(d, repeat="r1")
        assert rep.runs == Path(d) / "parser_runs_faster" / "repeat_r1"
        assert rep.model_cache == rep.runs / "model_cache" != first.model_cache
        assert rep.kq_file == first.kq_file                      # the same Kq file
        assert rep.run_dir.name == first.run_dir.name            # the same code, store, instructions
        assert rep.run_dir.parent == rep.runs and rep.run_dir.is_dir()
        assert rep.dev_ids == first.dev_ids and sorted(rep.questions) == sorted(first.dev_ids)
        assert rep.answer_set == {}
        for q in rep.dev_ids:
            assert rep.questions[q] == first.questions[q]
        # an empty value is a normal run
        assert _run(d, repeat="  ").runs == first.runs


def test_repeat_run_refuses_a_bad_name_and_the_sealed_questions():
    with tempfile.TemporaryDirectory() as d:
        for bad in ("../x", "a b", "x/y", "a" * 41):
            try:
                _run(d, repeat=bad)
            except AssertionError:
                continue
            raise AssertionError(f"the name {bad!r} was accepted")
        sealed = Path(d) / "sealed.json"
        sealed.write_text('{"VQ999": "a question"}')
        try:
            _run(d, repeat="r1", questions=str(sealed))
        except AssertionError:
            pass
        else:
            raise AssertionError("a repeat run took VINE_QUESTIONS")
        assert not (Path(d) / "parser_runs_faster" / "repeat_x").exists()


def test_repeat_run_makes_plans_only():
    from mrag.config import CFG
    V = _vine_hprc()
    called = []
    with tempfile.TemporaryDirectory() as d:
        fake = {s: (lambda R, s=s: called.append((s, R.repeat)) or 0) for s in ("retrieval", "parse", "execute")}
        with _Patched([(CFG, "base_dir", Path(d)), (V, "stage_retrieval", fake["retrieval"]),
                       (V, "stage_parse", fake["parse"]), (V, "stage_execute", fake["execute"])],
                      {"VINE_REPEAT": "r1", "VINE_QUESTIONS": None}):
            for stage in ("retrieval", "execute"):
                with _Patched([(sys, "argv", ["vine_hprc.py", stage])]):
                    assert V.main() == 2
            assert called == []
            with _Patched([(sys, "argv", ["vine_hprc.py", "parse"])]):
                assert V.main() == 0
            assert called == [("parse", "r1")]


def test_repeat_parse_stage_reads_the_shared_kq_and_writes_only_its_own_folder():
    """stage_parse itself, with the servers, the model and the graph faked:
    only the 11 DEV questions are parsed, every model client is built on the
    repeat run's own cache, and the plans land in the repeat folder."""
    import json
    from mrag.config import CFG
    from mrag import kg_vine
    from mrag.vine import table_data, vllm_client as vc
    import mrag.vine.parser as parser_mod
    V = _vine_hprc()
    caches, prompts = [], []

    def fake_make_ask_vllm(url, name, **k):
        caches.append(k.get("cache_dir"))

        def ask(prompt, images=None):
            prompts.append(prompt)
            ask.last = {"cache_key": "k", "cached": False, "finish_reason": "stop", "prompt_sha256": "p"}
            return '{"ok": true}'
        ask.last = None
        return ask

    class FakeBudgetedAsk:
        def __init__(self, make_ask, *a, **k):
            self.ask = make_ask(49152)

        def __call__(self, prompt, images=None):
            return self.ask(prompt, images)

    def fake_parser(ask, **k):
        def parse(question, chunks, section, figures):
            ask("PLAN FOR " + question)
            return None, {"made": True}
        return parse

    def fake_record(qid, q, v, spec, rep, net, secs, case=None):
        return {"case_id": qid, "question": q, "outcome": "valid first time", "attempts": 1, "stats": {},
                "seconds": secs, "calls": [], "spec": None, "raw_replies": [], "problems": []}

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        first = _run(d)
        # the first run's Kq (shared) and its plans/cache, which the repeat must not touch
        kq = {q: {"question": t, "chunks": [], "figures": []} for q, t in first.questions.items()}
        first.kq_file.write_text(json.dumps(kq))
        first.plans_file.write_text(json.dumps({"P01-scenario": {"question": first.questions["P01-scenario"],
                                                                 "outcome": "valid first time"}}))
        before = first.plans_file.read_text()
        hub = base / "hf" / "models--Qwen--Qwen3.8-27B-FP8" / "snapshots" / V.REVISION
        hub.mkdir(parents=True)
        (hub / "config.json").write_text("{}")
        rep = _run(d, repeat="r1")
        patches = [
            (CFG, "base_dir", base),
            (kg_vine, "VineKG", lambda *a, **k: type("KG", (), {"is_known_citation": staticmethod(lambda r: True)})()),
            (table_data, "load", lambda p: []),
            (vc, "launch", lambda *a, **k: {"base_url": "http://127.0.0.1:1", "max_model_len": 73728, "cmd": ["vllm"]}),
            (vc, "make_ask_vllm", fake_make_ask_vllm),
            (vc, "stop_server", lambda s: None),
            (V.vr, "BudgetedAsk", FakeBudgetedAsk),
            (parser_mod, "make_semantic_parser", fake_parser),
            (V.pc, "make_record", fake_record),
            (V.pc, "print_summary", lambda *a: None), (V.pc, "summarize", lambda *a: {}),
            (V.pc, "print_plan", lambda *a: None),
        ]
        env = {"CUDA_VISIBLE_DEVICES": "0,1", "VLLM_ENV": str(base / "venv"), "HF_HUB_CACHE": str(base / "hf"),
               "TMPDIR": str(base / "tmp"), "VINE_REPEAT": "r1", "VINE_QUESTIONS": None}
        with _Patched(patches, env):
            assert V.stage_parse(rep) == 0
        plans = json.loads(rep.plans_file.read_text())
        assert sorted(plans) == sorted(first.dev_ids)                  # the 11 DEV plans, nothing else
        # per GPU: a probe client (no cache at all) and the parser's client (the repeat's own cache)
        assert caches == [None, str(rep.model_cache)] * 2, caches
        assert sorted(p for p in prompts if p.startswith("PLAN FOR ")) == \
            sorted("PLAN FOR " + first.questions[q] for q in first.dev_ids)
        assert first.plans_file.read_text() == before                  # the first run is untouched
        assert (rep.run_dir / "parse_manifest.json").exists()
        assert json.loads((rep.run_dir / "parse_manifest.json").read_text())["kq_file"] == first.kq_file.name


def test_run_sh_repeat_submits_the_parse_stage_only():
    import shutil
    import subprocess
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        scratch, stubs = d / "scratch", d / "stubs"
        (scratch / "vine").mkdir(parents=True)
        (scratch / "vine" / ".done_models").write_text("")
        stubs.mkdir()
        (stubs / "sbatch").write_text('#!/bin/bash\necho "$@" >> "$SIM_LOG"\necho $((RANDOM + 1000))\n')
        (stubs / "sbatch").chmod(0o755)
        log = d / "sbatch.log"
        bash = shutil.which("bash")

        def run(*args, extra=None):
            if log.exists():
                log.unlink()
            env = {"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(d / "home"), "SCRATCH": str(scratch),
                   "USER": "u", "SIM_LOG": str(log), **(extra or {})}
            p = subprocess.run([bash, str(REPO / "hprc" / "run.sh"), *args], env=env,
                               capture_output=True, text=True, timeout=60)
            calls = log.read_text().splitlines() if log.exists() else []
            return p.returncode, p.stdout + p.stderr, calls

        code, out, calls = run("123", "6", "repeat", "r1")
        assert code == 0, out
        assert len(calls) == 1 and "STAGE=parse" in calls[0] and "VINE_REPEAT=r1" in calls[0], calls
        assert "--gres=gpu:a100:6" in calls[0] and "--dependency" not in calls[0]
        assert "compare_plans.py r1" in out
        # no Anthropic key is needed for plans only; a bad or missing name submits nothing
        for args in (("123", "6", "repeat"), ("123", "6", "repeat", "../x"), ("123", "6", "repeat", "a b")):
            code, out, calls = run(*args)
            assert code == 1 and calls == [], (args, out)
        code, out, calls = run("123", "6", "repeat", "r1", extra={"VINE_QUESTIONS": "/x/sealed.json"})
        assert code == 1 and calls == []
        # a normal run: a value of VINE_REPEAT left in the shell is overridden with nothing
        (scratch / "vine" / "anthropic_key").write_text("k")
        code, out, calls = run("123", "8", "parse", extra={"VINE_REPEAT": "left_over"})
        assert code == 0, out
        assert len(calls) == 2 and all("VINE_REPEAT=," in c or c.split("VINE_REPEAT=")[1].startswith(",STAGE")
                                       for c in calls), calls
        assert "STAGE=parse" in calls[0] and "STAGE=execute" in calls[1]


# --------------------------------------------------------------------------- #
# hprc/compare_plans.py, on made-up runs
# --------------------------------------------------------------------------- #
def _compare_mod():
    sys.path.insert(0, str(REPO / "hprc"))
    return importlib.import_module("compare_plans")


def _make_runs(d, n=3, change=None, old_cache=True):
    """A first run and a repeat run 'r1' of n questions, the same unless
    change(qid, plan, reply) alters the repeat's plan or cached reply."""
    import json
    import copy
    runs = Path(d) / "parser_runs_faster"
    folder = "e2e_rabc_sdef_p123"
    manifest = {"commit": "c1", "slurm_job": "1", "gpu": ["A100"] * 8, "servers": 8, "seed": 42,
                "max_tokens": 49152, "server_command": ["vllm", "--port", "1"]}
    plans = {}
    for i in range(n):
        qid = f"P{i:02d}"
        key = f"key{i}"
        plans[qid] = {"case_id": qid, "question": f"question {i}", "outcome": "valid first time", "attempts": 1,
                      "problems": [], "stats": {"obligations": i}, "spec": {"terminal": f"o{i}"},
                      "raw_replies": [f'{{"terminal": "o{i}"}}'], "gpu_slot": i, "seconds": 100.0 + i,
                      "calls": [{"cache_key": key, "cached": False, "prompt_sha256": f"sha{i}",
                                 "finish_reason": "stop", "reasoning_chars": 30, "content_chars": 17}]}
    replies = {f"key{i}": {"content": f'{{"terminal": "o{i}"}}', "reasoning": "thinking about it carefully " + str(i),
                           "finish_reason": "stop", "usage": {"completion_tokens": 500 + i}} for i in range(n)}
    new_plans, new_replies = copy.deepcopy(plans), copy.deepcopy(replies)
    for qid, p in new_plans.items():
        p["gpu_slot"], p["seconds"] = 7, 999.0               # allowed to differ
    if change:
        change(new_plans, new_replies)
    for root, ps, rs, cache in ((runs, plans, replies, old_cache), (runs / "repeat_r1", new_plans, new_replies, True)):
        (root / folder).mkdir(parents=True)
        (root / folder / "plans.json").write_text(json.dumps(ps))
        m = dict(manifest, slurm_job="2", servers=6) if root != runs else manifest
        (root / folder / "parse_manifest.json").write_text(json.dumps(m))
        if cache:
            (root / "model_cache").mkdir()
            for k, r in rs.items():
                (root / "model_cache" / f"{k}.json").write_text(json.dumps(r))
    return runs


def _verdicts(runs):
    code, report = _compare_mod().compare(runs, "r1")
    return code, ({r["case_id"]: r["verdict"] for r in report["folders"][0]["rows"]} if report else None), report


def test_compare_same_plans_on_other_gpus_are_the_same():
    with tempfile.TemporaryDirectory() as d:
        code, v, _ = _verdicts(_make_runs(d))
        assert code == 0 and set(v.values()) == {"SAME"}, v


def test_compare_finds_each_kind_of_difference():
    def change(plans, replies):
        r = replies["key1"]
        r["reasoning"] = r["reasoning"][:10] + "X" + r["reasoning"][11:]        # the model thought differently
        plans["P02"]["calls"][0]["prompt_sha256"] = "other"                     # our input changed
        plans["P03"]["calls"][0]["cache_key"] = "key3b"                          # same prompt, other settings
        replies["key3b"] = replies["key3"]
        plans["P04"]["spec"] = {"terminal": "something else"}                   # same reply, other plan
        plans["P05"]["calls"][0]["cached"] = True                               # a resumed job: a note only
    with tempfile.TemporaryDirectory() as d:
        code, v, report = _verdicts(_make_runs(d, n=6, change=change))
        assert code == 1
        assert v == {"P00": "SAME", "P01": "MODEL REPLY DIFFERS", "P02": "INPUT DIFFERS",
                     "P03": "SETTINGS DIFFER", "P04": "PLAN DIFFERS", "P05": "SAME"}, v
        row = {r["case_id"]: r for r in report["folders"][0]["rows"]}
        assert row["P01"]["where"]["at"] == 10
        assert row["P05"]["notes"]


def test_compare_without_the_first_runs_cache_compares_lengths():
    def change(plans, replies):
        plans["P01"]["calls"][0]["reasoning_chars"] = 31
    with tempfile.TemporaryDirectory() as d:
        code, v, report = _verdicts(_make_runs(d, change=change, old_cache=False))
        assert v == {"P00": "SAME", "P01": "MODEL REPLY DIFFERS", "P02": "SAME"} and code == 1
        assert any("by length only" in n for n in report["folders"][0]["rows"][0]["notes"])


def test_compare_flags_changed_settings_and_a_missing_first_run():
    import json
    import shutil
    with tempfile.TemporaryDirectory() as d:
        runs = _make_runs(d)
        m = runs / "repeat_r1" / "e2e_rabc_sdef_p123" / "parse_manifest.json"
        m.write_text(json.dumps(dict(json.loads(m.read_text()), seed=7)))
        code, v, report = _verdicts(runs)
        assert code == 1 and report["folders"][0]["settings_differ"] == ["seed"]
        shutil.rmtree(runs / "e2e_rabc_sdef_p123")
        assert _verdicts(runs)[0] == 2
        assert _compare_mod().compare(runs, "nothing")[0] == 2



# --------------------------------------------------------------------------- #
# The probe (hprc/repeat_probe.py), with fake servers: a server started fresh
# picks a random "kernel choice"; one started from a copy of another's caches
# keeps that one's choice; with VLLM_BATCH_INVARIANT=1 the choice is fixed.
# Each reply depends on the choice and the prompt.
# --------------------------------------------------------------------------- #
def _probe_mod():
    sys.path.insert(0, str(REPO / "hprc"))
    return importlib.import_module("repeat_probe")


def _probe_world(d, fail_setup=None, slow_a1=0.0):
    import hashlib
    import json
    import uuid
    import threading
    import time
    P = _probe_mod()
    runs = Path(d) / "parser_runs_faster"
    folder = "e2e_rX_sY_pZ"
    (runs / folder).mkdir(parents=True)
    (runs / "model_cache").mkdir()
    plans = {}
    for qid in P.PROBE_CASES:
        prompt = f"the whole prompt of {qid} " * 50
        sha = hashlib.sha256(prompt.encode()).hexdigest()
        plans[qid] = {"calls": [{"cache_key": "first_" + qid, "prompt_sha256": sha}]}
        (runs / "model_cache" / f"first_{qid}.json").write_text(json.dumps(
            {"prompt": prompt, "reasoning": "first run thinking about " + qid, "max_tokens": 49152}))
    (runs / folder / "plans.json").write_text(json.dumps(plans))
    w = {"kernel": {}, "launches": [], "sent": [], "stopped": [], "order": [], "lock": threading.Lock()}

    def launch(vllm_bin, model_path, log_path, port, env, say, extra=(), **kw):
        own = Path(env["VLLM_CACHE_ROOT"]).parent
        label = Path(log_path).stem
        with w["lock"]:
            w["launches"].append({"label": label, "env": dict(env), "extra": list(extra), "kw": dict(kw),
                                  "port": port})
            w["order"].append(("start", label))
        if fail_setup and ((fail_setup == "batch_invariant" and env.get("VLLM_BATCH_INVARIANT"))
                           or fail_setup == label):
            raise RuntimeError(f"the vLLM server exited with code 1 ({label})")
        if label == "A1" and slow_a1:
            time.sleep(slow_a1)
        own.mkdir(parents=True, exist_ok=True)
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(log_path).write_text("INFO torch.compile took 40.0 s in total\n")
        if (own / "kernel").exists():
            k = (own / "kernel").read_text()
        elif env.get("VLLM_BATCH_INVARIANT") == "1":
            k = "fixed"
        else:
            k = uuid.uuid4().hex[:8]
        (own / "kernel").write_text(k)
        url = f"http://fake/{port}"
        w["kernel"][url] = k
        return {"base_url": url, "max_model_len": 73728, "proc": None}

    def stop(server):
        w["stopped"].append(server["base_url"])

    def make_ask(base_url, cache_dir=None, **kw):
        assert kw["max_tokens"] == P.PROBE_TOKENS and kw["seed"] == 42
        cache = Path(cache_dir)
        cache.mkdir(parents=True, exist_ok=True)

        def ask(prompt, images=None):
            sha = hashlib.sha256(prompt.encode()).hexdigest()
            key = hashlib.sha256((prompt + cache_dir).encode()).hexdigest()
            assert not (cache / f"{key}.json").exists(), "a probe reply was read from a cache"
            text = f"thinking with kernels {w['kernel'][base_url]} about {sha[:8]}"
            (cache / f"{key}.json").write_text(json.dumps(
                {"reasoning": text, "content": "", "finish_reason": "length", "prompt_sha256": sha,
                 "usage": {"completion_tokens": 4096}}))
            with w["lock"]:
                w["sent"].append((base_url, prompt))
                w["order"].append(("ask", base_url))
            ask.last = {"cache_key": key}
            return ""
        return ask

    def go(name="p1"):
        return P.run_probe(name, runs, folder, ["0", "1", "2", "3"], launch=launch, stop=stop, make_ask=make_ask,
                           server_env=lambda gpu, own: {"CUDA_VISIBLE_DEVICES": gpu,
                                                        "VLLM_CACHE_ROOT": str(own / "vllm")},
                           server_kwargs={"served_name": "parser", "max_model_len": 73728, "seed": 42},
                           vllm_bin="vllm", model_path="M", tmp=Path(d) / "tmp", port0=21000,
                           ask_kwargs={"max_tokens": P.PROBE_TOKENS, "seed": 42}, say=lambda m: None, settle=0)
    return P, runs, plans, w, go


def _rows(report):
    return {r["title"]: (r["same"], r["of"]) for r in report["comparisons"]}


def test_probe_tells_the_setups_apart():
    import json
    with tempfile.TemporaryDirectory() as d:
        # A1 is slow to start, so A3 (which copies A1's caches) has to wait for it
        P, runs, plans, w, go = _probe_world(d, slow_a1=1.5)
        report = go()
        assert _rows(report) == {
            "the same server, asked twice": (3, 3),
            "two servers started fresh, as now": (0, 3),
            "a server started from a copy of A1's caches": (3, 3),
            "two fresh servers, VLLM_BATCH_INVARIANT=1": (3, 3),
            "two fresh servers, --enforce-eager": (0, 3)}, _rows(report)
        L = {x["label"]: x for x in w["launches"]}
        assert sorted(L) == ["A1", "A2", "A3", "B1", "B2", "C1", "C2"]
        assert all(x["env"]["TRITON_CACHE_AUTOTUNING"] == "1" for x in L.values())
        assert sorted(l for l, x in L.items() if x["env"].get("VLLM_BATCH_INVARIANT") == "1") == ["B1", "B2"]
        assert sorted(l for l, x in L.items() if "--enforce-eager" in x["extra"]) == ["C1", "C2"]
        assert all(x["kw"] == {"served_name": "parser", "max_model_len": 73728, "seed": 42} for x in L.values())
        assert len({x["port"] for x in L.values()}) == 7                    # no two servers share a port
        # every prompt sent is one the first run sent; 7 servers x 3, A1 twice
        first = {json.loads((runs / "model_cache" / f"first_{q}.json").read_text())["prompt"] for q in plans}
        assert len(w["sent"]) == 8 * 3 and {p for _, p in w["sent"]} == first
        assert len(w["stopped"]) == 7
        # A3 starts only after A1 has answered all three once
        i_a3 = w["order"].index(("start", "A3"))
        a1_url = "http://fake/21000"
        assert sum(1 for o in w["order"][:i_a3] if o == ("ask", a1_url)) >= 3
        saved = json.loads((runs / "probe_p1" / "probe.json").read_text())
        assert saved["report"]["comparisons"][0]["same"] == 3 and "A1" in saved["replies"]
        agree = saved["report"]["agreement_with_earlier_runs"]
        assert set(agree) == set(P.PROBE_CASES) and "first run" in agree["P44-scenario"]["A1 round 1"]
        # a used name is refused, so old replies can never be read back as new ones
        try:
            go()
        except AssertionError:
            pass
        else:
            raise AssertionError("the same probe name was accepted twice")


def test_probe_carries_on_when_a_setup_cannot_start():
    import threading
    with tempfile.TemporaryDirectory() as d:
        P, runs, plans, w, go = _probe_world(d, fail_setup="batch_invariant")
        report = go()
        rows = {r["title"]: r for r in report["comparisons"]}
        assert rows["two fresh servers, VLLM_BATCH_INVARIANT=1"]["of"] == 0
        assert rows["two fresh servers, VLLM_BATCH_INVARIANT=1"]["problems"]
        assert (rows["the same server, asked twice"]["same"], rows["two fresh servers, --enforce-eager"]["of"]) == (3, 3)
    with tempfile.TemporaryDirectory() as d:
        # A1 cannot start: A3 (which copies A1's caches) must not wait for ever
        P, runs, plans, w, go = _probe_world(d, fail_setup="A1")
        out = {}
        t = threading.Thread(target=lambda: out.setdefault("r", go()))
        t.start()
        t.join(timeout=60)
        assert not t.is_alive(), "the probe hung when A1 did not start"
        rows = {r["title"]: r for r in out["r"]["comparisons"]}
        assert rows["the same server, asked twice"]["of"] == 0
        assert rows["a server started from a copy of A1's caches"]["of"] == 0
        assert rows["two fresh servers, VLLM_BATCH_INVARIANT=1"]["same"] == 3


def test_probe_needs_the_first_runs_prompts():
    with tempfile.TemporaryDirectory() as d:
        P, runs, plans, w, go = _probe_world(d)
        (runs / "model_cache" / "first_P47-scenario.json").unlink()
        try:
            go()
        except AssertionError as e:
            assert "P47-scenario" in str(e)
        else:
            raise AssertionError("the probe ran without the first run's prompt")
        assert w["launches"] == []                                         # nothing was started


def test_parser_server_settings_are_unchanged():
    V = _vine_hprc()
    assert V.PARSER_SERVER == {"served_name": "parser", "max_model_len": 73728, "min_model_len": 65536,
                               "gpu_memory_utilization": 0.90, "seed": 42, "stop_others": False}
    assert V.parser_server_env("3", Path("/x")) == {
        "CUDA_VISIBLE_DEVICES": "3", "HF_HUB_OFFLINE": "1", "VLLM_USE_FLASHINFER_SAMPLER": "0",
        "VLLM_CACHE_ROOT": "/x/vllm", "TRITON_CACHE_DIR": "/x/triton", "TORCHINDUCTOR_CACHE_DIR": "/x/inductor",
        "FLASHINFER_WORKSPACE_BASE": "/x"}
    assert V.first_port("3198937") == 20000 + (3198937 % 400) * 10 and V.first_port("nojob") == 20000


def test_probe_stage_runs_only_with_its_name():
    from mrag.config import CFG
    V = _vine_hprc()
    called = []
    with tempfile.TemporaryDirectory() as d:
        stages = [(V, n, (lambda R, n=n: called.append(n) or 0))
                  for n in ("stage_retrieval", "stage_parse", "stage_execute", "stage_probe")]
        with _Patched([(CFG, "base_dir", Path(d))] + stages, {"VINE_REPEAT": None, "VINE_QUESTIONS": None,
                                                             "VINE_PROBE": None}):
            with _Patched([(sys, "argv", ["vine_hprc.py", "probe"])]):
                assert V.main() == 2                      # no VINE_PROBE
            with _Patched([], {"VINE_PROBE": "p1"}):
                for stage in ("retrieval", "parse", "execute"):
                    with _Patched([(sys, "argv", ["vine_hprc.py", stage])]):
                        assert V.main() == 2
                with _Patched([(sys, "argv", ["vine_hprc.py", "probe"])]):
                    assert V.main() == 0
            assert called == ["stage_probe"]
            with _Patched([], {"VINE_PROBE": "p1", "VINE_REPEAT": "r1"}):
                try:
                    V.Run()
                except AssertionError:
                    pass
                else:
                    raise AssertionError("VINE_PROBE and VINE_REPEAT were both accepted")


def test_run_sh_probe_submits_one_job_on_four_gpus():
    import shutil
    import subprocess
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        scratch, stubs = d / "scratch", d / "stubs"
        (scratch / "vine").mkdir(parents=True)
        (scratch / "vine" / ".done_models").write_text("")
        stubs.mkdir()
        (stubs / "sbatch").write_text('#!/bin/bash\necho "$@" >> "$SIM_LOG"\necho $((RANDOM + 1000))\n')
        (stubs / "sbatch").chmod(0o755)
        log = d / "sbatch.log"

        def run(*args, extra=None):
            if log.exists():
                log.unlink()
            env = {"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(d / "home"), "SCRATCH": str(scratch),
                   "USER": "u", "SIM_LOG": str(log), **(extra or {})}
            p = subprocess.run([shutil.which("bash"), str(REPO / "hprc" / "run.sh"), *args], env=env,
                               capture_output=True, text=True, timeout=60)
            return p.returncode, p.stdout + p.stderr, (log.read_text().splitlines() if log.exists() else [])

        code, out, calls = run("123", "4", "probe", "p1", extra={"VINE_REPEAT": "left_over"})
        assert code == 0, out
        assert len(calls) == 1, calls
        c = calls[0]
        assert "STAGE=probe" in c and "VINE_PROBE=p1" in c and "VINE_REPEAT=," in c and "--gres=gpu:a100:4" in c
        assert "--job-name=vine_probe" in c and "--dependency" not in c
        for args in (("123", "8", "probe", "p1"), ("123", "4", "probe"), ("123", "4", "probe", "a/b")):
            code, out, calls = run(*args)
            assert code == 1 and calls == [], (args, out)
        (scratch / "Beyond_RAG" / "parser_runs_faster" / "probe_p1").mkdir(parents=True)
        code, out, calls = run("123", "4", "probe", "p1")
        assert code == 1 and calls == [] and "used already" in out
        # a normal run never carries a probe name
        (scratch / "vine" / "anthropic_key").write_text("k")
        code, out, calls = run("123", "8", "execute", extra={"VINE_PROBE": "left_over"})
        assert code == 0 and len(calls) == 1 and calls[0].rstrip().split("VINE_PROBE=")[1].startswith(",STAGE")



def test_probe_stage_passes_the_parse_stages_settings():
    from mrag.config import CFG
    from mrag.vine import vllm_client as vc
    V = _vine_hprc()
    P = _probe_mod()
    got = {}

    def fake_run_probe(name, runs, folder, gpus, **kw):
        got.update(name=name, runs=runs, folder=folder, gpus=gpus, **kw)
        return {"comparisons": [{"of": 3}]}

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        hub = base / "hf" / "models--Qwen--Qwen3.8-27B-FP8" / "snapshots" / V.REVISION
        hub.mkdir(parents=True)
        (hub / "config.json").write_text("{}")
        env = {"VINE_PROBE": "p1", "VINE_REPEAT": None, "VINE_QUESTIONS": None, "CUDA_VISIBLE_DEVICES": "4,5,6,7",
               "VLLM_ENV": str(base / "venv"), "HF_HUB_CACHE": str(base / "hf"), "TMPDIR": str(base / "tmp"),
               "SLURM_JOB_ID": "3199700"}
        with _Patched([(CFG, "base_dir", base), (P, "run_probe", fake_run_probe)], env):
            R = V.Run()
            assert V.stage_probe(R) == 0
        first = _run(d)
    assert got["name"] == "p1" and got["gpus"] == ["4", "5", "6", "7"]
    assert got["runs"] == first.runs and got["folder"] == first.run_dir.name     # the first run's folder
    assert got["launch"] is vc.launch and got["stop"] is vc.stop_server and got["make_ask"] is vc.make_ask_vllm
    assert got["server_kwargs"] is V.PARSER_SERVER and got["server_env"] is V.parser_server_env
    assert got["ask_kwargs"] == {"model_id": V.MODEL_ID, "revision": V.REVISION, "engine": "vllm 0.31.0",
                                 "seed": 42, "max_tokens": P.PROBE_TOKENS, "reasoning_effort": "xhigh"}
    assert got["port0"] == V.first_port("3199700") and got["tmp"] == base / "tmp"
    assert got["vllm_bin"] == str(base / "venv" / "bin" / "vllm") and got["model_path"] == str(hub)


if __name__ == "__main__":
    for _name, _f in sorted(globals().items()):
        if _name.startswith("test_") and callable(_f):
            _f()
            print("ok", _name)
    print("ALL HPRC TESTS PASSED")
