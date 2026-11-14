"""changes_107 (14 Nov 2026), made-up provisions only:
  1. combining code: an open (UNKNOWN) check under a heading WEAKER than its
     merge does not block a merge read at its own heading, because TRUE and
     FALSE there give the same merge; at face value nothing changes;
  2. answer writer: per part, a FALSE is named by its heading (a
     recommendation not followed, a permission that does not apply, a
     requirement not met)."""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrag.vine.answer import build_answer_prompt  # noqa: E402
from mrag.vine.certificate import Authority, Certificate, Status  # noqa: E402
from mrag.vine.compile import NetworkSpec, instantiate  # noqa: E402
from mrag.vine.execute import _non_blocking, execute  # noqa: E402
from mrag.vine.experiments import _blocking  # noqa: E402

ok = 0


def check(c, what):
    global ok
    assert c, what
    ok += 1
    print("  ok ", what)


T, F, U = Status.TRUE, Status.FALSE, Status.UNKNOWN
ALL = ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")
S, G, O = Authority.STANDARD, Authority.GUIDANCE, Authority.OPTION


def ob(i, claim, auth):
    return {"id": i, "claim": claim, "type": "applicability", "authority": auth, "requires": [],
            "evidence_hint": [], "source_chunk": "made_up"}


def run(spec_dict, table):
    net, problems = instantiate(NetworkSpec.from_dict(spec_dict))
    assert problems == [], problems

    def verify(op, store):
        return Certificate(claim=op.claim, status=table[op.id], normative_authority=op.normative_authority,
                           verifier=op.verifier, obligation_id=op.id, confidence=0.9,
                           provenance={"reason": "made-up reason " + op.id})
    return net, execute(net, {v: verify for v in ALL})


def group(merge_auth, kind="conjunction"):
    return {"query": "q", "terminal": "m", "obligations": [
        ob("s", "Device Q is the size Section 9Z.01 paragraph 1 requires.", "STANDARD"),
        ob("g", "Device Q is at the height Section 9Z.01 paragraph 2 recommends.", "GUIDANCE"),
        ob("o", "Device Q carries the plaque Section 9Z.01 paragraph 3 allows.", "OPTION")],
        "merges": [{"id": "m", "claim": "Device Q meets Section 9Z.01.", "kind": kind,
                    "inputs": ["s", "g", "o"], "authority": merge_auth}]}


# --------------------------------------------------------------------------- #
# 1. the rule itself, over every status, heading and merge heading
# --------------------------------------------------------------------------- #
for st, auth, merge in itertools.product((T, F, U, Status.NOT_APPLICABLE), (S, G, O), (S, G, O, None)):
    cert = Certificate(claim="c", status=st, normative_authority=auth)
    got = _non_blocking(cert, merge)
    weaker = merge is not None and auth is not S and {S: 3, G: 2, O: 1}[merge] > {S: 3, G: 2, O: 1}[auth]
    want = T if (weaker and st in (F, U)) else st
    assert got is want, (st, auth, merge, got)
    if merge is not None:
        assert _blocking(st, auth, merge) is want, ("experiments reference differs", st, auth, merge)
check(True, "an input weaker than its merge counts as TRUE when FALSE or UNKNOWN; at its heading or "
            "stronger, or at face value, it counts as it is (and the experiments reference agrees)")

# --------------------------------------------------------------------------- #
# 2. through execute: a Standard group with an open Option, an open Guidance
# --------------------------------------------------------------------------- #
for open_one, label in (("o", "Option"), ("g", "Guidance")):
    table = {"s": T, "g": T, "o": T, open_one: U}
    net, tr = run(group("STANDARD"), table)
    m = tr.store.latest("s_m")
    check(m.status is T and tr.store.latest(f"s_{open_one}").status is U
          and m.provenance["inputs"][f"s_{open_one}"] == "UNKNOWN"
          and m.provenance["blocking_adjusted"][f"s_{open_one}"] == "TRUE",
          f"an open {label} in a Standard group: the group holds, the {label} stays open, and the "
          f"adjustment is recorded")
    p = build_answer_prompt("q", net, tr)
    open_claim = tr.store.latest(f"s_{open_one}").claim
    check("DECISION\nTRUE" in p and f"LEFT UNRESOLVED\n- {open_claim}" in p,
          f"the answer prompt for it decides TRUE and still lists the open {label} as left unresolved")

