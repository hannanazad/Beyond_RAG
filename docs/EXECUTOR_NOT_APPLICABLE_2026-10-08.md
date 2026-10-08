# Branches that do not apply, 8 October 2026

## The problem

A guard is a "run this check only if…" condition. When a guard stayed closed, the guarded check never ran. Any merge that waited for that check then waited forever, so the answer came out UNKNOWN even when every fact was known.

**Example (a made-up rule):** "A work-zone sign must be orange. If the work is at night, the sign must also be lit."

| Check | What it asks |
|---|---|
| A | Is the sign orange? |
| B | Is the work at night? |
| C | Is the sign lit? (guard: B is TRUE) |
| M | Both A and C pass |

For day work:
- B is FALSE, so C never ran.
- M waited for C forever.
- The answer was UNKNOWN. The right answer is "yes", because the lighting rule does not apply in daytime.

**How often:** in a dry run of the 33 DEV plans, the old executor got stuck in 298 of 3,300 runs, across 8 plans.

## The fix

A check that does not apply now gets its own result, **NOT_APPLICABLE**, instead of no result. A merge leaves it out. In the example, M is decided by A alone.

This is the standard fix for the same problem in workflow engines, called **dead-path elimination**. A skipped branch passes on a "dead" signal instead of nothing, and a step whose inputs are all dead is skipped too. In Völzer's words: "if all inputs are false, all outputs are false as well". Sources: WS-BPEL 2.0 (OASIS, 2007); H. Völzer, *A New Semantics for the Inclusive Converging Gateway in Safe Processes*, IBM Research RZ 3791, 2010.

## The rules

The draft (§3.2) says: "If a mandatory predecessor remains Unknown and the conclusion cannot otherwise be determined, the merged result also remains Unknown." The same rule is now used for guards and for prerequisites too. **Nothing is decided unless it would come out the same however every UNKNOWN result turned out.**

| Situation | Result |
|---|---|
| Guard open however its UNKNOWN results turn out | the check runs |
| Guard closed however they turn out | NOT_APPLICABLE |
| Guard open for some outcomes and closed for others | UNKNOWN ("whether it applies is unknown") |
| Every prerequisite does not apply | NOT_APPLICABLE |
| Every prerequisite does not apply or may not apply | UNKNOWN ("whether it applies is unknown") |
| At least one prerequisite applies | the check runs; its checker is told which ones do not apply |
| **Merge:** an input does not apply | left out |
| **Merge:** no input applies | NOT_APPLICABLE |
| **Exception merge:** the exception does not apply | the base rule decides |
| **Exception merge:** the base rule does not apply | NOT_APPLICABLE (there is no rule to relax) |
| **Merge:** an input may or may not apply | both possibilities are tried; the result is definite only if both agree |

**Who decides:** only the executor decides that a check does not apply. A checker (LLM, VLM, calculator) can only answer TRUE, FALSE or UNKNOWN. If one says "not applicable", it is read as UNKNOWN.

**What a guard reads:** a guard reads statuses exactly as the parser was told: TRUE, FALSE, UNKNOWN, or RESOLVED (TRUE or FALSE). A result that does not apply matches none of these.

**In the answer:**
- A TRUE or FALSE answer also lists the checks that did not apply.
- A NOT_APPLICABLE answer says "this does not apply to the situation described" and names the established results that decided it.

## What it changes in the paper

- **Eq 3:** a certificate's status can now also be NOT_APPLICABLE. Only the executor issues it, and only from results already established.
- **Eq 4:** unchanged. g_o is still open or closed. The executor also notes *why* a guard is closed.
- **Suggested sentence for §3.2:** "A branch whose guard is closed by established results is marked not applicable, and typed merges exclude it (dead-path elimination); a guard that depends on an unresolved result leaves the branch unresolved."
- **Synchronization depth:** checks found not to apply are not run, so they add no wave to the depth.

## How it was checked

