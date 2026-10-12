"""hprc/compare_plans.py -- did the repeat run make the same DEV plans as the first run?

    $SCRATCH/vine/envs/retrieval/bin/python hprc/compare_plans.py NAME

NAME is the repeat run's name (bash hprc/run.sh ACCOUNT GPUS repeat NAME). For
every plan in parser_runs_faster/repeat_NAME/e2e_<...>/plans.json, this checks it
against the plan for the same question in parser_runs_faster/e2e_<...>/plans.json
(the first run; the folder name holds the retrieval code, the store and the
parser instructions, so the two folders have the same name):

  1. the same input   : the prompt sent to the model has the same SHA-256, and
                        the same settings (model, seed, sampling, max_tokens)
  2. a new model call : the repeat's reply did not come from the first run's
                        cache (it has its own, which starts empty)
  3. the same output  : the model's whole reply -- its reasoning and its answer --
                        and the plan made from it are the same, byte for byte

Which GPU made a plan, and how long it took, are allowed to differ.

It only reads files (and writes compare.json in the repeat folder). Exit 0 when
every plan is the same, 1 when any differs, 2 when it cannot compare.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# manifest fields that may differ between two runs without changing a plan
_FREE = {"commit", "slurm_job", "gpu", "servers", "server_command"}


def load(path):
    return json.loads(Path(path).read_text())


def same_json(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def first_difference(a, b):
    """Where two texts first differ, with a little of each from there."""
    a, b = a or "", b or ""
    n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return {"at": n, "of": [len(a), len(b)], "first": a[max(0, n - 40):n + 80], "repeat": b[max(0, n - 40):n + 80]}


def model_reply(cache_dir, key):
    """The cached reply a call got: {content, reasoning, finish_reason, tokens}, or None."""
    p = Path(cache_dir) / f"{key}.json"
    if not key or not p.exists():
        return None
    try:
        rec = load(p)
    except (OSError, ValueError):
        return None
    return {"content": rec.get("content") or "", "reasoning": rec.get("reasoning") or "",
            "finish_reason": rec.get("finish_reason"),
            "tokens": (rec.get("usage") or {}).get("completion_tokens")}


def compare_one(old, new, old_cache, new_cache):
    """One question: (verdict, details). Verdicts, most basic cause first:
    SAME, NO FIRST PLAN, INPUT DIFFERS, SETTINGS DIFFER, MODEL REPLY DIFFERS,
    PLAN DIFFERS."""
    d = {"notes": []}
    if old is None:
        return "NO FIRST PLAN", d
    if old.get("question") != new.get("question"):
        return "INPUT DIFFERS", dict(d, why="the question text is not the same")
    oc, nc = old.get("calls") or [], new.get("calls") or []
    d["calls"] = [len(oc), len(nc)]
    for c in nc:
        if c.get("cached"):
            d["notes"].append("a reply came from this repeat run's own cache (the job was submitted again)")
    for c in oc:
        if c.get("cached"):
            d["notes"].append("in the first run a reply came from a cache made before it")
    # 1. the same input, call by call (a plan repaired after a bad reply makes more than one call)
    for i, (a, b) in enumerate(zip(oc, nc)):
        if a.get("prompt_sha256") != b.get("prompt_sha256"):
            return "INPUT DIFFERS", dict(d, why=f"call {i + 1}: the prompt sent to the model is not the same")
        if a.get("cache_key") != b.get("cache_key"):
            return "SETTINGS DIFFER", dict(d, why=f"call {i + 1}: same prompt, but other settings "
                                                  "(model, seed, sampling or max_tokens)")
    # 3. the same output: the whole reply, from both caches when they are there
    for i, (a, b) in enumerate(zip(oc, nc)):
        ra, rb = model_reply(old_cache, a.get("cache_key")), model_reply(new_cache, b.get("cache_key"))
        if ra is None or rb is None:
            d["notes"].append(f"call {i + 1}: a cached reply is missing, so its reasoning was compared by length only")
            if (a.get("reasoning_chars"), a.get("content_chars"), a.get("finish_reason")) != \
                    (b.get("reasoning_chars"), b.get("content_chars"), b.get("finish_reason")):
                return "MODEL REPLY DIFFERS", dict(d, why=f"call {i + 1}: reasoning or reply length differs",
                                                   lengths=[[a.get("reasoning_chars"), a.get("content_chars")],
                                                            [b.get("reasoning_chars"), b.get("content_chars")]])
            continue
        for part in ("reasoning", "content"):
            if ra[part] != rb[part]:
                return "MODEL REPLY DIFFERS", dict(d, why=f"call {i + 1}: same prompt and settings, "
                                                          f"but the model's {part} is not the same",
                                                   tokens=[ra["tokens"], rb["tokens"]],
                                                   finish=[ra["finish_reason"], rb["finish_reason"]],
                                                   where=first_difference(ra[part], rb[part]))
        if ra["finish_reason"] != rb["finish_reason"] or ra["tokens"] != rb["tokens"]:
            return "MODEL REPLY DIFFERS", dict(d, why=f"call {i + 1}: same text, other finish or token count",
                                               tokens=[ra["tokens"], rb["tokens"]],
                                               finish=[ra["finish_reason"], rb["finish_reason"]])
    if len(oc) != len(nc):
        return "MODEL REPLY DIFFERS", dict(d, why=f"{len(oc)} model calls in the first run, {len(nc)} now")
    if (old.get("raw_replies") or []) != (new.get("raw_replies") or []):
        return "MODEL REPLY DIFFERS", dict(d, why="the replies kept in plans.json are not the same")
    # the plan made from the same replies
    for k in ("spec", "outcome", "attempts", "problems", "stats"):
        if not same_json(old.get(k), new.get(k)):
            return "PLAN DIFFERS", dict(d, why=f"same model replies, but '{k}' is not the same "
                                               "(the code that turns a reply into a plan)")
    return "SAME", d


def compare(runs, name):
    runs = Path(runs)
    root = runs / f"repeat_{name}"
    found = sorted(root.glob("e2e_*/plans.json"))
    if not found:
        print(f"no plans in {root}/e2e_*/ -- has the repeat job finished? (squeue -u $USER)")
        return 2, None
    report = {"repeat": name, "folders": []}
    all_same = True
    for new_file in found:
        folder = new_file.parent.name
        old_file = runs / folder / "plans.json"
        print(f"repeat run : {new_file}")
        print(f"first run  : {old_file}")
        if not old_file.exists():
            print(f"\nCANNOT COMPARE: there is no first run in {runs / folder}. Its name holds the retrieval\n"
                  "code, the store and the parser instructions, so one of them changed between the two runs.")
            return 2, None
        old_plans, new_plans = load(old_file), load(new_file)
        # the settings the servers ran with
        mo = (load(runs / folder / "parse_manifest.json") if (runs / folder / "parse_manifest.json").exists() else {})
        mn = (load(new_file.parent / "parse_manifest.json") if (new_file.parent / "parse_manifest.json").exists() else {})
        diff = sorted(k for k in set(mo) | set(mn) if k not in _FREE and not same_json(mo.get(k), mn.get(k)))
        if mo and mn:
            print("settings   : " + ("the same (model, revision, vLLM, seed, sampling, effort, max_tokens, window, "
                                     "instructions, Kq, retrieval)" if not diff else "DIFFERENT in " + ", ".join(diff)))
            print(f"servers    : {mo.get('servers')} in the first run (job {mo.get('slurm_job')}), "
                  f"{mn.get('servers')} now (job {mn.get('slurm_job')})")
        print()
        print(f"{'question':26s} {'result':20s} {'GPU':8s} {'seconds':13s} why")
        rows = []
        for qid in new_plans:
            old, new = old_plans.get(qid), new_plans[qid]
            verdict, d = compare_one(old, new, runs / "model_cache", root / "model_cache")
            gpu = f"{(old or {}).get('gpu_slot', '-')} -> {new.get('gpu_slot', '-')}"
            secs = f"{(old or {}).get('seconds', 0):5.0f} / {new.get('seconds', 0):5.0f}"
            print(f"{qid:26s} {verdict:20s} {gpu:8s} {secs:13s} {d.get('why', '')}")
            if d.get("where"):
                w = d["where"]
                print(f"{'':26s}   first difference at character {w['at']:,} (lengths {w['of'][0]:,} / {w['of'][1]:,}); "
                      f"tokens {d['tokens'][0]} / {d['tokens'][1]}")
                print(f"{'':26s}   first : {w['first']!r}")
                print(f"{'':26s}   repeat: {w['repeat']!r}")
            for note in sorted(set(d.get("notes") or [])):
                print(f"{'':26s}   note: {note}")
            rows.append({"case_id": qid, "verdict": verdict, **d,
                         "gpu": [(old or {}).get("gpu_slot"), new.get("gpu_slot")],
                         "seconds": [(old or {}).get("seconds"), new.get("seconds")]})
        same = sum(1 for r in rows if r["verdict"] == "SAME")
        all_same = all_same and same == len(rows) and not diff
        by_length = sum(1 for r in rows if r["verdict"] == "SAME"
                        and any("by length only" in n for n in r.get("notes") or []))
        print(f"\n{same} of {len(rows)} plans are the same as in the first run "
              "(the prompt, the model's reasoning and reply, and the plan).")
        if by_length:
            print(f"BUT for {by_length} of them a cached reply was missing ({runs / 'model_cache'} or "
                  f"{root / 'model_cache'}),\nso the model's reasoning was compared by its length only, "
                  "not byte for byte.")
        elif same:
            print("All of these were compared byte for byte, the model's reasoning included.")
        report["folders"].append({"folder": folder, "settings_differ": diff, "rows": rows,
                                  "same": same, "of": len(rows)})
    (root / "compare.json").write_text(json.dumps(report, indent=1))
    print(f"saved -> {root / 'compare.json'}")
    return (0 if all_same else 1), report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="the repeat run's NAME")
    ap.add_argument("--runs", help="the parser_runs_faster folder (default: $SCRATCH/Beyond_RAG/parser_runs_faster)")
    a = ap.parse_args(argv)
    runs = a.runs or (Path(os.environ.get("SCRATCH", "")) / "Beyond_RAG" / "parser_runs_faster")
    return compare(runs, a.name)[0]


if __name__ == "__main__":
    sys.exit(main())
