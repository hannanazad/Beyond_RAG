"""The gemini_test branch: Gemini 4 Argon writes the plans (VINE_PARSER=gemini).
Made-up data only; no network, no model, no gold.
run: python3 tests/test_gemini_test.py"""
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from mrag.vine import gemini_client as gc  # noqa: E402
import test_hprc as th  # noqa: E402   (its _Patched, _run and _vine_hprc helpers)


# --------------------------------------------------------------------------- #
# the client
# --------------------------------------------------------------------------- #
class Resp:
    def __init__(self, status, data=None, text=""):
        self.status_code, self._data = status, data
        self.text = text or (json.dumps(data) if data is not None else "")

    def json(self):
        return self._data


def reply(text='{"ok": true}', thoughts="thinking it over", finish="STOP"):
    return {"candidates": [{"content": {"parts": [{"text": thoughts, "thought": True}, {"text": text}]},
                            "finishReason": finish}],
            "usageMetadata": {"promptTokenCount": 1200, "candidatesTokenCount": 40, "thoughtsTokenCount": 900,
                              "totalTokenCount": 2140},
            "responseId": "resp-1", "modelVersion": "gemini-4-argon-001"}


class FakePost:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, url, json=None, timeout=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        a = self.answers.pop(0)
        return a if isinstance(a, Resp) else Resp(200, a)


def test_request_has_the_thinking_level_and_no_sampling_settings_and_the_key_only_in_a_header():
    post = FakePost([reply()])
    ask = gc.make_ask_gemini("gemini-4-argon", api_key="SECRET-KEY", post=post, sleep=lambda s: None)
    assert ask("PROMPT", []) == '{"ok": true}'
    c = post.calls[0]
    assert c["url"].endswith("/models/gemini-4-argon:generateContent") and "SECRET-KEY" not in c["url"]
    assert c["headers"]["x-goog-api-key"] == "SECRET-KEY"
    g = c["json"]["generationConfig"]
    assert g == {"maxOutputTokens": 65536, "thinkingConfig": {"thinkingLevel": "high", "includeThoughts": True}}
    assert c["json"]["contents"] == [{"role": "user", "parts": [{"text": "PROMPT"}]}]
    text = json.dumps(c["json"]).lower()
    assert not any(w in text for w in ("temperature", "topp", "top_p", "topk", "seed")), text


def test_reply_keeps_the_thinking_out_and_maps_finish_and_usage():
    for finish, mapped in (("STOP", "stop"), ("MAX_TOKENS", "length"), ("SAFETY", "safety")):
        ask = gc.make_ask_gemini(api_key="k", post=FakePost([reply(finish=finish)]), sleep=lambda s: None)
        assert ask("p", []) == '{"ok": true}'
        last = ask.last
        assert last["finish_reason"] == mapped and last["finish_reason_raw"] == finish
        assert last["usage"]["prompt_tokens"] == 1200 and last["usage"]["completion_tokens"] == 940
        assert last["usage"]["thinking_tokens"] == 900 and last["prompt_tokens"] == 1200
        assert last["reasoning_chars"] == len("thinking it over") and last["model_version"] == "gemini-4-argon-001"
    # the plan records read the same fields as from the Qwen client
    from mrag.vine import vllm_client as vc
    qwen_keys = set(vc._summary({}, cached=False))
    assert qwen_keys <= set(ask.last), qwen_keys - set(ask.last)


def test_cache_saves_every_reply_without_the_key_and_reads_it_back():
    with tempfile.TemporaryDirectory() as d:
        post = FakePost([reply()])
        ask = gc.make_ask_gemini(api_key="SECRET-KEY", cache_dir=d, post=post, sleep=lambda s: None)
        ask("same prompt", [])
        assert len(post.calls) == 1 and ask.last["cached"] is False
        files = list(Path(d).glob("*.json"))
        assert len(files) == 1
        rec = json.loads(files[0].read_text())
        assert rec["prompt"] == "same prompt" and rec["reasoning"] == "thinking it over"
        assert rec["response_id"] == "resp-1" and "SECRET-KEY" not in files[0].read_text()
        again = gc.make_ask_gemini(api_key="other", cache_dir=d, post=FakePost([]), sleep=lambda s: None)
        assert again("same prompt", []) == '{"ok": true}' and again.last["cached"] is True
        # another model or thinking level is another cache entry
        other = gc.make_ask_gemini(api_key="k", cache_dir=d, thinking_level="medium",
                                   post=FakePost([reply()]), sleep=lambda s: None)
        other("same prompt", [])
        assert other.last["cached"] is False and len(list(Path(d).glob("*.json"))) == 2


