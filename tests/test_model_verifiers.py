"""Tests for the LLM and VLM verifiers.

Every model call is a stub, so this runs with no API key, no GPU and no cost.
That is the point of the callable contract: the verifier's behaviour is
testable without a model, exactly as the calculator's is.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import (Authority, Certificate, CertificateStore, Network,
                       Operation, Status, execute)
from mrag.vine.model_verifiers import (build_prompt, certificates_for_retrieval,
                                       make_llm_verifier, make_vlm_verifier,
                                       parse_model_reply)


CHUNK = {"chunk_id": "MUTCD11e_2C07_Standard_01", "section_id": "2C.07",
         "content_type": "Standard", "text": "A Curve sign shall be used.",
         "authority_inferred": False}
INFERRED = {"chunk_id": "MUTCD11e_TBLNOTE_4C-1_03", "section_id": "4C.02",
            "content_type": "Option", "text": "May be used above 40 mph.",
            "authority_inferred": True}
FIGURE = {"figure_id": "Figure 2C-1", "caption": "Horizontal alignment signs",
          "image_paths": ["/crops/2C-1_s1.png", "/crops/2C-1_s2.png"],
          "n_sheets": 4, "_sheets_shown": 2}


class FakeRetriever:
    def __init__(self, chunks=(CHUNK,), figures=(), fail=False):
        self.chunks, self.figures, self.fail = list(chunks), list(figures), fail
        self.calls = []

    def retrieve_for_obligation(self, query, obligation, certificates=None,
                                top_k=None, **kw):
        if self.fail:
            raise RuntimeError("qdrant unreachable")
        self.calls.append({"query": query, "obligation": obligation,
                           "certificates": certificates, "top_k": top_k})

        class R:
            pass
        r = R()
        r.chunks, r.figures = list(self.chunks), list(self.figures)
        r.debug = {"established_sections": ["2C.06"]}
        return r


def say(payload):
    """A stub model that always returns the same reply."""
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return lambda prompt, images: text


OP = Operation("o1", "a Curve sign is required in advance of the curve",
               "s_o1", [], "llm", normative_authority=Authority.STANDARD)


# ---- 1. the reply is read strictly ----------------------------------------
r = parse_model_reply(json.dumps({"status": "TRUE", "evidence": ["a"],
                                  "confidence": 0.8, "reason": "because"}), ["a"])
assert r.status is Status.TRUE and r.evidence == ["a"] and r.confidence == 0.8
r = parse_model_reply('```json\n{"status":"FALSE","evidence":["a"]}\n```', ["a"])
assert r.status is Status.FALSE          # a markdown fence is tolerated
print("1. a well-formed reply is read, fenced or not")

# ---- 2. every failure falls to UNKNOWN, never to FALSE --------------------
for raw, why in [("I think the answer is no.", "prose"),
                 ("{not json}", "malformed"),
                 ('{"status": "PROBABLY"}', "invented status"),
                 ("[1,2,3]", "not an object"),
                 ("", "empty")]:
    out = parse_model_reply(raw, ["a"])
    assert out.status is Status.UNKNOWN, why
    assert out.problem, why
print("2. prose, malformed JSON and invented statuses all give UNKNOWN")

# ---- 3. a model may not cite evidence it was never shown ------------------
r = parse_model_reply(json.dumps({"status": "TRUE", "confidence": 1.0,
                                  "evidence": ["MUTCD11e_2C07_Standard_01",
                                               "Section 9Z.99"]}),
                      ["MUTCD11e_2C07_Standard_01"])
assert r.evidence == ["MUTCD11e_2C07_Standard_01"]
assert r.dropped == ["Section 9Z.99"]
print("3. invented evidence ids are dropped and recorded")

# ---- 4. confidence is clamped ---------------------------------------------
assert parse_model_reply('{"status":"TRUE","evidence":["a"],"confidence":7}',
                         ["a"]).confidence == 1.0
assert parse_model_reply('{"status":"TRUE","evidence":["a"],"confidence":"high"}',
                         ["a"]).confidence == 0.0
print("4. a confidence outside 0..1, or not a number at all, is clamped")

# ---- 5. the prompt asks about the OBLIGATION, not the question -----------
prompt, allowed = build_prompt(OP, [CHUNK, INFERRED], [FIGURE])
assert OP.claim in prompt
assert allowed == ["MUTCD11e_2C07_Standard_01", "MUTCD11e_TBLNOTE_4C-1_03",
                   "Figure 2C-1"]
assert "UNKNOWN is a correct answer" in prompt
# an inferred authority is flagged, so a guessed heading is not read as printed
assert "type inferred from the verb" in prompt
# and a partial figure says so in the evidence itself
assert "only 2 of 4 sheets are shown" in prompt
print("5. the prompt carries the claim, flags inferred types and partial "
      "figures, and offers UNKNOWN")

# ---- 6. a definitive answer citing nothing supplied is downgraded ---------
verify = make_llm_verifier(say({"status": "TRUE", "evidence": ["Section 9Z.99"],
                                "confidence": 0.9}), FakeRetriever())
cert = verify(OP, CertificateStore())
assert cert.status is Status.UNKNOWN
assert cert.provenance["fabricated_evidence_ids"] == ["Section 9Z.99"]
assert "downgraded" in cert.provenance
print("6. a TRUE resting only on invented evidence becomes UNKNOWN")

# ---- 7. a good answer becomes a proper certificate -------------------------
verify = make_llm_verifier(say({"status": "TRUE", "confidence": 0.9,
                                "evidence": ["MUTCD11e_2C07_Standard_01"],
                                "reason": "the Standard says so"}),
                           FakeRetriever())
cert = verify(OP, CertificateStore())
assert cert.status is Status.TRUE and cert.confidence == 0.9
assert [(e.type, e.id) for e in cert.evidence] == \
    [("chunk", "MUTCD11e_2C07_Standard_01")]
assert cert.verifier == "llm" and cert.obligation_id == "o1"
assert cert.provenance["raw_reply"]        # auditable, S3.4
print("7. a good answer yields a certificate with evidence and provenance")

# ---- 8. the model never sets the authority --------------------------------
guidance = Operation("o2", "a Turn sign should be used", "s_o2", [], "llm",
                     normative_authority=Authority.GUIDANCE)
verify = make_llm_verifier(say({"status": "FALSE", "confidence": 1.0,
                                "normative_authority": "SUPPORT",
                                "evidence": ["MUTCD11e_2C07_Standard_01"]}),
                           FakeRetriever())
cert = verify(guidance, CertificateStore())
assert cert.normative_authority is Authority.GUIDANCE
assert cert.non_conformance()          # GUIDANCE FALSE records, does not refute
print("8. authority comes from the operation even when the model volunteers one")

# ---- 9. no evidence, a crash, and a dead retriever all abstain ------------
assert make_llm_verifier(say({"status": "TRUE"}),
                         FakeRetriever(chunks=()))(OP, CertificateStore()
                                                   ).status is Status.UNKNOWN


def boom(prompt, images):
    raise RuntimeError("rate limited")


c = make_llm_verifier(boom, FakeRetriever())(OP, CertificateStore())
assert c.status is Status.UNKNOWN and "rate limited" in c.provenance["reason"]
c = make_llm_verifier(say({"status": "TRUE"}),
                      FakeRetriever(fail=True))(OP, CertificateStore())
assert c.status is Status.UNKNOWN and "retrieval failed" in c.provenance["reason"]
print("9. empty evidence, a crashed model and a dead retriever all abstain")

# ---- 10. Eq 5: the store conditions the retrieval -------------------------
store = CertificateStore()
store.add("s_class", Certificate(
    claim="the road is a conventional road", status=Status.TRUE,
    evidence=[__import__("mrag.vine", fromlist=["Evidence"]).Evidence(
        "section", "2C.06")]))
store.add("s_open", Certificate(claim="unresolved", status=Status.UNKNOWN))
retr = FakeRetriever()
make_llm_verifier(say({"status": "TRUE",
                       "evidence": ["MUTCD11e_2C07_Standard_01"]}),
                  retr, query="is a Curve sign required?")(OP, store)
sent = retr.calls[0]
assert sent["obligation"] == OP.claim          # the claim, not the question
assert sent["query"] == "is a Curve sign required?"
statuses = {c["status"] for c in sent["certificates"]}
assert statuses == {"TRUE", "UNKNOWN"}         # filtering happens in retrieval
print("10. the certificate store is passed to retrieval, obligation as the "
      "search text")

# ---- 11. the VLM verifier sends crops and distrusts a partial figure ------
seen = {}


def watch(prompt, images):
    seen["images"] = list(images)
    return json.dumps({"status": "TRUE", "confidence": 1.0,
                       "evidence": ["Figure 2C-1"]})


visual = Operation("o3", "the layout matches Figure 2C-1", "s_o3", [], "vlm")
cert = make_vlm_verifier(watch, FakeRetriever(chunks=(), figures=(FIGURE,))
                         )(visual, CertificateStore())
assert seen["images"] == ["/crops/2C-1_s1.png", "/crops/2C-1_s2.png"]
assert cert.status is Status.TRUE
# two sheets of four: the model said 1.0, the certificate does not agree
assert cert.confidence == 0.5
assert cert.provenance["partial_figures"] == ["Figure 2C-1"]
assert [(e.type, e.id) for e in cert.evidence] == [("figure", "Figure 2C-1")]
print("11. the VLM gets the crops, and a half-seen figure caps confidence "
      "at 0.5")

# ---- 12. the LLM verifier sends no images ---------------------------------
seen.clear()
make_llm_verifier(watch, FakeRetriever(chunks=(CHUNK,), figures=(FIGURE,))
                  )(OP, CertificateStore())
assert seen["images"] == []
print("12. a textual obligation is not sent pictures")

# ---- 13. both plug into the executor unchanged ----------------------------
net = Network(query="is a Curve sign required?", terminal="s_m")
net.states = {"s_o1", "s_o3", "s_m"}
net.operations = [
    Operation("o1", "a Curve sign is required", "s_o1", [], "llm"),
    Operation("o3", "the layout matches Figure 2C-1", "s_o3", [], "vlm"),
    Operation("m", "the requirements are met", "s_m", ["s_o1", "s_o3"], "merge",
              merge=__import__("mrag.vine", fromlist=["MergeType"]).MergeType.CONJUNCTION,
              merge_inputs=["s_o1", "s_o3"]),
]
good = say({"status": "TRUE", "confidence": 0.9,
            "evidence": ["MUTCD11e_2C07_Standard_01", "Figure 2C-1"]})
trace = execute(net, {
    "llm": make_llm_verifier(good, FakeRetriever()),
    "vlm": make_vlm_verifier(good, FakeRetriever(chunks=(CHUNK,),
                                                 figures=(FIGURE,))),
})
assert trace.problems == []
assert trace.terminal.status is Status.TRUE
assert not trace.unsupported_certification()
print("13. both run inside execute() with no change to the executor")

# ---- 14. one unparsable reply leaves the terminal unresolved --------------
trace = execute(net, {
    "llm": make_llm_verifier(say("I'd say yes, probably."), FakeRetriever()),
    "vlm": make_vlm_verifier(good, FakeRetriever(chunks=(CHUNK,),
                                                 figures=(FIGURE,))),
})
assert trace.terminal.status is Status.UNKNOWN
assert not trace.unsupported_certification()
print("14. a model that answered in prose leaves the decision unresolved, "
      "not refuted")

print("\nALL MODEL VERIFIER TESTS PASSED")
