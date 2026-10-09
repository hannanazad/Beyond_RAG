# The checker reads like an engineer who signs — 9 October 2026

Everything here was found and tested on DEV cases only (written from the MUTCD
itself). No sample question, test question or gold answer was used.

## What changed, in one line each

1. **How to read a claim.** The checker's instructions now say how a claim is
   judged, and quote the manual's own reading rules.
2. **Labels.** Every piece of the manual the checker sees is shown with its
   section number and title, paragraph, heading, and its links in the graph.
3. **Lookups.** While it decides, the checker can open more of the manual
   itself (read-only, at most 12 lookups per check, every lookup logged).
4. **Exception check.** If an answer rests on a provision that names an
   exception the checker has not read, the exception is handed to it and it
   answers again, once.
5. **DEV cases corrected.** An audit of all 154 DEV cases found 9 written
   about a situation their provision does not cover (P44 among them). They are
   corrected in `manual_cases_v2.jsonl`.

## Why (what went wrong before)

- **P24:** the checker judged the rule in general instead of the case, even
  though the facts of the case were in front of it.
- **P01:** the checker read "1D.06 applies" as FALSE, and the mistake was then
  passed on to later checks.
- The checker saw each piece as `[id] (2B.03 Standard)` and its text: no title,
  no paragraph number, and nothing about the exceptions the piece names. It
  could not look anything up.

## What the paper says (why this is allowed)

- §3.3: "All verification remains grounded in the persistent knowledge graph."
- §3.3: "Nq in turn issues obligation-specific requests back to the graph as
  execution proceeds."
- §3.3: retrieval for a check "can focus on provisions, definitions,
  thresholds, figures, and exceptions associated with that category."

The lookups are such requests to the graph. The checker still never sees the
question, and still answers only TRUE, FALSE or UNKNOWN (§3.2, §3.4). There is
no "certified, with a warning".

## 1. How to read a claim (`READING_RULES` in `model_verifiers.py`)

- **Judge the case, not the rule in general.** The case is what GIVEN IN THE
  QUESTION and ALREADY ESTABLISHED describe.
- **"The manual requires / allows / prohibits X":**
  - TRUE when a provision says so for a case like this one;
  - FALSE when the manual says otherwise for this case (a different value, a
    prohibition, or an exception, condition or Option that covers it).
- **"Provision P applies":**
  - TRUE when the case falls under P (P's subject and conditions fit the
    facts);
  - it does not ask whether the case obeys P.
- **A statement about the case itself:**
  - FALSE when a fact contradicts it;
  - UNKNOWN when the facts do not say.

The manual's own rules, quoted word for word:

- **1C.01:** the four headings. "Standard statements are sometimes modified by
  Option statements." "Option statements sometimes contain allowable
  modifications to a Standard or Guidance statement."
- **"Except as provided in Section X / Paragraph N":** the exception is part of
  the rule.
- **"Except as otherwise provided in this Manual":** look for the provision
  about the specific device or situation.
- **1A.04 Paragraph 5:** tables, figures and their notes.
- **1A.04 Paragraph 6:** numerals on figure images are examples only.
- **1B.03 Paragraph 9:** not prohibited does not mean allowed. But what you
  have not read is not absent from the manual: look further, or answer
  UNKNOWN.

## 2. Labels (`mrag/vine/lookup.py`, `ManualView`)

Example:

```
[MUTCD11e_2B03_Standard_03] Section 2B.03 "Size of Regulatory Signs" · paragraph 3 · Standard
Except as provided in Paragraphs 5 and 6 of this Section, the minimum sizes ...
  links: exceptions it names: Section 2B.03 paragraph 5, Section 2B.03 paragraph 6 | refers to: Table 2B-1 | notes printed with: Table 2B-1 | Option paragraphs in this section: 5, 6 | terms the manual defines: "conventional road", ...
```

- **Only links that go out of the piece.** On 9 October we agreed the manual
  names a rule's exceptions in the rule itself: at least 160 rules say "Except
  as provided in …". Only about 50 rules out of about 7,000 say "except as
  otherwise provided in this Manual" without naming where.