1. **New test file `tests/test_not_applicable.py`:** 15 groups, all on made-up rules. It includes the following checks.
   - **Guards:** a brute-force check of 12,016 guard and status cases. No decided guard would change if an UNKNOWN result were known.
   - **Whole networks:** 400 random networks. 1,227 definite answers were each re-run for every way their UNKNOWN checks could have turned out (13,661 cases), and none changed.
   - **Agreement:** the executor agrees with an independent, brute-force reference (`experiments.reference_terminal`) on every run.
2. **Existing tests:** all still pass.
   - The live parts of `test_experiments`, `test_faults` and `test_compile` also pass, run on the real manual chunks.
   - Three tests (`test_compile_closure`, `test_obligation_retrieval`, `test_xref_resolver`) need files from an old setup. They fail the same way on the unchanged code.
3. **DEV dry run:** the 33 DEV plans from the three DEV runs, each with 100 sets of made-up checker results.

   | | Old executor | New executor |
   |---|---|---|
   | Runs stuck | 298, in 8 plans | 0 |
   | Agreement with reference | — | 3,300 of 3,300 |

   125 runs that used to end UNKNOWN now get an answer: 67 FALSE, 46 TRUE, 12 NOT_APPLICABLE.
4. **Independent review:** a separate reviewer checked three versions.
   - The first two versions had real safety bugs, in which an UNKNOWN fact could end up as "does not apply". Both are fixed.
   - On the final version the reviewer found no safety problems in 38,400 random networks.
   - It also found that the reference had become too slow on wide sections. This is fixed: section 1C.02, with 293 inputs, now takes 0.0 s.
5. **Leak scan:** every line added was checked for 4-, 5- and 6-word phrases that appear in the test material but not in the manual. The test material is the 20 sample questions with their gold answers and notes, plus the 150 MUTCD-150 records. The scan found 0 at every length.

No sample question, gold answer or test plan was used to design or tune anything. The only real plans used were the DEV plans, and only for the dry run.

## Files

| File | Change |
|---|---|
| `mrag/vine/certificate.py` | adds the NOT_APPLICABLE status and `applicability_unknown()` |
| `mrag/vine/network.py` | adds `Gate` (open / closed / undecided / pending); `Operation` gains `guard_eval` and `guard_spec` |
| `mrag/vine/compile.py` | guards are evaluated for every way their UNKNOWN results could turn out |
| `mrag/vine/execute.py` | settles checks that do not apply; merges leave them out; inputs that may not apply are tried both ways |
| `mrag/vine/experiments.py` | the reference evaluator handles all this independently; "w/o guards" also clears the new guard fields |
| `mrag/vine/faults.py` | "Unconstrained chain" also clears the new guard fields |
| `mrag/vine/answer.py` | the answer text and prompt for NOT_APPLICABLE; the "Decided by" list |
| `mrag/vine/model_verifiers.py` | the checker's prompt shows "DOES NOT APPLY HERE" in words |
| `mrag/vine/run.py` | the summary and saved output list not-applicable and undecided checks |
| `mrag/vine/__init__.py` | exports `Gate` |
| `evaluation/parser_check.py` | a comment only |
| `tests/test_not_applicable.py` | new |

The parser is **not** changed. Its instructions are still frozen at fix4 (e7ae691).

## Known limits

- **A guard of the form "X is UNKNOWN" can never open now.**
  - While X is unknown, knowing X could close it, so the check is UNKNOWN. Once X is known, the check does not apply.
  - So a "fallback when X cannot be checked" branch always ends UNKNOWN or not applicable. This is the safe side.
  - The parser text still allows UNKNOWN as a guard status. No DEV plan used it: all 18 DEV guards are "X is TRUE" (15) or "X is RESOLVED" (3).
- **Size limits:** a guard with more than 8 uncertain results, or a merge with more than 10 inputs that may not apply, is answered UNKNOWN without trying every case. Real plans are far below both limits.
- **Speed:** `test_faults.py` takes about 15% longer (7 min 10 s, against 6 min 12 s before).