# an open Standard still blocks; a FALSE Standard still refutes
net, tr = run(group("STANDARD"), {"s": U, "g": T, "o": T})
check(tr.store.latest("s_m").status is U, "an open Standard still leaves the Standard group open")
net, tr = run(group("STANDARD"), {"s": F, "g": U, "o": U})
check(tr.store.latest("s_m").status is F, "a FALSE Standard still refutes, whatever is open beside it")

# a Guidance group: an open Option does not block it, an open Guidance does
net, tr = run(group("GUIDANCE"), {"s": T, "g": T, "o": U})
check(tr.store.latest("s_m").status is T, "an open Option in a Guidance group: the group holds")
net, tr = run(group("GUIDANCE"), {"s": T, "g": U, "o": T})
check(tr.store.latest("s_m").status is U, "an open Guidance in a Guidance group: the group stays open")

# an alternative must be SATISFIED: an open branch is not relaxed there
net, tr = run(group("STANDARD", "alternative"), {"s": F, "g": F, "o": U})
check(tr.store.latest("s_m").status is U, "an alternative is not relaxed: an open branch stays open")

# --------------------------------------------------------------------------- #
# 3. at face value (a bundle that only joins the parts of the question)
# --------------------------------------------------------------------------- #
bundle = {"query": "q", "terminal": "t", "obligations": [
    ob("s", "Device Q is the size Section 9Z.01 paragraph 1 requires.", "STANDARD"),
    ob("g", "Device Q is at the height Section 9Z.01 paragraph 2 recommends.", "GUIDANCE")],
    "merges": [{"id": "t", "claim": "Both parts hold.", "kind": "conjunction", "inputs": ["s", "g"],
                "authority": "STANDARD"}],
    "asked": [{"id": "a1", "ask": "Is the size required?", "answered_by": ["s"]},
              {"id": "a2", "ask": "Is the height recommended?", "answered_by": ["g"]}]}
net, tr = run(bundle, {"s": T, "g": U})
t_cert = tr.store.latest("s_t")
check(t_cert.status is U and t_cert.provenance.get("read_at_face_value") is True,
      "a bundle read at face value keeps an open Guidance part open")

# --------------------------------------------------------------------------- #
# 4. the answer writer names a FALSE by its heading, per part
# --------------------------------------------------------------------------- #
net, tr = run(bundle, {"s": T, "g": F})
p = build_answer_prompt("q", net, tr)
check("PARTS OF THE QUESTION" in p and "[FALSE] Device Q is at the height Section 9Z.01 paragraph 2 "
      "recommends.  [GUIDANCE]" in p, "the part shows its result with its heading")
check("found FALSE, means the case does not follow that recommendation, which breaks no requirement" in p
      and "means that permission does not apply here or is not used, which breaks nothing" in p
      and "only a STANDARD found FALSE is a requirement not met" in p,
      "the per-part instructions say what a FALSE means under each heading")
check("it does not by itself say that a requirement is broken: the parts say what is" in p,
      "the per-part instructions say the joined result is not by itself a broken requirement")
# a question with one part keeps its own instructions
net, tr = run(group("STANDARD"), {"s": T, "g": F, "o": T})
p1 = build_answer_prompt("q", net, tr)
check("DECISION\nTRUE" in p1 and "PARTS OF THE QUESTION" not in p1
      and "which breaks no requirement" not in p1,
      "a one-part question keeps its single-decision instructions")

print(f"ALL CHANGES_107 TESTS PASSED ({ok} checks)")