def test_rate_limits_and_server_errors_are_asked_again_but_a_bad_request_is_not():
    slept = []
    post = FakePost([Resp(429, text="quota"), Resp(503, text="busy"), reply()])
    ask = gc.make_ask_gemini(api_key="k", post=post, sleep=slept.append)
    assert ask("p", []) == '{"ok": true}' and ask.last["tries"] == 3 and len(slept) == 2
    post = FakePost([Resp(429, text="quota")] * 3)
    ask = gc.make_ask_gemini(api_key="k", post=post, sleep=lambda s: None, max_tries=3)
    try:
        ask("p", [])
    except gc.GeminiError as e:
        assert "answered 429" in str(e)
    else:
        raise AssertionError("no error after the last try")
    post = FakePost([Resp(400, text="invalid argument: contents")])
    ask = gc.make_ask_gemini(api_key="k", post=post, sleep=lambda s: None)
    try:
        ask("p", [])
    except gc.GeminiError as e:
        # the parse stage does not ask again for this ("answered 400" is in vine_run._NO_RETRY)
        assert "answered 400" in str(e) and len(post.calls) == 1
    else:
        raise AssertionError("a bad request was not an error")


def test_a_refused_output_cap_falls_back_once_and_says_so():
    for words in ("maxOutputTokens must be at most 32768",
                  "Invalid value at 'generation_config.max_output_tokens' (TYPE_INT32), 65536"):
        with tempfile.TemporaryDirectory() as d:
            post = FakePost([Resp(400, text=words), reply(), reply()])
            ask = gc.make_ask_gemini(api_key="k", post=post, sleep=lambda s: None, cache_dir=d)
            ask("p1", [])
            assert [c["json"]["generationConfig"]["maxOutputTokens"] for c in post.calls] == [65536, 32768]
            assert "refused" in ask.last["note"] and ask.last["max_tokens"] == 32768
            ask("p2", [])
            assert post.calls[-1]["json"]["generationConfig"]["maxOutputTokens"] == 32768
            # a reply made with the smaller cap is not reused by a client asking for the larger one
            big = gc.make_ask_gemini(api_key="k", post=FakePost([reply()]), sleep=lambda s: None, cache_dir=d)
            big("p1", [])
            assert big.last["cached"] is False


def test_lost_connections_are_asked_again_only_twice_and_retry_after_is_kept():
    class Boom(Exception):
        pass

    def broken(url, json=None, timeout=None, headers=None):
        broken.n += 1
        raise Boom("read timed out")
    broken.n = 0
    slept = []
    ask = gc.make_ask_gemini(api_key="k", post=broken, sleep=slept.append)
    try:
        ask("p", [])
    except gc.GeminiError as e:
        assert "answered None" in str(e) and "read timed out" in str(e)
    else:
        raise AssertionError("no error")
    assert broken.n == gc.MAX_TRIES_NO_ANSWER == 3 and len(slept) == 2
    r = Resp(429, text="quota")
    r.headers = {"Retry-After": "120"}
    slept = []
    ask = gc.make_ask_gemini(api_key="k", post=FakePost([r, reply()]), sleep=slept.append)
    ask("p", [])
    assert slept and slept[0] >= 120
    body = '{"error": {"code": 429, "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "45s"}]}}'
    slept = []
    ask = gc.make_ask_gemini(api_key="k", post=FakePost([Resp(429, text=body), reply()]), sleep=slept.append)
    ask("p", [])
    assert slept and slept[0] >= 45


