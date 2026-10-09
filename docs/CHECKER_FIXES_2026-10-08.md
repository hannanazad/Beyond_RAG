# Checker fixes and parser fix5, 8 October 2026 (evening)

## Why

The first real execution run (`Execution_Test` CELL 9, 11 DEV cases, Claude Sonnet 5.5 checkers, run `exec_20261009_0128`) was read case by case against the manual.

| Result | Cases |
|---|---|
| Right | P01, P04, P18, P33, P42, T01, T08 |
| Partly right | P47: right sign, but misses "or instead of" (9E.09 ¶11 was not retrieved) |
| **Wrong** | **P35**: said "no requirement", but 6C.01 ¶1 says these provisions "shall be applied by knowledgeable (for example, trained and/or certified) persons" |
| UNKNOWN | P24: should be "not allowed" (4E.04 ¶1) |
| UNKNOWN | P44: see "Not changed" below |

Other numbers from that run:
- Repeat test: 0 of 9 results changed.
- Cost: $0.54 in all, about 4 cents per case.
- Pointers: 41 of the 44 checks given pointed evidence cited it.

Four problems explain all the misses except the retrieval ones. **All four were found on DEV cases; no test question was used.**

## What the draft says the checker may see

**The checker does not see the question.**
- Eq 1, `Nq = Compile(q, Kq)`: the parser/compiler sees q.
- Eq 5, `Ri = Retrieve(q, φi, Γt, K)`: q is used to find the evidence for each check. This is the search step only.
- Eq 6, `a = fLM(q, C⋆, Πq)`: the answer writer sees q.
- §3.3: "All verification remains grounded in the persistent knowledge graph."
- Eq 3: a result rests on Ri, "the supporting standards evidence".

So the facts of the case can reach a checker only two ways:
- through the claim (φi), which the parser writes;
- through the certificate store (Γt), which starts from Eq 2's initial store, **Γ0q**.

Γ0q existed in the code (`Network.initial`), but nothing ever filled it.

## The four changes

### 1. Given facts in Γ0q (parser fix5 + compiler + checker prompt)

**Found on:**
- **P04 and P44:** the checker said "no situation is described" and returned UNKNOWN.
- **P24:** the checker said TRUE to "in the described face the red arrow is above the green ball". The question says the opposite. The parser had not copied that fact into the claim, so the checker could only judge the rule.

**Change:**
- The plan has a new `facts` list: the facts the question states, copied in the question's own words.
- `instantiate` puts each fact into Γ0q as a starting certificate. Each one is TRUE, has `verifier="given"`, its evidence is `given:<id>`, and its authority is SUPPORT.
- Every text and image checker sees the facts under **GIVEN IN THE QUESTION** and may cite them by id. It still never sees the question.
- **A fact alone settles nothing.** A TRUE or FALSE must cite at least one item of manual text. An answer that cites only facts becomes UNKNOWN (§3.3: "All verification remains grounded in the persistent knowledge graph").

**Safety checks on the facts (deterministic; a plan that fails is sent back for repair).** They compare a fact only with what the question *states*, never with what it *asks*:
- **What counts as an ask:**
  - a sentence ending in "?" (a closing quote or bracket after it is ignored);
  - a sentence starting "Determine / Explain / Decide / ...";
  - a sentence containing "whether";
  - if none of these is found, the question's last sentence.
- **A fact is the question's own words:** at most a quarter of its content words may be words the question's statements do not use. This stops a reworded conclusion such as "the panel is good" or "the panel is too low".
- **Numbers:** every number in a fact, in digits or in words, is in the statements.
- **References and requirement words:** a fact names a section, figure, table or the manual, or uses a word such as shall, must, may, required, allowed, complies, violates, OK, fine, needed, applies, passes or fails, only if a statement does.
- **Form:** one sentence; not a question; does not copy the ask.
- **Not a step:** a fact is never in `requires` or `inputs`, never in a guard, and never the terminal.
- **Ids:** f1, f2, f3 and so on, unique.
- **Checked on all 154 DEV questions:** every statement copied word for word passes. Short forms such as "in." and "U.S." do not end a sentence, and "State Route" is not an ask.

**Why this fits the paper:** Eq 1 compiles from (q, Kq), and Eq 2 gives the network an initial store. In Petri-net terms, the starting marking is the starting conditions, and the facts of the case are those conditions.

### 2. Authority follows the evidence a FALSE rests on (checker + executor)

**Found on P35:**
- The first search missed 6C.01 ¶1.
- The checker's own search for o5 found it and said FALSE.
- But the parser had labelled o5 "Guidance". So the FALSE was filed as a non-conformance, the merge came out TRUE, and the answer was wrong.

