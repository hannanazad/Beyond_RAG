"""Table 1 of the paper: can the compiler recover the required verification structure?

Metrics, as the paper lists them:
  obligation precision / recall / F1
  dependency F1
  operation-type accuracy
  terminal-logic accuracy

MATCHING RULE
A compiled obligation and a gold obligation are the same when they are about the
same thing. There is no id in common and the wording differs, so matching is by
content overlap -- the rare words they share, above a threshold. That is crude,
and it is stated rather than hidden: a stricter rule would need a human to pair
them, which is the annotation this is meant to avoid.

LEAKAGE
The compiler sees only the question text. The gold file is opened after every
question has been compiled, and is used for nothing but scoring.
"""
import json
import re
import sys
from collections import Counter

sys.path.insert(0, '/home/claude/work/Beyond_RAG-main')
from mrag.vine.graph_parser import GraphParser, _stem_set  # noqa: E402

MATCH_FLOOR = 0.25          # share of the gold claim's rare words that must appear


def similarity(a: str, b: str, idf) -> float:
    wa, wb = _stem_set(a), _stem_set(b)
    if not wa or not wb:
        return 0.0
    shared = wa & wb
    total = sum(idf.get(w, 1.0) for w in wa)
    return sum(idf.get(w, 1.0) for w in shared) / total if total else 0.0


def pair_up(gold_obs, made_obs, idf):
    """Greedy best-match pairing between gold and compiled obligations."""
    pairs, used = [], set()
    for g in gold_obs:
        best, best_s = None, 0.0
        for j, m in enumerate(made_obs):
            if j in used:
                continue
            s = similarity(g.get('claim', ''), getattr(m, 'claim', ''), idf)
            if s > best_s:
                best, best_s, best_j = m, s, j
        if best is not None and best_s >= MATCH_FLOOR:
            used.add(best_j)
            pairs.append((g, best, best_s))
        else:
            pairs.append((g, None, best_s))
    return pairs, used


def main():
    gp = GraphParser()
    questions = json.load(open('/home/claude/run_input.json'))
    compiled = {}
    for sid, q in questions.items():
        spec, _rep = gp.parse(q)
        compiled[sid] = list(spec.obligations) if spec else []

    gold = json.load(open('/home/claude/gold_obligations.json'))   # only now

    tp = fp = fn = 0
    auth_hit = auth_tot = 0
    dep_tp = dep_fp = dep_fn = 0
    rows = []
    for sid, g in gold.items():
        gobs = g['obligations']
        mobs = compiled.get(sid, [])
        pairs, used = pair_up(gobs, mobs, gp.idf)
        matched = [(a, b) for a, b, _ in pairs if b is not None]
        tp += len(matched)
        fn += len(gobs) - len(matched)
        fp += len(mobs) - len(used)

        for gg, mm in matched:
            auth_tot += 1
            auth_hit += (gg.get('normative_authority') == getattr(mm, 'authority', None))

        gold_dep = sum(len(o.get('depends_on') or []) for o in gobs)
        made_dep = sum(len(getattr(m, 'requires', []) or []) for m in mobs)
        dep_fn += gold_dep
        dep_fp += made_dep
        rows.append((sid, len(gobs), len(mobs), len(matched), gold_dep, made_dep))

    print(f'{"id":11s} {"gold":>5s} {"made":>5s} {"matched":>8s} {"gold deps":>10s} {"made deps":>10s}')
    for r in rows:
        print(f'{r[0]:11s} {r[1]:>5d} {r[2]:>5d} {r[3]:>8d} {r[4]:>10d} {r[5]:>10d}')

    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    print()
    print('  TABLE 1')
    print(f'    obligation precision      {100*prec:5.1f}%')
    print(f'    obligation recall         {100*rec:5.1f}%')
    print(f'    obligation F1             {100*f1:5.1f}%')
    print(f'    authority accuracy        '
          f'{100*auth_hit/auth_tot if auth_tot else 0:5.1f}%   ({auth_hit}/{auth_tot} matched pairs)')
    print(f'    gold dependency edges     {dep_fn}')
    print(f'    compiled dependency edges {dep_fp}')
    print(f'\n  matched {tp} of {tp+fn} gold obligations; '
          f'{fp} compiled obligations had no gold counterpart')


if __name__ == '__main__':
    main()
