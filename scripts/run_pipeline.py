"""Run every sample question through the whole chain, then score.

LEAKAGE GUARD -- the point of the file layout
  run_input.json  holds ONLY the question text. It is the pipeline's input.
  run_gold.json   holds the governing sections. It is opened AFTER every
                  question has been processed, and is used for nothing but
                  printing right or wrong.

Nothing in `process()` can see a gold answer: it is not passed in, and the gold
file is not read until `score()` runs. Earlier in this project a benchmark was
tuned against its own answer key four times without anyone noticing, so the two
are kept in separate files on purpose rather than separate variables.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, '/home/claude/work/Beyond_RAG-main')
from mrag.vine.graph_parser import GraphParser, _stem_set  # noqa: E402


def process(gp, question):
    """Everything the pipeline does, with no knowledge of the answer."""
    facts = gp.facts(question)
    ranked, _rep = gp.parse_ranked(question, k=5)
    qw = _stem_set(question)

    # Only conditions inside a section the router chose. The router is now right
    # 10/10 in its top five, so this is a strong filter rather than a guess --
    # and without it a question with six facts produced 113 arithmetic matches
    # with the right one buried.
    top_sections = {c.section for c in ranked}
    scored = []
    for nid, sec, why in gp.satisfied(facts):
        if sec not in top_sections:
            continue
        text = gp.N[nid].text or ''
        m = re.search(r'satisfies "\S+ ([\d,\.]+)"', why)
        i = text.find(m.group(1).split('.')[0]) if m else -1
        # the words the manual uses just before the value: what is being measured
        phrase = _stem_set(text[max(0, i - 70):i] if i >= 0 else '')
        shared = qw & phrase
        # rare shared words carry the signal; "paved" and "lane" carry little
        strength = sum(gp.idf.get(w, 0.0) for w in shared)
        scored.append((strength, sec, why, sorted(shared, key=lambda w: -gp.idf.get(w, 0))[:3]))
    scored.sort(reverse=True)
    return {'facts': [(f.kind, f.value, f.unit) for f in facts],
            'sections': [c.section for c in ranked],
            'conditions': scored}


def score():
    gp = GraphParser()
    questions = json.load(open('/home/claude/run_input.json'))
    out = {sid: process(gp, q) for sid, q in questions.items()}

    gold = json.load(open('/home/claude/run_gold.json'))   # opened only now
    sec_top1 = sec_top5 = cond_top1 = cond_top3 = cond_any = 0
    n = len(questions)
    print(f'{"id":11s} {"facts":>6s}  {"sections found":>26s}  {"gold condition rank":>21s}')
    for sid, r in out.items():
        g = gold[sid]
        in5 = [s for s in r['sections'] if s in g]
        sec_top1 += bool(r['sections']) and r['sections'][0] in g
        sec_top5 += bool(in5)
        ranks = [i for i, c in enumerate(r['conditions'], 1) if c[1] in g]
        cond_top1 += bool(ranks) and ranks[0] == 1
        cond_top3 += bool(ranks) and ranks[0] <= 3
        cond_any += bool(ranks)
        rk = str(ranks[0]) if ranks else '-'
        print(f'{sid:11s} {len(r["facts"]):>6d}  {str(in5) or "none":>26s}  '
              f'{rk:>8s} of {len(r["conditions"]):<4d}')
    print()
    print(f'  gold section ranked 1st        {sec_top1}/{n}')
    print(f'  gold section in the top 5      {sec_top5}/{n}')
    print(f'  gold condition ranked 1st      {cond_top1}/{n}')
    print(f'  gold condition in the top 3    {cond_top3}/{n}')
    print(f'  gold condition found at all    {cond_any}/{n}')
    json.dump({k: {'facts': v['facts'], 'sections': v['sections'],
                   'conditions': [(round(s, 1), sec, why) for s, sec, why, _ in v['conditions'][:8]]}
               for k, v in out.items()},
              open('/home/claude/run_output.json', 'w'), indent=1)


if __name__ == '__main__':
    score()