def test_output_token_limit_is_read_from_the_model_entry():
    def get(url, headers=None, timeout=None):
        assert url.endswith("/models/gemini-4-argon") and headers == {"x-goog-api-key": "k"}
        return Resp(200, {"name": "models/gemini-4-argon", "outputTokenLimit": 32768})
    assert gc.output_token_limit("gemini-4-argon", api_key="k", get=get) == 32768
    assert gc.output_token_limit("gemini-4-argon", api_key="k", get=lambda *a, **k: Resp(404, text="no")) is None

    def boom(*a, **k):
        raise OSError("no network")
    assert gc.output_token_limit("gemini-4-argon", api_key="k", get=boom) is None


def test_no_answer_images_and_no_key_are_errors():
    ask = gc.make_ask_gemini(api_key="k", post=FakePost([{"promptFeedback": {"blockReason": "OTHER"}}]),
                             sleep=lambda s: None)
    for call in (lambda: ask("p", []), lambda: ask("p", ["/x.png"])):
        try:
            call()
        except gc.GeminiError:
            continue
        raise AssertionError("no error")
    saved = os.environ.pop("GEMINI_API_KEY", None)
    try:
        gc.make_ask_gemini(post=FakePost([]))
    except gc.GeminiError as e:
        assert "GEMINI_API_KEY" in str(e)
    else:
        raise AssertionError("no key was accepted")
    finally:
        if saved is not None:
            os.environ["GEMINI_API_KEY"] = saved


def test_the_key_is_cleaned_and_never_shown_in_an_error():
    key = "AQ.Ab12CD34ef56GH78ij90KL12mn34OP56qr78ST90uv"
    # a paste that brought a line break and other text with it: refused, without showing the key
    for raw in ("\rls -l $SCRATCH/vine/gemini_key" + key, key + " extra", "two keys\n" + key):
        try:
            gc.make_ask_gemini(api_key=raw, post=FakePost([]))
        except gc.GeminiError as e:
            assert key not in str(e) and "Save it again" in str(e), str(e)
        else:
            raise AssertionError(f"{raw!r} was accepted")
    # a line break or spaces at the ends only: cleaned and used
    post = FakePost([reply()])
    ask = gc.make_ask_gemini(api_key="  " + key + "\r\n", post=post, sleep=lambda s: None)
    ask("p", [])
    assert post.calls[0]["headers"]["x-goog-api-key"] == key

    # an error that quotes the header (as requests does for a bad header value) never shows the key
    def quoting(url, json=None, timeout=None, headers=None):
        raise ValueError(f"Invalid header value: {headers['x-goog-api-key']!r}")
    ask = gc.make_ask_gemini(api_key=key, post=quoting, sleep=lambda s: None)
    try:
        ask("p", [])
    except gc.GeminiError as e:
        assert key not in str(e) and "<key>" in str(e), str(e)
    else:
        raise AssertionError("no error")
    # nor an error body that echoes it
    ask = gc.make_ask_gemini(api_key=key, post=FakePost([Resp(403, text=f"bad key {key}")]), sleep=lambda s: None)
    try:
        ask("p", [])
    except gc.GeminiError as e:
        assert key not in str(e) and "<key>" in str(e)
    else:
        raise AssertionError("no error")
    assert gc.output_token_limit(api_key="\rjunk " + key, get=lambda *a, **k: 1 / 0) is None


# --------------------------------------------------------------------------- #
# the run: its own folder and caches; the Qwen runs untouched
# --------------------------------------------------------------------------- #
def _gemini_run(d, questions=None):
    with th._Patched([], {"VINE_PARSER": "gemini"}):
        return th._run(d, questions=questions)


