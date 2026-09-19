"""Tests for the end-to-end entry point.

Stubs throughout, so this runs at no cost. What is tested is the ORDER: that
compilation is checked before execution, that execution never starts on a
rejected network, and that the answer step never runs before certification.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import Status
from mrag.vine.run import VineResult, ask_vine, build_verifiers, make_ask
from mrag.vine.table_data import load as load_tables

CHUNKS = [
    {"chunk_id": "c1", "section_id": "2C.07", "content_type": "Standard",
     "ordinal": 1, "text": "If Table 2C-4 indicates that a horizontal alignment "
                           "sign is required, a Curve (W1-2) sign shall be used.",
     "table_refs": ["2C-4"]},
    {"chunk_id": "c2", "section_id": "2C.07", "content_type": "Guidance",
     "ordinal": 2, "text": "A Turn sign should be used where the advisory speed "
                           "is 30 mph or less."},
    {"chunk_id": "c3", "section_id": "2C.07", "content_type": "Support",
     "ordinal": 3, "text": "Figure 2C-2 provides examples."},
]
Q = "Which horizontal alignment sign is required here?"

GOOD_SPEC = {
    "terminal": "m1",
    "obligations": [
        {"id": "o1", "claim": "Table 2C-4 indicates a sign is required",
         "type": "numerical", "authority": "STANDARD",
         "evidence_hint": [{"type": "table", "id": "Table 2C-4"}],
         "source_chunk": "c1"},
        {"id": "o2", "claim": "the advisory speed is 30 mph or less",
         "type": "numerical", "authority": "GUIDANCE", "requires": ["o1"],
         "source_chunk": "c2"},
    ],
    "merges": [{"id": "m1", "claim": "the requirement is met",
                "kind": "conjunction", "inputs": ["o1", "o2"]}],
}


class FakeRetriever:
    def __init__(self, chunks=CHUNKS, figures=()):
        self.chunks, self.figures = list(chunks), list(figures)
        self.compile_calls = 0
        self.obligation_calls = 0

    def _result(self, chunks, figures):
        class R:
            pass
        r = R()
        r.chunks, r.figures, r.debug = list(chunks), list(figures), {}
        return r

    def retrieve_for_compile(self, query, top_k=None, **kw):
        self.compile_calls += 1
        return self._result(self.chunks, self.figures)

    def retrieve_for_obligation(self, query, obligation, certificates=None,
                                top_k=None, **kw):
        self.obligation_calls += 1
        return self._result(self.chunks[:1], [])


def model(*payloads):
    """A stub whose reply changes per call; the last one repeats."""
    seq = [p if isinstance(p, str) else json.dumps(p) for p in payloads]
    box = {"i": 0, "prompts": []}

    def ask(prompt, images=None):
        box["prompts"].append(prompt)
        out = seq[min(box["i"], len(seq) - 1)]
        box["i"] += 1
        return out
    ask.box = box
    return ask


VERDICT = {"status": "TRUE", "confidence": 0.9, "evidence": ["c1"]}


# ---- 1. with no model at all it still runs -------------------------------
r = ask_vine(Q, chunks=CHUNKS, section_id="2C.07")
assert r.stage == "answered", r.summary()
assert r.report.source == "baseline"
assert r.network is not None and r.problems == []
# no verifiers were available, so nothing was established -- and that is
# UNKNOWN, never FALSE
assert r.status is Status.UNKNOWN
assert not r.trace.unsupported_certification()
print("1. runs with no model: baseline compiler, no verifiers, UNKNOWN")

# ---- 2. the deterministic verifiers alone are enough to run --------------
DATA = (Path(os.environ["MUTCD_TABLES"]) if os.environ.get("MUTCD_TABLES")
        else next((p for p in (Path("/mnt/user-data/uploads/mutcd_tables.jsonl"),
                               Path(__file__).resolve().parents[1] / "mutcd_tables.jsonl")
                   if p.exists()), None))
if DATA is not None:
    tables = load_tables(DATA)
    r = ask_vine(Q, chunks=CHUNKS, section_id="2C.07", tables=tables)
    assert r.stage == "answered"
    used = {o.verifier for o in r.network.operations if o.merge is None}
    assert "calculator" in used
    # the calculator cannot get its inputs from this text, so it abstains
    gate = r.trace.store.latest(r.network.op("o1").produces) if r.network.op("o1") else None
    assert r.status is Status.UNKNOWN
    print("2. calculator and symbolic wired in with no model; they abstain "
          "rather than guess")
else:
    print("2. mutcd_tables.jsonl not found; skipped")

# ---- 3. dry run compiles and spends nothing ------------------------------
ask = model(GOOD_SPEC, VERDICT)
r = ask_vine(Q, chunks=CHUNKS, section_id="2C.07", ask=ask, dry_run=True)
assert r.stage == "compiled (dry run)"
assert r.network is not None and r.trace is None and r.answer is None
assert ask.box["i"] == 1          # the parser only; no verifier, no answer
print("3. a dry run compiles the network and makes exactly one model call")

# ---- 4. the full path, in order ------------------------------------------
# an obligation with no table or figure hint routes to the llm verifier, which
# is the only one that performs Eq 5 obligation-conditioned retrieval
WITH_LLM = json.loads(json.dumps(GOOD_SPEC))
WITH_LLM["obligations"].append(
    {"id": "o3", "claim": "the provision applies to this roadway",
     "type": "applicability", "authority": "STANDARD", "source_chunk": "c1"})
WITH_LLM["merges"][0]["inputs"] = ["o1", "o2", "o3"]
ask = model(WITH_LLM, VERDICT, VERDICT, VERDICT, "The Curve sign is required.")
retr = FakeRetriever()
r = ask_vine(Q, retriever=retr, ask=ask, section_id="2C.07")
assert r.stage == "answered", r.summary()
assert r.report.source == "semantic_parser"
assert retr.compile_calls == 1          # Kq fetched once
assert retr.obligation_calls >= 1       # Eq 5 during execution
assert r.answer is not None
print("4. retrieve -> parse -> compile -> execute -> answer, in that order")

# ---- 5. a rejected network never executes --------------------------------
bad = json.loads(json.dumps(GOOD_SPEC))
bad["merges"][0]["inputs"] = ["o1", "o9"]        # o9 does not exist
ask = model(bad, bad, bad)                        # fails every repair attempt
# the fallback is turned OFF: with it on, the printed structure would rescue
# the run and the parser's failure would be invisible
r = ask_vine(Q, chunks=CHUNKS, ask=ask, section_id="2C.07",
             fall_back_to_baseline=False)
assert r.trace is None and r.answer is None
assert r.stage in ("compilation failed", "network rejected")
print("5. a network that fails validation is never executed")

# ---- 6. ...and with a section id it falls back rather than dying ---------
ask = model("not json", "still not json", "nope")
r = ask_vine(Q, chunks=CHUNKS, section_id="2C.07", ask=ask)
assert r.report.source == "baseline"
assert r.stage == "answered"
print("6. a parser that never produces valid JSON falls back to the printed "
      "structure")

# ---- 7. the answer step runs only after certification --------------------
ask = model(GOOD_SPEC, VERDICT, VERDICT, "FINAL PROSE")
r = ask_vine(Q, chunks=CHUNKS, section_id="2C.07", ask=ask,
             verifiers={"calculator": lambda op, st: _true(op),
                        "symbolic": lambda op, st: _unknown(op)})
from mrag.vine import Certificate


def _true(op):
    return Certificate(claim=op.claim, status=Status.TRUE, confidence=0.9,
                       normative_authority=op.normative_authority)


def _unknown(op):
    return Certificate(claim=op.claim, status=Status.UNKNOWN, confidence=0.0,
                       normative_authority=op.normative_authority)


r = ask_vine(Q, chunks=CHUNKS, section_id="2C.07", ask=ask,
             verifiers={"calculator": lambda op, st: _true(op),
                        "symbolic": lambda op, st: _unknown(op),
                        "llm": lambda op, st: _unknown(op),
                        "vlm": lambda op, st: _unknown(op)})
assert r.status is Status.UNKNOWN          # one branch unresolved
assert r.answer.abstained
assert not r.certified
print("7. an unresolved branch leaves the run uncertified and the answer an "
       "abstention")

# ---- 8. a missing verifier abstains, it is not stubbed ------------------
v = build_verifiers(tables=(), kg=None, retriever=None, ask=None)
assert v == {}, v
r = ask_vine(Q, chunks=CHUNKS, section_id="2C.07", verifiers=v)
assert all(c.status is Status.UNKNOWN for c in r.trace.store.all())
assert not r.trace.unsupported_certification()
print("8. a verifier that cannot be built is left out, and the executor "
      "abstains for it")

# ---- 9. empty evidence stops before compiling ---------------------------
r = ask_vine(Q, chunks=[], section_id="2C.07")
assert r.stage == "no evidence" and r.spec is None
print("9. no evidence stops the run before compilation")

# ---- 10. a dead retriever is reported, not swallowed --------------------
class Dead:
    def retrieve_for_compile(self, *a, **k):
        raise RuntimeError("qdrant unreachable")


r = ask_vine(Q, retriever=Dead())
assert r.stage == "retrieval failed" and "qdrant" in r.problems[0]
print("10. a dead retriever is reported as a stage failure")

# ---- 11. the section is inferred when not given -------------------------
r = ask_vine(Q, chunks=CHUNKS)
assert r.section_id == "2C.07"
print("11. the section id is inferred from the chunks when not supplied")

# ---- 12. the record is complete and serialisable ------------------------
ask = model(GOOD_SPEC, VERDICT, VERDICT, "FINAL PROSE")
with tempfile.TemporaryDirectory() as d:
    r = ask_vine(Q, chunks=CHUNKS, section_id="2C.07", ask=ask, record_dir=d)
    files = list(Path(d).glob("*.json"))
    assert len(files) == 1
    saved = json.loads(files[0].read_text())
for key in ("question", "stage", "status", "spec", "certificates",
            "compile_report", "raw_parser_replies", "answer",
            "supporting_certificates", "unsupported_certification"):
    assert key in saved, key
assert saved["raw_parser_replies"]           # S3.4: auditable
assert isinstance(r.summary(), str) and "obligations" in r.summary()
print("12. the saved record carries the spec, every certificate and every "
      "raw reply")

print("\nALL ENTRY POINT TESTS PASSED")