- **Exceptions:**
  - a reference in parentheses ("(see definition in Section 1C.02)") is a
    reference, not an exception;
  - "Sections 2F.12 through 2F.16" counts every section in between;
  - a section named whole as an exception is handed over whole only when it is
    short (8 normative paragraphs or fewer); a long one is named so the checker
    can open it.
- **The paragraphs a pointed provision names as its exceptions are added to
  the evidence** (up to 6). This closes a gap we found: the checker used to
  follow no links from the paragraphs the plan gave it.
- **What a piece is (note or paragraph, heading, paragraph number) always comes
  from the graph's own record,** never from a copy that an earlier step
  re-tagged.

## 3. Lookups (`Lookups`, and `ask.converse` in `anthropic_client.py`)

**The tools:**

| tool | what it returns |
|---|---|
| `open_section(section, from_paragraph)` | up to 10 paragraphs at a time |
| `open_paragraph(section, paragraph, from_item)` | a paragraph with the ones before and after |
| `open_table_or_figure(id, from_row, row_contains)` | notes always; rows by page or by matching text; the figure description |
| `define_term(term)` | the term's definition |
| `search_manual(query)` | the same hybrid search and reranker the pipeline uses; 6 results |

**Limits:**
- Every result is at most about 12,000 characters. Long sections, lists and
  tables say how to read on.
- 12 lookups per check. Lookups beyond that are answered with "the limit is
  reached, answer now". A model that keeps asking ends with no answer
  (UNKNOWN).

**Kept exactly as the API requires** (checked against the current docs on
9 October):
- every earlier model turn is sent back unchanged, with its thinking blocks;
- every tool call gets one result, first in the next message;
- the tools and the effort never change inside one check, and no
  `tool_choice` is sent;
- the stop reason is read first: a refusal, a reply cut off by the token limit
  or the context window gives no answer (UNKNOWN), and a cut-off tool call is
  never run;
- an empty reply is not sent back; one new message asks for the answer.

**Repeatable:**
- every turn is saved in the reply cache under a key of everything sent so far;
- search results are saved by query (`checker_cache/lookup_search/`), so a
  re-run on another GPU sees the same pieces;
- a re-run replays the whole conversation with no API call (tested).

**Cost:**
- the instructions and the tool list are marked for the API's prompt cache;
  later turns read them at 5% of the price;
- the cost printed counts cache writes ($2.50 per million tokens) and cache
  reads ($0.10 per million tokens) at the prices on the pricing page.

## 4. The exception check (`_exception_gate` in `model_verifiers.py`)

After a TRUE or FALSE, once:
- **Named exceptions not read yet** are handed over (at most 16; the rest are
  named), with: "If one of them covers this case, the answer must follow it."
- **Long sections named whole that it has not opened** → it is asked to open
  them.
- **An exception said to exist "otherwise" with no place named** → it is
  asked to look for the specific provision.

It then answers again. Both answers are recorded (`first_answer` and the
final status).

## What each check records

| record | meaning |
|---|---|
| `lookups` | every lookup: tool, input, ids returned, size |
| `found_by_checker` | manual text it cited that it was not first given (what retrieval and the plan missed); exceptions the exception check handed over are counted separately, in `cited_handed_over_exceptions` |
| `named_exceptions` | exceptions named by the pointed paragraphs and added to the evidence |
| `handed_over_exceptions`, `asked_to_open_sections`, `asked_to_look_for_specific_provision`, `first_answer` | what the exception check did, and the answer before it |
| `conversation` | turns, lookups, refused lookups, cache keys; `conversation_stopped` when it ended without an answer |

`evaluation/execution_check.py` prints all of these (lines `looked`, `found`,
`except.`, `handed`, `asked`, `changed`, `stopped`) and sums them in the
summary.

## 5. DEV cases corrected (`evaluation/retrieval_dev/manual_cases_v2.jsonl`)

**How the audit was done:**
- Five independent reviewers each checked one batch against the full text of
  the target sections. Every PROBLEM was then checked by hand.
- The record is `evaluation/retrieval_dev/dev_audit_2026-10-09.json`:
  130 OK, 15 MINOR, 9 PROBLEM.

**Corrected (same id; the case keeps `previous_text` and `revised` with the
reason):**