def test_gemini_run_has_its_own_folder_and_caches_and_reads_the_same_kq():
    with tempfile.TemporaryDirectory() as d:
        qwen = th._run(d)
        assert qwen.parser == "qwen"
        assert qwen.model_cache == qwen.runs / "model_cache" and qwen.checker_cache == qwen.runs / "checker_cache"
        g = _gemini_run(d)
        assert g.parser == "gemini"
        assert g.run_dir.name == qwen.run_dir.name + "_gemini4argon" and g.run_dir.parent == qwen.run_dir.parent
        assert g.model_cache == g.run_dir / "model_cache" and g.checker_cache == g.run_dir / "checker_cache"
        assert g.plans_file == g.run_dir / "plans.json" != qwen.plans_file
        assert g.kq_file == qwen.kq_file and g.instructions_sha == qwen.instructions_sha
        assert sorted(g.questions) == sorted(qwen.questions)
        for bad in ("gpt", "Gemini 4"):
            with th._Patched([], {"VINE_PARSER": bad}):
                try:
                    th._run(d)
                except AssertionError:
                    continue
            raise AssertionError(f"VINE_PARSER={bad!r} was accepted")
        with th._Patched([], {"VINE_PARSER": "gemini"}):
            try:
                th._run(d, repeat="r1")
            except AssertionError:
                pass
            else:
                raise AssertionError("a Gemini repeat run was accepted")


def test_gemini_run_never_runs_the_retrieval_stage_and_parses_with_gemini():
    from mrag.config import CFG
    V = th._vine_hprc()
    called = []
    with tempfile.TemporaryDirectory() as d:
        fakes = [(CFG, "base_dir", Path(d)),
                 (V, "stage_retrieval", lambda R: called.append("retrieval") or 0),
                 (V, "_stage_parse", lambda R: called.append("qwen parse") or 0),
                 (V, "_stage_parse_gemini", lambda R: called.append("gemini parse") or 0),
                 (V, "stage_execute", lambda R: called.append("execute") or 0)]
        with th._Patched(fakes, {"VINE_PARSER": "gemini", "VINE_REPEAT": None, "VINE_QUESTIONS": None}):
            for stage, code in (("retrieval", 2), ("probe", 2), ("parse", 0), ("execute", 0)):
                with th._Patched([(sys, "argv", ["vine_hprc.py", stage])]):
                    assert V.main() == code, stage
        assert called == ["gemini parse", "execute"], called
        called.clear()
        with th._Patched(fakes, {"VINE_PARSER": None, "VINE_REPEAT": None, "VINE_QUESTIONS": None}):
            with th._Patched([(sys, "argv", ["vine_hprc.py", "parse"])]):
                assert V.main() == 0
        assert called == ["qwen parse"]                       # unset: the Qwen parse, as before


