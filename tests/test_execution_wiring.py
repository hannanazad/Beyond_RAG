"""The wiring execution needs: pointed evidence, the hand-over, the checker's
API client, reading plans back from the cache, and the server start-up.

Everything here is made up for the test (ids, claims, files). No sample
question, gold answer or MUTCD text is used.
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import networkx as nx

from mrag.vine import (Authority, Certificate, CertificateStore, NetworkSpec, Operation,
                       Status, instantiate)
from mrag.vine.pointers import paragraph_numbers, pointed_evidence
from mrag.vine.model_verifiers import make_llm_verifier, make_vlm_verifier
from mrag.vine.run import build_verifiers, hand_over_when_undecided
from mrag.vine import vllm_client as vc

T, F, U = Status.TRUE, Status.FALSE, Status.UNKNOWN

# ---- 1. paragraph numbers in a hint ---------------------------------------------
assert paragraph_numbers("05") == [5]
assert paragraph_numbers("3-5") == [3, 4, 5]
assert paragraph_numbers("2, 4") == [2, 4]
assert paragraph_numbers("1-20") == [1, 2, 3, 4, 5, 6], "a range is cut at six"
assert paragraph_numbers("") == [] and paragraph_numbers(None) == []
assert paragraph_numbers("paragraph 7") == [7]
print("1. paragraph numbers read from hints")

# ---- a tiny made-up manual -------------------------------------------------------
CHUNKS = {f"X{i}": {"chunk_id": f"X{i}", "section_id": "9Z.01", "text": f"made-up provision {i}",
                    "content_type": "Standard"} for i in range(1, 40)}
CHUNKS["N1"] = {"chunk_id": "N1", "section_id": "9Z.02", "text": "note to the made-up table",
                "content_type": "Standard"}


class KG:
    def __init__(self):
        self.g = nx.MultiDiGraph()
        self.g.add_node("figure:TABLE 9Z-1", id="Table 9Z-1", caption="made-up table",
                        image_path="", image_paths=["/nowhere/a.png"], n_sheets=1)

    def chunks_for_paragraph(self, sec, n):
        return [f"X{n}"] if sec == "9Z.01" else []

    def chunks_for_section(self, sec):
        return [f"X{i}" for i in range(1, 30)] if sec == "9Z.01" else ["X30", "X31"]

    def note_chunks_for(self, ident):
        return ["N1"] if ident == "Table 9Z-1" else []

    def figure(self, fid):
        return "figure:TABLE 9Z-1" if fid == "Table 9Z-1" else None


class Store:
    def fetch_chunks_by_ids(self, name, ids, default_score=0.0):
        return [{"payload": CHUNKS[i], "score": default_score} for i in ids if i in CHUNKS]


class Retriever:
    def __init__(self, searched=(), figures=()):
        self.kg, self.store = KG(), Store()
        self._searched, self._figures = list(searched), list(figures)
        self.seen_certificates = None

    def retrieve_for_obligation(self, query, obligation, certificates=None, top_k=None):
        self.seen_certificates = certificates
        return SimpleNamespace(chunks=[dict(CHUNKS[i]) for i in self._searched],
                               figures=list(self._figures), debug={})


# ---- 2. the pointer lookup -------------------------------------------------------
got = pointed_evidence(Retriever(), source_chunk="X9",
                       hints=[{"type": "section", "id": "9Z.01", "paragraph": "3-4"},
                              {"type": "section", "id": "9Z.02"},
                              {"type": "section", "id": "9Z.01"},           # 29 chunks: too big
                              {"type": "table", "id": "Table 9Z-1"},
                              {"type": "column", "id": "Speed"}],
                       collection="chunks")
ids = [c["chunk_id"] for c in got["chunks"]]
assert ids == ["X9", "X3", "X4", "X30", "X31", "N1"], ids
assert all(c["source"] == "obligation_pointer" for c in got["chunks"])
assert [f["figure_id"] for f in got["figures"]] == ["Table 9Z-1"]
assert got["debug"]["sections_too_big_to_take_whole"] == [("9Z.01", 29)]
print("2. pointed evidence: source paragraph, hinted paragraphs, small sections, table notes, the table")

# ---- 3. the checker sees pointed evidence first, then the search -----------------
prompts = []


def model(reply_status="TRUE", cite=None):
    def ask(prompt, images=None):
        prompts.append((prompt, list(images or [])))
        ids = [l[1:l.index("]")] for l in prompt.splitlines() if l.startswith("[") and "]" in l]
        return json.dumps({"status": reply_status, "evidence": cite or ids[:1],
                           "confidence": 0.9, "reason": "made-up"})
    return ask


op = Operation("o1", "the made-up sign is red", "s_o1", [], "llm",
               evidence_hint=[{"type": "section", "id": "9Z.01", "paragraph": "2"}],
               source_chunk="X7")
r = Retriever(searched=["X5", "X7", "X6"])
cert = make_llm_verifier(model(), r, query="q")(op, CertificateStore())
first_prompt = prompts[-1][0]
order = [l[1:l.index("]")] for l in first_prompt.splitlines() if l.startswith("[") and "]" in l]
assert order[:2] == ["X7", "X2"], order          # pointed first
assert order.count("X7") == 1 and "X5" in order and "X6" in order, order
assert cert.status is T and cert.provenance["pointed_evidence"] == ["X7", "X2"]
print("3. the checker gets the pointed evidence first, then what the search adds, no repeats")

# pointers off: only the search
prompts.clear()
make_llm_verifier(model(), r, query="q", use_pointers=False)(op, CertificateStore())
order = [l[1:l.index("]")] for l in prompts[-1][0].splitlines() if l.startswith("[") and "]" in l]
assert order == ["X5", "X7", "X6"], order

# the search fails but pointed evidence exists: still checked
class Broken(Retriever):
    def retrieve_for_obligation(self, *a, **k):
        raise RuntimeError("search down")
cert = make_llm_verifier(model(), Broken(), query="q")(op, CertificateStore())
assert cert.status is T and "retrieval_error" in cert.provenance
print("   the search failing does not lose the pointed evidence")

# ---- 4. images: at most max_images, missing files skipped, confidence capped -----
tmp = Path(tempfile.mkdtemp())
pngs = []
for i in range(3):
    p = tmp / f"sheet{i}.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([i]) * 16)
    pngs.append(str(p))
fig = {"figure_id": "Figure 9Z-5", "caption": "made-up figure",
       "image_paths": pngs + [str(tmp / "missing.png")], "n_sheets": 4}
vop = Operation("o2", "the made-up figure shows a circle", "s_o2", [], "vlm")
prompts.clear()
cert = make_vlm_verifier(model(cite=["Figure 9Z-5"]), Retriever(searched=["X1"], figures=[fig]),
                         query="q", max_images=2)(vop, CertificateStore())
assert prompts[-1][1] == pngs[:2], prompts[-1][1]
assert cert.provenance["images_left_out"] == pngs[2:3]
assert cert.provenance["images_missing"] == [str(tmp / "missing.png")]
assert cert.confidence <= 0.5, "part of the figure unseen: confidence is capped"
print("4. image checker: 2 images sent, 1 left out, 1 missing file skipped, confidence capped")

# ---- 5. the hand-over ---------------------------------------------------------------
calls = []
def det(status):
    def v(op, st):
        calls.append("det")
        return Certificate(claim=op.claim, status=status, provenance={"reason": "no table named"})
    return v
def interp(op, st):
    calls.append("llm")
    return Certificate(claim=op.claim, status=F, verifier="llm", provenance={})

c = hand_over_when_undecided(det(U), interp, "calculator")(op, CertificateStore())
assert calls == ["det", "llm"] and c.status is F
assert c.provenance["handed_over_from"] == {"verifier": "calculator", "status": "UNKNOWN",
                                             "reason": "no table named"}
calls.clear()
c = hand_over_when_undecided(det(T), interp, "calculator")(op, CertificateStore())
assert calls == ["det"] and c.status is T, "a definite result is kept; the model is not asked"
print("5. hand-over: UNKNOWN goes to the text checker; TRUE/FALSE stays")

from mrag.vine.table_data import Table
vs = build_verifiers(tables=[], ask=model())
assert "calculator" not in vs, "no tables: no calculator"
vs = build_verifiers(tables=[SimpleNamespace(table_id="Table 9Z-1")], ask=model(), retriever=Retriever())
assert vs["calculator"].__name__ == "verify" and vs["symbolic"].__name__ == "verify"
vs_off = build_verifiers(tables=[SimpleNamespace(table_id="Table 9Z-1")], ask=model(), hand_over=False)
assert vs_off["calculator"].__name__ == "calculate", "hand_over=False leaves the calculator alone"
print("   build_verifiers wraps the calculator and the rule checker only when a model is there")

# ---- 6. the plan's source paragraph reaches the operation -------------------------
spec = NetworkSpec.from_dict({"query": "q", "terminal": "o1", "obligations": [
    {"id": "o1", "claim": "c", "type": "applicability", "authority": "STANDARD",
     "source_chunk": "X7", "evidence_hint": [{"type": "section", "id": "9Z.01"}]}]})
net, problems = instantiate(spec)
assert not problems and net.op("o1").source_chunk == "X7"
print("6. source_chunk is carried from the plan to the operation")

# ---- 7. the parser's client: text-only keys unchanged, cache_only -----------------
class Resp:
    def __init__(self, body, status=200, headers=None):
        self._b, self.status_code, self.headers = body, status, headers or {}
        self.text = json.dumps(body)
    def json(self): return self._b

sent = []
def fake_post(self, url, json=None, timeout=None, headers=None):
    sent.append({"url": url, "json": json, "headers": headers})
    return Resp({"choices": [{"message": {"content": "{\"ok\": true}", "reasoning_content": "hm"},
                              "finish_reason": "stop"}], "usage": {"completion_tokens": 3}})
import requests
requests.Session.post = fake_post
cache = tmp / "cache"
ask = vc.make_ask_vllm("http://x", "parser", model_id="m", revision="r", engine="e",
                       seed=1, max_tokens=10, reasoning_effort="medium", cache_dir=str(cache))
ask("hello", [])
legacy_key = vc._key({"model": "m", "revision": "r", "engine": "e", "prompt": "hello", "seed": 1,
                      "sampling": vc.QWEN_THINKING, "max_tokens": 10, "reasoning_effort": "medium",
                      "enable_thinking": True})
assert (cache / f"{legacy_key}.json").exists(), "the cache key is the one the parser runs used"
ro = vc.make_ask_vllm("http://x", "parser", model_id="m", revision="r", engine="e",
                      seed=1, max_tokens=10, reasoning_effort="medium", cache_dir=str(cache),
                      cache_only=True)
n = len(sent)
assert ro("hello", []) == "{\"ok\": true}" and len(sent) == n
try:
    ro("never asked", [])
    raise AssertionError("cache_only must not call the server")
except vc.NotInCache:
    pass
assert len(sent) == n
print("7. parser client: keys unchanged; cache_only reads saved plans and never calls the server")

# ---- 8. the checker's client (Anthropic API) -------------------------------------
from mrag.vine import anthropic_client as ac
from PIL import Image
big = tmp / "big.png"
Image.new("RGB", (4000, 3000), "white").save(big)
replies = []
def api_post(self, url, headers=None, json=None, timeout=None):
    replies.append({"url": url, "headers": headers, "json": json})
    if len(replies) == 1:
        return Resp({"type": "error"}, status=529, headers={"retry-after": "0"})
    return Resp({"model": "claude-sonnet-5-5", "stop_reason": "end_turn",
                 "content": [{"type": "thinking", "thinking": "let me look"},
                             {"type": "text", "text": "{\"status\": \"TRUE\"}"}],
                 "usage": {"input_tokens": 1000, "output_tokens": 200}},
                headers={"request-id": "req_1"})
requests.Session.post = api_post
os.environ["ANTHROPIC_API_KEY"] = "test-key"
acache = tmp / "acache"
cask = ac.make_ask_anthropic("claude-sonnet-5-5", effort="high", max_tokens=32000,
                             cache_dir=str(acache), say=lambda *a: None)
out = cask("check this", [pngs[0], str(big)])
assert out == "{\"status\": \"TRUE\"}", "only the text blocks are the reply"
assert len(replies) == 2, "an overloaded answer (529) is tried again"
body, head = replies[-1]["json"], replies[-1]["headers"]
assert body["model"] == "claude-sonnet-5-5" and body["max_tokens"] == 32000
assert body["output_config"] == {"effort": "high"}
for banned in ("temperature", "top_p", "top_k", "thinking"):
    assert banned not in body, f"{banned} must not be sent"
blocks = body["messages"][0]["content"]
assert [b["type"] for b in blocks] == ["image", "image", "text"] and blocks[-1]["text"] == "check this"
assert head["x-api-key"] == "test-key" and head["anthropic-version"] == "2023-06-01"
rec = json.loads(next(acache.glob("*.json")).read_text())
assert rec["images"][1]["sent_size"] == [2576, 1932], rec["images"][1]["sent_size"]
assert rec["thinking"] == "let me look" and rec["request_id"] == "req_1"
assert cask.last["usage"]["completion_tokens"] == 200
assert ac.cost_usd(cask.calls) == round((1000 * 2 + 200 * 10) / 1e6, 4)
n = len(replies)
assert cask("check this", [pngs[0], str(big)]) == out and len(replies) == n and cask.last["cached"]
assert ac.cost_usd(cask.calls) == round((1000 * 2 + 200 * 10) / 1e6, 4), "a cached reply costs nothing"
del os.environ["ANTHROPIC_API_KEY"]
ro = ac.make_ask_anthropic("claude-sonnet-5-5", effort="high", max_tokens=32000,
                           cache_dir=str(acache), cache_only=True)
assert ro("check this", [pngs[0], str(big)]) == out, "a cached run needs no API key"
try:
    ro("something new", [])
    raise AssertionError("cache_only must not call the API")
except ac.NotInCache:
    pass
fresh = ac.make_ask_anthropic("claude-sonnet-5-5", cache_dir=None)
try:
    fresh("x", [])
    raise AssertionError("no key: a clear error")
except RuntimeError as e:
    assert "ANTHROPIC_API_KEY" in str(e)
print("8. checker client: images then text, effort set, no temperature; busy -> retried; "
      "large image shrunk to 2576 px; cached replies cost nothing and need no key")

# ---- 9. the server start-up retry ----------------------------------------------------
started = []
class Proc:
    returncode = 1
    def poll(self): return None
    def terminate(self): pass
vc.stop_servers = lambda say=print, wait=0: None
vc.start_server = lambda cmd, log, env=None: (started.append(cmd), Proc())[1]
outcomes = iter([vc.ServerFailed("ValueError: To serve at least one request ... Based on the "
                                 "available memory, the estimated maximum model length is 70000. Try"),
                 12.0])
def wait(base, proc, log, say=print, **k):
    o = next(outcomes)
    if isinstance(o, Exception):
        raise o
    return o
vc.wait_until_ready = wait
vc.log_tail = lambda path, n=40: ""
res = vc.launch("vllm", "M", "/tmp/none.log", max_model_len=73728, min_model_len=65536,
                say=lambda *a: None)
assert res["max_model_len"] == 69632, res["max_model_len"]
assert started[0][started[0].index("--max-model-len") + 1] == "73728"
assert started[1][started[1].index("--max-model-len") + 1] == "69632"
assert all("--language-model-only" in c for c in started)
print("9. too little memory for the window -> started again at the largest length that fits")

print("\nALL EXECUTION WIRING TESTS PASSED")