| case | what was wrong |
|---|---|
| P44-plain_words, P44-scenario | 8A.12 is only about roundabouts and traffic circles near a grade crossing; the cases said an ordinary or signalized intersection |
| P09-scenario | passing on the shoulder is 2B.43 Paragraph 2 (R4-18); the source is Paragraph 1 (R4-17, shoulder as a travel lane) |
| P16-scenario | a stop sign hidden by a pier makes the Stop Ahead sign required (2C.35 Paragraph 1), not the "may" of 2E.31 Paragraph 5 |
| P23-scenario | an all-way STOP intersection is 3C.02 Paragraph 3; the source Paragraph 2 follows the paragraph on signalized locations |
| P27-scenario | a green arrow across a crosswalk during WALK is decided by 4F.01 Paragraph 3, not 4I.06 Paragraph 3 |
| P31-scenario | at the stem of a T, a shared left/right lane requires a CIRCULAR RED (4F.16 Paragraph 7); the lanes are now stated |
| P37-scenario | loose gravel has standard signs (2C.30, 6H.19); the case said none existed |
| T06-two_section_linked | the hidden signal makes the Signal Ahead sign required; the case asked what "may" be used |

**Other changes:**
- **Reworded only (same meaning):** P07, P11 and P12 scenarios. Each shared a
  five-word run with a text outside the DEV set, by chance.
- **MINOR cases kept as they are:** none of them changes the answer. The
  reasons are in the audit file.
- **`manual_cases_v1.jsonl` is kept unchanged:** the retrieval test of 7
  October was run on it.

**Of the 11 DEV cases in the parser and execution tests, only P44-scenario
changed.**
- Parser_Test CELL 5 now retrieves a case again when its text changed.
- Execution_Test CELL 4 stops if a case was corrected after it was retrieved.

## How often retrieval misses a needed section (measured 7 October, DEV only)

Retrieval test of 7 October (`retrieval_test_20261007_052206.json`, commit
8344844). The retrieval code has not changed since.

| style | target section in Kq | source paragraph in Kq |
|---|---|---|
| manual words | 48/48 | 48/48 |
| plain words | 45/48 | 43/48 |
| scenario | 40/48 | 38/48 |
| two sections, linked | 6/7 | – |
| two sections, unlinked | 2/3 | – |

In all, 17 of 154 cases miss a needed section or paragraph. P44-plain was one
of the misses, and it was a badly written case. The checker's own search per
claim (Eq 5) is a second chance: in P35 it found 6C.01 Paragraph 1, which Kq
had missed.

## How it was tested

- `tests/test_checker_lookups.py` (new, made-up data):
  - links, labels, lookups, size limits, the saved search;
  - the conversation against a strict stand-in API (turns echoed, results
    first, tools fixed, cache marks, limit, nudge, stop reasons, replay from
    the cache, cost);
  - the checker (rules, labels, named exceptions, the exception check, the
    plain path).
- All 15 test scripts pass.
- **Dry run of the 11 xhigh DEV plans:**
  - setup: the real graph, the real chunks and the real client code, with a
    strict stand-in API (the model's answers are fake);
  - 0 breaches of the API rules;
  - a replay from the reply cache gives identical results with 0 API calls.
- **Both notebooks were run end to end in a simulator:**
  - Parser_Test: CELL 1-8 and 14, plus a changed case re-retrieved;
  - Execution_Test: CELL 1-10, with the lookup probe.
- **An independent code review, then a second pass by the same reviewer on
  every fix.** All findings were fixed: "see Section X" read as an exception,
  results that were too large, a re-tagged note looking like a paragraph, and
  the stop-reason cases. The second pass confirmed the fixes.
- **Leak scan:** 0 matches of 5 or 6 words.

## What to run (Colab)

1. **Parser_Test: CELL 1, 2, 3, 4, 5, 6, 7, 8, 14.**
   - CELL 2 and 3 are needed: CELL 5 retrieves P44-scenario again.
   - In CELL 14, 10 plans come from the cache and P44 is parsed afresh at
     xhigh (about 10 minutes).
2. **Execution_Test: CELL 1 to 9, then 10.**
   - CELL 5 has a new lookup probe. If it fails, stop and send the output.
   - Rough cost for CELL 9: **$3–8, 45–90 minutes**; CELL 10 adds about a
     quarter.
3. Send the output of CELL 9 (and 10).