def test_gemini_parse_stage_writes_only_its_own_folder():
    from mrag.config import CFG
    from mrag import kg_vine
    from mrag.vine import table_data
    import mrag.vine.parser as parser_mod
    V = th._vine_hprc()
    built, prompts = [], []

    fail_for = set()

    def fake_make_ask_gemini(model="", **k):
        built.append((model, k.get("thinking_level"), k.get("max_tokens"), k.get("cache_dir")))

        def ask(prompt, images=None):
            prompts.append(prompt)
            if any(q in prompt for q in fail_for):
                raise gc.GeminiError("Gemini answered 400 after 1 tries: bad")
            ask.last = {"cache_key": "k", "cached": False, "finish_reason": "stop", "model_version": "v1",
                        "usage": {"prompt_tokens": 10, "completion_tokens": 20}, "max_tokens": k.get("max_tokens")}
            ask.calls.append(ask.last)
            return '{"ok": true}'
        ask.last, ask.calls = None, []
        return ask

    def fake_parser(ask, **k):
        def parse(question, chunks, section, figures):
            try:
                ask("PLAN FOR " + question, [])
            except Exception as e:                       # as the real parser records a failed call
                return None, {"failed": f"the model call failed: {e!r}"}
            return None, {"made": True}
        return parse

    def fake_record(qid, q, v, spec, rep, net, secs, case=None):
        if "failed" in rep:
            return {"case_id": qid, "question": q, "outcome": "failed", "attempts": 1, "stats": {},
                    "seconds": secs, "calls": [], "spec": None, "raw_replies": [], "problems": [[rep["failed"]]]}
        return {"case_id": qid, "question": q, "outcome": "valid first time", "attempts": 1, "stats": {},
                "seconds": secs, "calls": [{"finish_reason": "stop", "usage": {"prompt_tokens": 10,
                                                                               "completion_tokens": 20}}],
                "spec": None, "raw_replies": [], "problems": []}

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        qwen = th._run(d)
        kq = {q: {"question": t, "chunks": [], "figures": []} for q, t in qwen.questions.items()}
        qwen.kq_file.write_text(json.dumps(kq))
        qwen.plans_file.write_text(json.dumps({"P01-scenario": {"question": qwen.questions["P01-scenario"],
                                                                "outcome": "valid first time"}}))
        kq_before, plans_before = qwen.kq_file.read_bytes(), qwen.plans_file.read_bytes()
        listing_before = sorted(str(p) for p in qwen.run_dir.rglob("*"))
        g = _gemini_run(d)
        patches = [
            (CFG, "base_dir", base),
            (kg_vine, "VineKG", lambda *a, **k: type("KG", (), {"is_known_citation": staticmethod(lambda r: True)})()),
            (table_data, "load", lambda p: []),
            (V.vr, "BudgetedAsk", None),                    # never used by the Gemini path
            (parser_mod, "make_semantic_parser", fake_parser),
            (V.pc, "make_record", fake_record),
            (V.pc, "print_summary", lambda *a: None), (V.pc, "summarize", lambda *a: {}),
            (V.pc, "print_plan", lambda *a: None),
        ]
        from mrag.vine import gemini_client
        patches.append((gemini_client, "make_ask_gemini", fake_make_ask_gemini))
        patches.append((gemini_client, "output_token_limit", lambda *a, **k: 32768))
        # no key: stops before any call
        with th._Patched(patches, {"VINE_PARSER": "gemini", "GEMINI_API_KEY": None, "CUDA_VISIBLE_DEVICES": None}):
            assert V.stage_parse(g) == 1
        assert built == [] and not g.plans_file.exists()

        # a key file with other text in it: the probe's client refuses it, and the stage stops cleanly
        def refusing(*a, **k):
            raise gc.GeminiError("the Gemini key holds more than one key")
        with th._Patched(patches + [(gemini_client, "make_ask_gemini", refusing)],
                         {"VINE_PARSER": "gemini", "GEMINI_API_KEY": "x y", "CUDA_VISIBLE_DEVICES": None}):
            assert V.stage_parse(g) == 1
        assert not g.plans_file.exists()
        # one question's Gemini call fails: the stage stops (so the execute job does not start) ...
        bad = qwen.questions["P01-scenario"]
        fail_for.add(bad)
        with th._Patched(patches, {"VINE_PARSER": "gemini", "GEMINI_API_KEY": "k", "CUDA_VISIBLE_DEVICES": None}):
            assert V.stage_parse(g) == 1
        assert json.loads(g.plans_file.read_text())["P01-scenario"]["outcome"] == "failed"
        # ... and a second job makes only that plan again, even though the call "answered 400"
        fail_for.clear()
        built.clear()
        n_before = len(prompts)
        with th._Patched(patches, {"VINE_PARSER": "gemini", "GEMINI_API_KEY": "k", "CUDA_VISIBLE_DEVICES": None}):
            assert V.stage_parse(g) == 0
        assert [p for p in prompts[n_before:] if p.startswith("PLAN FOR ")] == ["PLAN FOR " + bad]
        assert len(built) == 2                                        # the probe and one worker
        prompts[:] = prompts[:n_before]
        plans = json.loads(g.plans_file.read_text())
        assert sorted(plans) == sorted(qwen.questions)                # DEV + the questions, all by Gemini
        assert all(r.get("plan_writer") == "gemini-4-argon" for r in plans.values())
        probe, *workers = built
        # the probe: the real settings, no cache; the cap is ours (65,536) whatever the model entry
        # says (32,768 here): the probe and the client's fallback find what the API accepts
        assert probe == ("gemini-4-argon", "high", 65536, None), probe
        assert workers and all(w == ("gemini-4-argon", "high", 65536, str(g.model_cache)) for w in workers)
        assert sorted(p for p in prompts if p.startswith("PLAN FOR ")) == \
            sorted("PLAN FOR " + t for t in qwen.questions.values())
        m = json.loads((g.run_dir / "parse_manifest.json").read_text())
        assert m["parser"] == "gemini" and m["model"] == "gemini-4-argon" and m["thinking_level"] == "high"
        assert m["max_tokens"] == 65536 and m["model_output_limit"] == 32768
        assert m["instructions_sha256"] == qwen.instructions_sha and m["kq_file"] == qwen.kq_file.name
        # the Qwen run's Kq, plans and folder are untouched
        assert qwen.kq_file.read_bytes() == kq_before and qwen.plans_file.read_bytes() == plans_before
        assert sorted(str(p) for p in qwen.run_dir.rglob("*")) == listing_before
        # a second job has nothing to do
        built.clear()
        with th._Patched(patches, {"VINE_PARSER": "gemini", "GEMINI_API_KEY": "k"}):
            assert V.stage_parse(g) == 0
        assert built == []


