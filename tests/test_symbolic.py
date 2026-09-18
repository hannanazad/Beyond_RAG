"""Tests for the symbolic rule evaluator.

Part 1 is the parser and the three-valued logic, built in code.
Part 2 is the live check against the conditions in `mutcd_tables.jsonl`, and
the loop back into the calculator: a held value released once the condition
has been decided.

No models, no GPU, no Qdrant.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine import (Certificate, CertificateStore, Network, Operation,
                       Status, execute, make_calculator)
from mrag.vine.symbolic import (Comparison, Conjunction, Disjunction,
                                Negation, Unparsed, evaluate_rule,
                                facts_from_store, make_rule_evaluator,
                                parse_rule)
from mrag.vine.table_data import Footnote, Table, Value
from mrag.vine.table_data import load as load_tables


def facts(**kw):
    """{'speed': 45} or {'speed': (45, 'mph')} as the evaluator wants them."""
    store = CertificateStore()
    m = {k: ({"value": v[0], "unit": v[1]} if isinstance(v, tuple) else v)
         for k, v in kw.items()}
    store.add("s", Certificate(claim="given", status=Status.TRUE,
                               obligation_id="O_given",
                               provenance={"facts": m}))
    return facts_from_store(store)


def decide(text, **kw):
    return evaluate_rule(parse_rule(text), facts(**kw))


# ===========================================================================
# Part 1 — built in code
# ===========================================================================

# ---- 1. the four ways the manual writes a bound ---------------------------
assert parse_rule("the speed exceeds 40 mph") == \
    Comparison("speed", ">", 40.0, "mph", "the speed exceeds 40 mph")
assert parse_rule("speed limits of 25 mph or less").comparator == "<="
assert parse_rule("a speed of 45 mph or higher").comparator == ">="
assert parse_rule("a population of less than 10,000").bound == 10000.0
print("1. exceeds / or less / or higher / less than all read correctly")

# ---- 2. the subject may sit on either side of the number ------------------
assert parse_rule("the major-street speed exceeds 40 mph").subject == "major_street_speed"
assert parse_rule("Community less than 10,000 population").subject == "population"
# and the bare word must not swallow the qualified one
assert parse_rule("major-street speed exceeds 40 mph").subject != "speed"
print("2. subject found before OR after the number; 'major-street speed' "
      "not read as 'speed'")

# ---- 3. "or less" is a comparator; "or above 40" is a new clause ----------
assert isinstance(parse_rule("speeds of 25 mph or less"), Comparison)
r = parse_rule("Community less than 10,000 population or above 40 mph on major street")
assert isinstance(r, Disjunction) and len(r.parts) == 2, r.describe()
assert {p.subject for p in r.parts} == {"population", "major_street_speed"}
print("3. 'or less' stays a comparator; 'or above 40 mph' opens a clause")

# ---- 4. a comma list is not a disjunction ---------------------------------
r = parse_rule("a posted, statutory, or 85th-percentile speed of 45 mph or higher")
assert isinstance(r, Comparison) and r.bound == 45.0, r.describe()
print("4. 'posted, statutory, or 85th-percentile' is a list, not a choice")

# ---- 5. one sentence can hold both kinds of 'or' ---------------------------
r = parse_rule("A minimum size of 18 x 18 may be used on low-volume roadways "
               "or roadways with speeds of 25 mph or less")
assert isinstance(r, Disjunction) and len(r.parts) == 2
assert isinstance(r.parts[0], Unparsed) and isinstance(r.parts[1], Comparison)
print("5. a real 'or' and a comparator 'or' in one sentence, both kept")

# ---- 6. Kleene: unknown does not become false ------------------------------
assert decide("speed exceeds 40 mph", speed=45) is Status.TRUE
assert decide("speed exceeds 40 mph", speed=35) is Status.FALSE
assert decide("speed exceeds 40 mph") is Status.UNKNOWN           # no fact
rule = ("the major-street speed exceeds 40 mph or in an isolated community "
        "with a population of less than 10,000")
assert decide(rule, major_street_speed=45) is Status.TRUE          # one side decides
assert decide(rule, major_street_speed=35) is Status.UNKNOWN       # other side unknown
assert decide(rule, major_street_speed=35, population=8000) is Status.TRUE
assert decide(rule, major_street_speed=35, population=20000) is Status.FALSE
print("6. Kleene logic: one TRUE branch decides; a missing one abstains")

# ---- 7. an undecidable branch keeps the whole thing honest ----------------
r = ("may be used on low-volume roadways or roadways with speeds of "
     "25 mph or less")
assert decide(r, speed=20) is Status.TRUE
# the speed test fails, but "low-volume" might still qualify it
assert decide(r, speed=45) is Status.UNKNOWN
print("7. failing the arithmetic branch abstains rather than denying a use "
      "the manual allows")

# ---- 8. negation ----------------------------------------------------------
assert decide("not the speed exceeds 40 mph", speed=35) is Status.TRUE
assert decide("not the speed exceeds 40 mph") is Status.UNKNOWN
print("8. negation flips TRUE and FALSE, and leaves UNKNOWN alone")

# ---- 9. units -------------------------------------------------------------
assert decide("signs measuring less than 48 inches", sign_size=(3, "ft")) is Status.TRUE
assert decide("signs measuring less than 48 inches", sign_size=(5, "ft")) is Status.FALSE
# no exact conversion -> abstain rather than compare numbers of different things
assert decide("the speed exceeds 40 mph", speed=(100, "vpd")) is Status.UNKNOWN
print("9. feet compared against inches; mph against vpd abstains")

# ---- 10. an ambiguous subject is refused ----------------------------------
two = facts(major_street_speed=45, minor_street_speed=20)
assert evaluate_rule(parse_rule("speed exceeds 40 mph"), two) is Status.UNKNOWN
print("10. two facts could answer 'speed' -> UNKNOWN, not a coin flip")

# ---- 11. prose that is not a comparison -----------------------------------
assert isinstance(parse_rule("Typical conditions are locations where the road "
                             "user must use extra time"), Unparsed)
assert decide("Typical conditions are locations where the road user must use "
              "extra time", speed=45) is Status.UNKNOWN
print("11. a judgement about a site stays UNKNOWN; it is an LLM's to make")

# ---- 12. the compiler may write the rule directly -------------------------
assert decide("speed > 40", speed=45) is Status.TRUE
assert decide("population <= 10000", population=10000) is Status.TRUE
print("12. an explicit rule string from the compiler is accepted as written")

# ---- 13. it plugs into the executor ---------------------------------------
net = Network(query="may the column be used?", terminal="s_ok")
net.states = {"s_ok"}
net.operations = [Operation("O1", "the major-street speed exceeds 40 mph",
                            "s_ok", [], "symbolic")]
store0 = CertificateStore()
store0.add("s_given", Certificate(claim="speed", status=Status.TRUE,
                                  provenance={"facts": {"major_street_speed": 45}}))
net.initial = store0
net.states.add("s_given")
trace = execute(net, {"symbolic": make_rule_evaluator()})
assert trace.problems == [], trace.problems
assert trace.terminal.status is Status.TRUE
assert trace.terminal.confidence == 1.0
print("13. runs inside execute() with no change to the executor")


# ===========================================================================
# Part 2 — live, and the loop back into the calculator
# ===========================================================================
def _table_file():
    if os.environ.get("MUTCD_TABLES"):
        return Path(os.environ["MUTCD_TABLES"])
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                               / "scripts" / "table_transcription"))
        import paths as _p                                    # noqa: WPS433
        if _p.TABLES_OUT.exists():
            return _p.TABLES_OUT
    except Exception:                                         # noqa: BLE001
        pass
    here = Path(__file__).resolve().parents[1] / "mutcd_tables.jsonl"
    return here if here.exists() else None


DATA = _table_file()
if DATA is None:
    print("\nmutcd_tables.jsonl not found; skipped the live checks")
else:
    tables = load_tables(DATA)
    rules = make_rule_evaluator(tables)

    # 4C-1 note c, named by the compiler as a footnote rather than as text
    hint = [{"type": "table", "id": "Table 4C-1"}, {"type": "footnote", "id": "c"}]
    op = Operation("O_c", "does note c apply?", "s_c", [], "symbolic",
                   evidence_hint=hint)

    store = CertificateStore()
    store.add("s_speed", Certificate(
        claim="the major-street speed is 45 mph", status=Status.TRUE,
        obligation_id="O_speed",
        provenance={"facts": {"major_street_speed": {"value": 45, "unit": "mph"}}}))
    c = rules(op, store)
    assert c.status is Status.TRUE, c.provenance
    assert c.provenance["discharges"] == ["Table 4C-1:c"]
    print("\nL1. 4C-1 note c at 45 mph -> TRUE, and it discharges "
          "'Table 4C-1:c'")

    # the same note, below the threshold: the population branch is unknown,
    # so the condition is unresolved, not denied
    store = CertificateStore()
    store.add("s_speed", Certificate(
        claim="the major-street speed is 35 mph", status=Status.TRUE,
        provenance={"facts": {"major_street_speed": 35}}))
    c = rules(op, store)
    assert c.status is Status.UNKNOWN and "discharges" not in c.provenance
    print("L2. at 35 mph with no population figure -> UNKNOWN, discharges "
          "nothing")

    # ---- the loop: a value the calculator held, released by this verifier --
    HELD = Table(
        table_id="Table 9Z-1", page_pdf=1,
        column_labels=["Speed (S)", "Minimum volume"],
        rows=[[Value("40 mph or less", maximum=40, unit="mph"),
               Value("500", number=500, unit="vph")],
              [Value("45 mph or more", minimum=45, unit="mph"),
               Value("350", number=350, unit="vph")]],
        variables={"S": "major-street speed in mph"},
        footnotes=[Footnote("c", "May be used when the major-street speed "
                                 "exceeds 40 mph or in an isolated community "
                                 "with a population of less than 10,000",
                            applies_to="column:1")],
        verified=True)
    calc = make_calculator([HELD])
    ask = Operation("O_v", "minimum volume from Table 9Z-1 at 45 mph",
                    "s_v", [], "calculator")

    held = calc(ask, CertificateStore())
    assert held.status is Status.UNKNOWN, held.provenance
    assert held.provenance["value"] == 350
    assert held.provenance["undischarged"][0]["marker"] == "c"

    store = CertificateStore()
    store.add("s_speed", Certificate(
        claim="the major-street speed is 45 mph", status=Status.TRUE,
        provenance={"facts": {"major_street_speed": {"value": 45, "unit": "mph"}}}))
    decided = make_rule_evaluator([HELD])(
        Operation("O_c", "does note c apply?", "s_c", [], "symbolic",
                  evidence_hint=[{"type": "table", "id": "Table 9Z-1"},
                                 {"type": "footnote", "id": "c"}]),
        store)
    assert decided.status is Status.TRUE
    store.add("s_c", decided)

    released = calc(ask, store)
    assert released.status is Status.TRUE, released.provenance
    assert released.provenance["value"] == 350
    print("L3. the calculator holds 350 vph on note c; the rule evaluator "
          "decides it; the same call then certifies")

    # ---- how much of the manual this verifier can actually decide ---------
    from mrag.vine.calculator import ConditionKind, classify_condition

    def has_comparison(expr) -> bool:
        if isinstance(expr, Comparison):
            return True
        if isinstance(expr, (Conjunction, Disjunction)):
            return any(has_comparison(p) for p in expr.parts)
        if isinstance(expr, Negation):
            return has_comparison(expr.part)
        return False

    seen, decidable, total = set(), 0, 0
    for t in tables:
        for f in t.footnotes:
            key = (t.table_id, f.marker, f.text)
            if key in seen or classify_condition(f, t) is not ConditionKind.CONDITIONAL:
                continue
            seen.add(key)
            total += 1
            if has_comparison(parse_rule(f.text)):
                decidable += 1
    print(f"L4. of {total} conditional footnotes, {decidable} reduce to a "
          f"comparison this verifier can decide")

print("\nALL SYMBOLIC RULE TESTS PASSED")