**Change:**
- **The checker's reply** has a new field, `basis`: the id it rests on most. For a FALSE, that is the provision the claim fails against.
  - If the basis is also among the evidence the checker cites, and is a provision whose printed heading is stronger than the check's authority, the certificate takes that heading. For example, a check labelled Guidance whose FALSE rests on a Standard becomes STANDARD.
  - The heading is read from the provision's record, never from the reply. Only printed headings count, never inferred ones.
  - The authority is only ever raised, never lowered. The change is recorded as `authority_from`.
  - The executor keeps such a raise only when all of these hold: it comes from the text or image checker, on a FALSE, the heading is stronger, and the recorded printed heading matches.
  - The executor resets every other change of authority. A raise it refuses is moved to `authority_from_not_accepted`, so it never reads as a raise.
- **A merge** that comes out FALSE carries the strongest heading among the inputs that made it fail (`merge_authority`).
  - In a conjunction, or at the base of an exception merge, only a failed Standard blocks. So such a merge failing always means a Standard failed.
  - Before this change, a Guidance-labelled conjunction holding a failed Standard came out "FALSE, Guidance". An enclosing conjunction then passed it as a non-conformance.
  - The reference evaluator (`experiments.reference_terminal`) and both sequential baselines apply the same rule.

**Why this fits the paper:** Eq 3 says "Ri is the supporting standards evidence, ri records its normative authority". 1C.01 defines a Standard as mandatory.

### 3. Cross-reference: resolve exactly, then read (run.py)

**Found on P47:** the cross-reference checker said TRUE to a claim about what 9E.09 ¶12 says. It did so only because ¶12 exists; nobody read the claim against the manual.

**Change:** `resolve_then_read`.
- The resolver still checks that every reference exists. A reference to something missing is still FALSE, a real finding.
- Otherwise, the text checker decides the claim against the manual text. This includes the case where the resolver itself crashed.
- The trace shows `cross_reference_resolver -> llm`.
- With no model (the free mode), the resolver runs alone, as before.

**Why this fits the paper:** §3.3 says "an explicit section reference should be resolved exactly", and "generative models are used where interpretation is necessary".

### 4. The first input of an exception merge (parser check)

**Found on P01:**
- The base of the exception merge was "the assembly falls under 1D.06". That is an applicability claim.
- It came out TRUE, so the merge said TRUE without looking at the exception. The answer was right only because the exception was also TRUE.
- The parser's instructions already forbade this. Now a deterministic check enforces it: such a plan is sent back for repair.

## Small changes

- **The model-free answer:** next to a decision that does not hold, Guidance non-conformances now read "Also recorded as non-conformance with Guidance". The old wording, "which does not refute the decision", made sense only next to a TRUE.
- **Execution summaries:** they now show:
  - the given facts;
  - results whose authority was raised;
  - checks passed from an exact tool to the text checker, by tool;
  - the repeat count, with given facts left out.
- **The notebooks no longer print** the character count that `write_text` returns.
- **Facts are not citations.** A fact from the question is never listed among the answer's citations. The Eq 6 prompt lists the facts a result used separately from its evidence.
- **The two sequential baselines** start from Γ0q, as the executor does.

## Not changed

- **Retrieval is frozen.** The retrieval files are untouched, so the Kq file name (`kq_r8344844_…`) and the saved retrieval results stay the same.
  - Three DEV targets were missed: P33 (5B.01 ¶2), P35 (6C.01 ¶1), and P47 (9E.09 ¶11, the paragraph just before one that was found).
  - Any fix will be designed and measured on DEV only, later.
- **The checker still never sees the question.**
- **P44 is a DEV-case problem, not a pipeline one.**
  - 8A.12 ¶3 sits in a section about circular intersections (roundabouts and traffic circles). The DEV scenario, written from ¶3 alone, says "signalized intersection".
  - The parser's guard follows the manual. With the given facts, the expected answer is "does not apply".
  - The DEV case is left as it is, because the DEV set is fixed.
- **The numeric rule checker** reads numbers only from established certificates, not from a fact's text. So a number check on the question's values still goes to the text checker (the hand-over).

## Parser instructions

- **fix5.** sha256 of `PARSER_TASK + PARSER_CONTRACT`: `eca523d04ddcaa500421318fa019114d1eab14a3decee55075d882a2ae92048d`. Under fix4 it was `e177dee6…`.
- **What changed in the text:**
  - the `facts` field and its rules;
  - "the checker sees the claim, the facts and the manual, never the question";
  - the cross-reference line;
  - two new lines in RULES.
- **Every plan must be made again.** The fix4 replies stay in the cache but are not used, because the prompt changed.
- **Order:** first the DEV plans at medium and at xhigh. After the choice between them, the TEST/TEST2 plans are made once, with the chosen setting.

## How to run