# --------------------------------------------------------------------------- #
# run.sh and the job script
# --------------------------------------------------------------------------- #
def test_run_sh_gemini_submits_parse_on_one_gpu_then_execute_and_refuses_the_rest():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        scratch, stubs = d / "scratch", d / "stubs"
        (scratch / "vine").mkdir(parents=True)
        (scratch / "vine" / ".done_models").write_text("")
        (scratch / "vine" / "anthropic_key").write_text("a")
        stubs.mkdir()
        (stubs / "sbatch").write_text('#!/bin/bash\necho "$@ KEY_IN_ENV=${GEMINI_API_KEY:-none}" >> "$SIM_LOG"\n'
                                      'echo $((RANDOM + 1000))\n')
        (stubs / "sbatch").chmod(0o755)
        qfile = d / "questions_40.json"
        qfile.write_text('{"SAMPLE002": "a question"}')
        log = d / "sbatch.log"

        def run(*args, extra=None):
            if log.exists():
                log.unlink()
            env = {"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(d / "home"), "SCRATCH": str(scratch),
                   "USER": "u", "SIM_LOG": str(log), **(extra or {})}
            p = subprocess.run([shutil.which("bash"), str(REPO / "hprc" / "run.sh"), *args], env=env,
                               capture_output=True, text=True, timeout=60)
            return p.returncode, p.stdout + p.stderr, (log.read_text().splitlines() if log.exists() else [])

        g = {"VINE_PARSER": "gemini", "VINE_QUESTIONS": str(qfile)}
        code, out, calls = run("123", "2", "parse", extra=g)
        assert code == 1 and calls == [] and "gemini_key" in out, out          # no key yet
        # a key file with other text in it (a paste that took the next line too): refused, key not shown
        (scratch / "vine" / "gemini_key").write_text("\rls -l $SCRATCH/vine/gemini_keyAQ.secretpart123")
        code, out, calls = run("123", "2", "parse", extra=g)
        assert code == 1 and calls == [] and "save it again" in out and "secretpart" not in out, out
        (scratch / "vine" / "gemini_key").write_text("cd\nAQ.secretpart123")          # two lines: refused too
        code, out, calls = run("123", "2", "parse", extra=g)
        assert code == 1 and calls == [] and "secretpart" not in out, out
        # a key in the shell instead of the file: not accepted, and never passed to the jobs
        (scratch / "vine" / "gemini_key").unlink()
        code, out, calls = run("123", "2", "parse", extra={**g, "GEMINI_API_KEY": "AQ.fromshell123"})
        assert code == 1 and calls == [] and "missing" in out, out
        (scratch / "vine" / "gemini_key").write_text("  AQ.secret-part_123\r\n")
        code, out, calls = run("123", "2", "parse", extra={**g, "GEMINI_API_KEY": "AQ.fromshell123"})
        assert code == 0, out
        assert all("KEY_IN_ENV=none" in c for c in calls), calls
        assert len(calls) == 2 and "STAGE=parse" in calls[0] and "STAGE=execute" in calls[1]
        assert "--gres=gpu:a100:1" in calls[0], calls[0]                      # no GPU work: one A100 only
        assert all("VINE_PARSER=gemini" in c and f"VINE_QUESTIONS={qfile}" in c for c in calls)
        assert "GEMINI TEST" in out
        code, out, calls = run("123", "1", "execute", extra=g)
        assert code == 0 and len(calls) == 1 and "STAGE=execute" in calls[0]
        for args, extra in ((("123", "1"), g), (("123", "1", "retrieval"), g),
                            (("123", "1", "repeat", "r1"), g), (("123", "1", "parse"), {"VINE_PARSER": "gemini"}),
                            (("123", "1", "parse"), {"VINE_PARSER": "gemini", "VINE_QUESTIONS": "questions_40.json"}),
                            (("123", "1", "parse"), {"VINE_PARSER": "gpt", "VINE_QUESTIONS": str(qfile)})):
            code, out, calls = run(*args, extra=extra)
            assert code == 1 and calls == [], (args, extra, out)
        # without VINE_PARSER: run.sh says these jobs will stop (the job script stops them), and
        # exports it empty so the job script sees no "gemini"
        code, out, calls = run("123", "2", "parse", extra={"VINE_QUESTIONS": str(qfile)})
        assert code == 0 and "runs the Gemini test only" in out, out
        assert all("VINE_PARSER=," in c for c in calls), calls


