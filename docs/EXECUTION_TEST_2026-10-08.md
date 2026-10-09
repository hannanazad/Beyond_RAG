# Execution test, 8 October 2026

> **Update, 8 October 2026 (evening):** after the first run, the checkers see the plan's given facts, a FALSE takes the authority of the provision it rests on, and a cross-reference claim is read by the text checker. See `CHECKER_FIXES_2026-10-08.md` for what changed and the new run order.

## What it is

`notebooks/Execution_Test.ipynb` runs the frozen parser's DEV plans through the checkers and the executor.

1. **The plan** is read back from the parser's cache on Drive: exactly the plan the frozen parser (Qwen3.8-27B, fix4) wrote in `Parser_Test`.
   - Nothing is parsed again, and no local model is loaded.
   - The parser's settings are read from that `Parser_Test` run's `manifest.json`.
   - If a plan is not in the cache, the notebook stops and says so.
2. **The checkers** decide each check, in the order the plan allows (Eq 4):

   | Checker | What it is |
   |---|---|
   | calculator | a table lookup, no model |
   | rule checker | a numeric comparison, no model |
   | cross-reference checker | does the section, table or figure exist |
   | text and image checkers | **Claude Sonnet 5.5** (`claude-sonnet-5-5`) through the Anthropic API |

3. **The merges and the decision** are worked out by the executor, with no model. The answer is written from the certificates, also with no model.

**Only DEV cases.** No test question, gold answer or test plan is in this notebook.

## Why two different models

The draft keeps the parser and the checkers separate:
- §3.1: the compiler "does not depend on a particular LLM";
- §3.3: "different language models, vision-language models ... can be substituted".

So the parser stays open-source (Qwen3.8-27B), and the checkers use Sonnet 5.5.

**Why Sonnet 5.5:**
- Among the closed models anyone can use, it had the lowest published rate of wrong answers when unsure (AA-Omniscience, 47.0%). For a checker, saying UNKNOWN instead of guessing matters most.
- It reads images, up to 2,576 pixels on the long side.
- Price: $2 / $10 per million tokens (input / output).

**For the paper:** the RAG baseline should be run with the same model, so the comparison shows the effect of the structure, not of a different model.

## Repeatable by caching, not by temperature

Sonnet 5.5 rejects any non-default `temperature`, `top_p` or `top_k` (a 400 error), and its thinking is always adaptive.
- **Every checker reply is saved** in `parser_runs/checker_cache/`. Each file holds the prompt, the images' hashes, the reply, any thinking text, the stop reason, the token usage and the request id. A re-run reads the saved replies.
- **CELL 10** asks the checker again, without the saved replies, on 3 DEV cases, and counts how many results come out differently. That is the number to report.
- **Settings:** effort `high` (the model's default, and what Anthropic recommends starting with), `max_tokens` 32,000 (thinking plus reply), at most 4 images per check.

## Three things that were missing, and what was done

**1. The checkers did not see the evidence the plan points to.**
- The parser writes, for each check, its source paragraph (`source_chunk`) and where its evidence is (`evidence_hint`).
- The text and image checkers only searched with the claim's words (Eq 5).
- **Now:** each text and image check first gets the pointed evidence, looked up by id with no model (`mrag/vine/pointers.py`). That means the source paragraph, the hinted paragraphs, a hinted section if it is small enough to take whole, and a hinted table or figure with its notes.
- The Eq 5 search then adds to it.
- The retrieval code that builds the parser's input (`mrag/retrieval.py`) is not changed.

**2. A calculator or rule check that could not decide stayed UNKNOWN.**
- **Now:** if it returns UNKNOWN, the text checker gets the check, and both attempts are recorded.
- A definite TRUE or FALSE from the exact tool is kept, and the model is not asked.
- Paper basis, §3.3: exact tools "whenever the obligation admits" them; a model "where interpretation is necessary".

**3. No client for an API checker with images.**
- **Now:** `mrag/vine/anthropic_client.py`. It sends the images first, then the text, plus `output_config.effort`.
- It never sends temperature or a thinking setting.
- An image larger than 2,576 pixels on its long side is shrunk to that size first (the model would do the same itself).
- When the API is busy (429 or 529), it waits and tries again.
- It has a cache-only mode, and the cost is counted from the token usage.

## How to run

1. Push the files below.
2. In Colab, add your key to the secrets (the key icon on the left) as **`ANTHROPIC_API_KEY`**, and allow the notebook to use it.
3. Choose a **GPU runtime (A100 or L4)**. The GPU is only for the retrieval models; no model server is started.
4. Run `Execution_Test` **CELL 1 to CELL 8**.
5. **Stop after CELL 8 and send me its output.** It is one DEV case, check by check.
6. Then CELL 9 runs all 11 DEV cases, and CELL 10 does the repeat check.

**Cost:** the dry run's estimate for the 11 DEV cases was about $0.30, but thinking makes real replies longer, so expect a few dollars. Each record shows its cost.

**The xhigh parser test** (`Parser_Test` CELL 14, DEV only) is separate. It needs the A100 and the Qwen model server: run CELL 1, 4, 5, 6, 7, 8, then 14.

## Files

| File | Change |
|---|---|
| `notebooks/Execution_Test.ipynb` | new: the execution test (10 code cells) |
| `notebooks/Parser_Test.ipynb` | new CELL 14 (DEV at xhigh); CELL 1–13 unchanged |
| `mrag/vine/anthropic_client.py` | new: Claude through the API, every reply saved |
| `mrag/vine/pointers.py` | new: the evidence a plan points to, by id |
| `evaluation/execution_check.py` | new: prints and summarizes executed plans (no gold) |
| `mrag/vine/model_verifiers.py` | pointed evidence first; at most 4 images; missing image files skipped |
| `mrag/vine/run.py` | `hand_over_when_undecided`; `build_verifiers` takes `hand_over` and `model_options` |
| `mrag/vine/vllm_client.py` | `cache_only` (read saved plans without a server); a smaller window if the memory is short |
| `mrag/vine/network.py`, `compile.py` | an operation carries its `source_chunk` |
| `tests/test_execution_wiring.py` | new: 9 groups, all on made-up data |
| `tests/test_model_verifiers.py` | its image test now writes real temporary files |

The parser's instructions are **not** changed (still fix4). Neither is the retrieval code.

## How it was checked

- **All tests pass.** The 3 that need files from the old setup still can't run, as before.
- **Dry runs on this machine** of the 11 real DEV plans from fix4, with the real VINE graph, chunks and tables. The search, reranker and model were stand-ins, and the statuses mean nothing; only the wiring was tested.
  - **Through the plain checker path:** all 48 checks settled; every model check got the evidence its plan pointed to (47 of 47); 3 calculator or rule checks were handed over.
  - **Through the real Sonnet client code, with only the network faked:** the same results, every call saved, and the cost counted.
- **Leak scan of every added line:** 0 matches at 5 and 6 words. At 4 words there is 1 match: the plan format's own field names (`"obligations": [{"id": "o1", "claim": ...`), which come from `compile.py`.

## What could still go wrong on Colab

- **A plan not in the cache:** this happens if the `Parser_Test` run's manifest doesn't match the saved replies. CELL 6 stops and names the case.
- **The API key is not loaded:** CELL 5 stops with the steps to fix it.
- **A refusal or a reply cut off by `max_tokens`:** that check comes out UNKNOWN, and the stop reason is in the record.