**Parser_Test (A100):**
- Run CELL 1, 4, 5, 6, 7, 8, 9, 10, 11, 14, in that order.
- Skip CELL 2 and 3: retrieval is saved.
- Do not run CELL 12 or 13 (TEST, TEST2).
- Stop after CELL 9 and read the plan, including its GIVEN lines.
- Timing: CELL 10 takes about 30–50 minutes, CELL 11 about 15 minutes, and CELL 14 about 1.5–3 hours.

**Execution_Test (A100 or L4):**
- Run CELL 1 to CELL 9, then send the output of CELL 9.
- `PARSER_EFFORT` in CELL 4 picks the medium (default) or xhigh DEV plans.
- CELL 10 is the repeat check.
- The checker's prompts changed, so every call is new. That costs about $0.50 for DEV.

## Files

| File | Change |
|---|---|
| `mrag/vine/parser.py` | fix5 instructions; `fact_problems`; the exception-base check |
| `mrag/vine/compile.py` | `GivenFact`, `NetworkSpec.facts` (serialised only when there are some); fact checks in `problems()`; facts put in Γ0q by `instantiate` |
| `mrag/vine/model_verifiers.py` | GIVEN IN THE QUESTION block; a definite answer must cite manual text; the `basis` field; a FALSE's authority raised to its cited basis's printed heading |
| `mrag/vine/execute.py` | the executor keeps a shown raise; `merge_authority` |
| `mrag/vine/certificate.py` | `AUTHORITY_RANK`, `stronger`; evidence type `given` |
| `mrag/vine/run.py` | `resolve_then_read`, wired in `build_verifiers` |
| `mrag/vine/experiments.py`, `faults.py` | the reference evaluator and the sequential baselines use the same merge-authority rule; the baselines start from Γ0q |
| `mrag/vine/answer.py` | the non-conformance wording next to a decision that does not hold; facts are not citations |
| `mrag/vine/__init__.py` | exports `merge_authority` |
| `evaluation/execution_check.py`, `parser_check.py` | given facts, raised authority, hand-over by tool |
| `notebooks/Parser_Test.ipynb` | fix5 run order; checks that fix5 is pushed |
| `notebooks/Execution_Test.ipynb` | `PARSER_EFFORT`; fix5 notes; given facts in the printout |
| `tests/test_checker_fixes.py` | new: 11 groups, all on made-up data |
| `docs/PARSER_TEST_2026-10-07.md`, `EXECUTION_TEST_2026-10-08.md` | a one-line note at the top pointing here |

## How it was checked

- **All test scripts pass**, including the new one. The 3 that need files from the old setup still can't run, as before.
- **Random networks:** the executor and the brute-force reference agree on 900 of 900 random nested networks with mixed headings. In 46 of the 900, the new merge-authority rule changes the answer, so the test really exercises it.
- **Dry runs on the 11 DEV plans** used the real graph, chunks and tables, with stand-ins for the search and the model:
  - the old fix4 plans still run;
  - with given facts added, the checker prompt shows them and never the question;
  - the P35-like path raises o5 and its merge to STANDARD.
- **Notebook simulations** with a fake model server and a faked API:
  - Parser_Test ran CELL 1, 4–11 and 14, with CELL 14 reading the medium plans from the cache;
  - Execution_Test ran CELL 1 and 3–10, at both medium and xhigh.
- **An independent review** of the logic, in three rounds, by a separate agent with no access to test material.
  - **Round 1 found two real holes.** A fact could state the answer ("This panel is allowed.", allowed because the question's ask used the word), and the checker could then pass a check on that fact alone. And the whole question could be passed in as one fact.
  - **Rounds 2 and 3** closed these and the smaller points: fact ids, the basis check, a crashed resolver, and the baselines starting from Γ0q.
  - **Executor vs reference:** the reviewer's own random generators found 0 disagreements in more than 84,000 runs.
- **Leak scan of every added line:** 0 matches at 5 and 6 words.

## Limits to keep in mind

- **The fact checks are mechanical.** They can stop a fact from adding numbers, references, requirement words or new wording, but they cannot prove a fact is faithful. The checker is also told that the facts "say nothing about what the manual requires", and a fact alone settles nothing.
- **The checker chooses the basis.** A wrong basis pointing at a Standard would turn a Guidance non-conformance into a refutation. It must at least be evidence the checker says it used, and the record shows which one it was.
- **A check that could only be answered from the facts** (for example "the road is rural") now comes out UNKNOWN, because it needs manual text too. This is the safe side, but it may cost a few answers on DEV.

## A sentence for the paper

For §3.2, after Eq 3: "The facts stated in the query form the initial store Γ0q: the compiler records them as certificates, so every verifier conditions on them without seeing the query itself, and a certificate's normative authority r_i is that of the provision its evidence rests on — a failed obligation resting on a Standard refutes, whatever heading the obligation was compiled with."