def test_gemini_execute_stops_before_any_checker_call_when_the_plans_have_too_many_checks():
    from mrag.config import CFG
    V = th._vine_hprc()
    with tempfile.TemporaryDirectory() as d:
        g = _gemini_run(d)
        many = {"obligations": [{"id": f"o{i}"} for i in range(4)]}
        g.plans_file.write_text(json.dumps({q: {"question": t, "spec": many} for q, t in g.questions.items()}))
        with th._Patched([(CFG, "base_dir", Path(d))],
                         {"VINE_PARSER": "gemini", "VINE_MAX_CHECKS": "10", "ANTHROPIC_API_KEY": None}):
            assert V.stage_execute(g) == 1          # 4 x 31 checks > 10: stopped before the key is even needed


def test_job_script_stops_at_once_unless_it_is_the_gemini_test():
    s = (REPO / "hprc" / "vine_job.slurm").read_text()
    guard = s.index('if [ "${VINE_PARSER:-}" != gemini ]; then')
    assert guard < s.index("module load") and guard < s.index("vine_hprc.py")
    assert "exit 1" in s[guard:s.index("\nfi", guard)]
    bash = shutil.which("bash")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "hprc").mkdir()
        (d / "hprc" / "env.sh").write_text("RETR_ENV=/nonexistent\n")
        (d / "hprc" / "vine_job.slurm").write_text(s)
        for parser, code in (("", 1), ("qwen", 1)):
            p = subprocess.run([bash, str(d / "hprc" / "vine_job.slurm")], capture_output=True, text=True,
                               env={"PATH": "/usr/bin:/bin", "VINE_REPO": str(d), "STAGE": "parse",
                                    "VINE_PARSER": parser})
            assert p.returncode == code and "Gemini test checkout" in p.stdout, (parser, p.stdout, p.stderr)
            assert "job " not in p.stdout                                # stopped before anything else


def test_job_script_reads_the_gemini_key_only_for_the_gemini_parse():
    s = (REPO / "hprc" / "vine_job.slurm").read_text()
    i = s.index('if [ "$STAGE" = parse ] && [ "${VINE_PARSER:-}" = gemini ]; then')
    block = s[i:s.index("fi\nfi", i)]
    assert "module load WebProxy" in block and "$VINE_HOME/gemini_key" in block and "export GEMINI_API_KEY" in block
    run_sh = (REPO / "hprc" / "run.sh").read_text()
    assert "(umask 077; printf" in run_sh and "chmod 600 $SCRATCH/vine/gemini_key" in run_sh
    assert s.count("gemini_key") == block.count("gemini_key") == 2       # read nowhere else


if __name__ == "__main__":
    for _name, _f in sorted(globals().items()):
        if _name.startswith("test_") and callable(_f):
            _f()
            print("ok", _name)
    print("ALL GEMINI TEST TESTS PASSED")
