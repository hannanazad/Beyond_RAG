"""The answer says WHY a decision does not hold (answer.compose, 15 Oct 2026).

Before, a FALSE decision printed its final claim and "this does not hold", and
nothing else: a reader could not tell which requirement failed, and a question
with several parts lost the parts that did hold. A failed Guidance check was
printed as its claim -- written as the statement that would pass -- so it read
as if it held. And a Guidance item the network had set aside (an exception
applied, or an alternative was met another way) was still reported as a
departure.

Now the answer lists:
  - the checks a FALSE decision rests on, walked down the merges the way the
    executor read them (only inputs that block at each merge's own heading),
    each named as found NOT true, with its heading;
  - the parts of the final conjunction that do hold;
  - Guidance checks not followed, as checks (not the merges that repeat them),
    leaving out the ones an exception or an alternative covered.
The model that writes the prose (Eq 6) gets the same lists, with each failed
check's reason, and the composed text is kept beside its prose.

Every network here is made up in the shape the parser writes. None comes from
a sample question, a gold answer or the MUTCD.

Run: python3 tests/test_answer_reasons.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrag.vine import Certificate, NetworkSpec, Status, execute, instantiate
from mrag.vine.answer import answer, build_answer_prompt, compose

T, F, U = Status.TRUE, Status.FALSE, Status.UNKNOWN
ALL = ("llm", "vlm", "calculator", "symbolic", "cross_reference_resolver")
S, G, O = "STANDARD", "GUIDANCE", "OPTION"


def ob(i, claim, auth, typ="applicability"):
    return {"id": i, "claim": claim, "type": typ, "authority": auth, "requires": [],
            "evidence_hint": [], "source_chunk": "made_up"}


def merge(i, claim, kind, inputs, auth):
    return {"id": i, "claim": claim, "kind": kind, "inputs": inputs, "authority": auth}


def run(obligations, merges, terminal, table, reasons=None):
    spec = NetworkSpec.from_dict({"query": "made-up test", "terminal": terminal,
                                  "obligations": obligations, "merges": merges})
    net, problems = instantiate(spec)
    assert problems == [], problems

    def verify(op, store):
        return Certificate(claim=op.claim, status=table[op.id], normative_authority=op.normative_authority,
                           verifier=op.verifier, obligation_id=op.id, confidence=0.9,
                           provenance={"reason": (reasons or {}).get(op.id, "")})
    return net, execute(net, {v: verify for v in ALL})


checks = 0


def check(cond, what):
    global checks
    assert cond, what
    checks += 1
    print(f"  ok  {what}")


# --------------------------------------------------------------------------- #
print("1. A FALSE decision names the check that failed, and the parts that hold")
obs = [ob("a", "Panel P is the required color.", S), ob("b", "Panel P is at least the minimum size.", S, "numerical"),
       ob("c", "Panel P is mounted on the right side.", S)]
ms = [merge("m_look", "Panel P has the required color and size.", "conjunction", ["a", "b"], S),
      merge("m_all", "Panel P meets the color, size and side rules.", "conjunction", ["m_look", "c"], S)]
net, tr = run(obs, ms, "m_all", {"a": T, "b": F, "c": T})
txt = compose("q", net, tr).text
check("does not hold" in txt and "found not true: Panel P is at least the minimum size (Standard)" in txt,
      "the failed check is named as found NOT true, with its heading")
check("These parts do hold: Panel P is mounted on the right side" in txt,
      "the part of the final conjunction that holds is named")
check("Panel P is the required color" not in txt.split("found not true:")[1].split("These parts")[0],
      "a check that passed inside the failed branch is not given as a reason")

# --------------------------------------------------------------------------- #
print("2. Only what blocks at each merge's heading is a reason")
obs = [ob("s1", "Item Q meets the required height.", S, "numerical"),
       ob("g1", "Item Q is at the recommended offset.", G, "numerical"),
       ob("p1", "The optional plaque is used.", O)]
ms = [merge("m", "Item Q meets the manual.", "conjunction", ["s1", "g1", "p1"], S)]
net, tr = run(obs, ms, "m", {"s1": F, "g1": F, "p1": F})
a = compose("q", net, tr)
why = a.text.split("found not true:")[1].split(". ")[0]
check("Item Q meets the required height" in why and "recommended offset" not in why
      and "optional plaque" not in why,
      "a Standard merge fails on the Standard; the Guidance and the Option not taken are not its reasons")
check(a.non_conformances == ["Item Q is at the recommended offset."]
      and "non-conformance with Guidance (found not true): Item Q is at the recommended offset" in a.text,
      "the Guidance item is reported separately, as a departure found not true")
check(a.provenance["found_false"] == ["s1"], "the record keeps which checks the decision rests on")

# --------------------------------------------------------------------------- #
print("3. A Guidance merge that failed is reported by its check, not by itself")
obs = [ob("s1", "Sign R is the required shape.", S), ob("g1", "Sign R is at the recommended height.", G, "numerical"),
       ob("g2", "Sign R is on the recommended side.", G)]
ms = [merge("mg", "The mounting Guidance for Sign R is followed.", "conjunction", ["g1", "g2"], G),
      merge("m", "Sign R meets the manual.", "conjunction", ["s1", "mg"], S)]
net, tr = run(obs, ms, "m", {"s1": T, "g1": F, "g2": T})
a = compose("q", net, tr)
check(tr.terminal.status is T and a.non_conformances == ["Sign R is at the recommended height."],
      "the decision holds; the departure listed is the check, not the merge that repeats it")

# --------------------------------------------------------------------------- #
print("4. A Guidance item an exception or an alternative covered is not a departure")
obs = [ob("gb", "Device D is at the recommended spacing.", G, "numerical"),
       ob("ex", "The constrained-site exception covers Device D.", O, "exception"),
       ob("s1", "Device D is the required color.", S)]
ms = [merge("x", "Device D's spacing is as recommended, or excepted.", "exception", ["gb", "ex"], G),
      merge("m", "Device D meets the manual.", "conjunction", ["x", "s1"], S)]
net, tr = run(obs, ms, "m", {"gb": F, "ex": T, "s1": T})
a = compose("q", net, tr)
check(tr.terminal.status is T and a.non_conformances == [] and "non-conformance" not in a.text,
      "exception applied: the base Guidance item is not reported as a departure (it was)")
obs = [ob("w1", "Marking M follows the first recommended layout.", G),
       ob("w2", "Marking M follows the second recommended layout.", G),
       ob("s1", "Marking M is the required color.", S)]
ms = [merge("alt", "Marking M follows one of the recommended layouts.", "alternative", ["w1", "w2"], G),
      merge("m", "Marking M meets the manual.", "conjunction", ["alt", "s1"], S)]
net, tr = run(obs, ms, "m", {"w1": F, "w2": T, "s1": T})
check(compose("q", net, tr).non_conformances == [],
      "alternative met another way: the other layout is not reported as a departure")
net, tr = run(obs, ms, "m", {"w1": F, "w2": F, "s1": T})
check(sorted(compose("q", net, tr).non_conformances) == sorted(
    ["Marking M follows the first recommended layout.", "Marking M follows the second recommended layout."]),
    "neither layout followed: both are departures")

# --------------------------------------------------------------------------- #
print("5. An exception that failed: the base and the exception not available are both reasons")
obs = [ob("b", "Unit U meets the standard size.", S, "numerical"),
       ob("e1", "The low-speed condition of the small-unit Option is met.", O)]
ms = [merge("x", "Unit U meets the standard size, or the small-unit Option applies.", "exception", ["b", "e1"], S)]
net, tr = run(obs, ms, "x", {"b": F, "e1": F})
why = compose("q", net, tr).text.split("found not true:")[1]
check(tr.terminal.status is F and "Unit U meets the standard size (Standard)" in why
      and "low-speed condition of the small-unit Option is met (Option)" in why,
      "the failed base and the condition that kept the exception away are both named")

# --------------------------------------------------------------------------- #
print("6. A one-check plan does not repeat its claim as its own reason")
net, tr = run([ob("o1", "Pattern Z may be printed on the sign face.", S)], [], "o1", {"o1": F})
txt = compose("q", net, tr).text
check(txt.count("Pattern Z may be printed") == 1 and "found not true" not in txt,
      "the final claim is stated once")

# --------------------------------------------------------------------------- #
print("7. The model that writes the prose gets the reasons; the composed text is kept")
obs = [ob("a", "Light L flashes within the required rate.", S, "numerical"),
       ob("b", "Light L is the required color.", S)]
ms = [merge("m", "Light L meets the manual.", "conjunction", ["a", "b"], S)]
net, tr = run(obs, ms, "m", {"a": F, "b": T}, reasons={"a": "The rate given is above the maximum."})
prompt = build_answer_prompt("q", net, tr)
check("WHY IT DOES NOT HOLD" in prompt and "the checker's reason: The rate given is above the maximum." in prompt
      and "PARTS THAT DO HOLD\n- Light L is the required color." in prompt,
      "the prompt carries the failed check, its reason, and the part that holds")
check("found not true must be reported as not true" in prompt and "Do not re-decide it" in prompt,
      "the prompt says a claim found not true is reported as not true, and forbids re-deciding")
said = {}


def stub(p, images):
    said["prompt"] = p
    return "Light L does not meet the manual: its flash rate is above the maximum."


a = answer("q", net, tr, stub)
check(a.status is F and a.text.startswith("Light L does not meet") and a.provenance["verbalized"] is True
      and "found not true: Light L flashes within the required rate" in a.provenance["template_text"],
      "the model's prose is the answer, the status is not read from it, and the composed text is kept")

print(f"\nALL ANSWER-REASON TESTS PASSED ({checks} checks)")
