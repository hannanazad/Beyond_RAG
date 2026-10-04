"""Score section routing on every set we have, with the metrics the pipeline needs.

WHY THESE METRICS

The parser's output is not an answer, it is the set of sections the obligations
get compiled from. A question whose terminal logic spans two sections needs both
of them. If only one is found, the compiler does not return Unknown for the
missing half -- it never learns the missing half exists, builds a small clean
network from what it has, and certifies it. That is `obligation omission` in the
paper's taxonomy, and it is the failure mode that produces a confident wrong
answer rather than an abstention.

So the headline is COMPLETE COVERAGE: every governing section found, in the
top k. `recall` says how close it got when it failed. `top1` is kept only as a
diagnostic on ranking quality.

SETS
  smoke  the 20 hand-written queries in eval_graph_parser.py. Short, leaky,
         tuned against. Use to catch breakage, never as a score.
  dev    the 30-item development split of MUTCD-150. The only set it is
         legitimate to fit anything on.
  test   the 120-item test split. DO NOT RUN while tuning.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine.graph_parser import GraphParser  # noqa: E402

GOLD_PATH = Path(__file__).resolve().parent / 'gold' / 'mutcd_benchmark_gold_v1_1_msdi.jsonl'


def load_mutcd150(split: str):
    rows = [json.loads(l) for l in GOLD_PATH.read_text().splitlines() if l.strip()]
    out = []
    for r in rows:
        if r.get('split') != split:
            continue
        secs = [s for s in (r.get('sections') or []) if s and '-' not in s]
        if not secs:
            continue
        out.append((r['question'], secs))
    return out


def load_smoke():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from eval_graph_parser import GOLD
    return [(q, list(g)) for q, g in GOLD]


def score(gp: GraphParser, items, k: int):
    complete = top1 = 0
    recall_sum = 0.0
    extras = 0
    rows = []
    for q, gold in items:
        ranked, _ = gp.parse_ranked(q, k=k)
        got = [c.section for c in ranked]
        found = [s for s in gold if s in got]
        is_complete = len(found) == len(gold)
        complete += is_complete
        top1 += bool(got) and got[0] in gold
        recall_sum += len(found) / len(gold)
        extras += len([s for s in got if s not in gold])
        rows.append((is_complete, q, got, gold, found))
    n = max(1, len(items))
    return {
        'n': len(items),
        'complete': complete,
        'complete_pct': 100.0 * complete / n,
        'recall_pct': 100.0 * recall_sum / n,
        'top1': top1,
        'top1_pct': 100.0 * top1 / n,
        'extras_per_q': extras / n,
    }, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--graph', type=Path, default=None)
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--sets', default='smoke,dev',
                    help="comma-separated: smoke, dev, test. 'test' is held out -- "
                         "do not run it while tuning.")
    ap.add_argument('--show', action='store_true', help='print every question')
    a = ap.parse_args()

    gp = GraphParser(a.graph)
    loaders = {'smoke': load_smoke,
               'dev': lambda: load_mutcd150('development'),
               'test': lambda: load_mutcd150('test')}

    print(f"  k = {a.k}\n")
    print(f"  {'set':6s} {'n':>4s}  {'complete':>13s}  {'recall':>8s}  {'top1':>12s}  {'extra/q':>8s}")
    for name in [s.strip() for s in a.sets.split(',') if s.strip()]:
        if name == 'test':
            print("\n  *** running the HELD-OUT test split ***\n")
        s, rows = score(gp, loaders[name](), a.k)
        print(f"  {name:6s} {s['n']:>4d}  {s['complete']:>5d} ({s['complete_pct']:>5.1f}%)  "
              f"{s['recall_pct']:>7.1f}%  {s['top1']:>4d} ({s['top1_pct']:>5.1f}%)  {s['extras_per_q']:>8.1f}")
        if a.show:
            for ok, q, got, gold, found in rows:
                print(f"      [{'OK  ' if ok else 'MISS'}] {q[:54]:56s} got {got} want {gold}")


if __name__ == '__main__':
    main()
