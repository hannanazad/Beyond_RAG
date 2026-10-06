"""Pick provisions at random from the MUTCD chunks for the retrieval dev set.

Rules, fixed before any retrieval was run:
  - normative paragraphs only (Standard / Guidance / Option), source=paragraph
  - 100-450 characters, so one provision is one idea
  - one provision per section
  - Chapter 6P (Typical Application notes) and appendices left out
  - a quota per Part, fixed seed
  - optional --exclude FILE: section ids to leave out (one per line). Used to
    keep the development set away from the sections the held-out test
    questions use. That file is kept with the test material, NOT in the repo.

Usage:
  python sample_provisions.py chunks.jsonl [--exclude FILE] > sampled.jsonl
"""
import argparse
import json
import random

SEED = 20261006
QUOTA = {'1': 3, '2': 14, '3': 6, '4': 9, '5': 2, '6': 7, '7': 2, '8': 3, '9': 2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chunks')
    ap.add_argument('--exclude', default=None)
    a = ap.parse_args()
    excluded = set()
    if a.exclude:
        excluded = {l.strip() for l in open(a.exclude) if l.strip()}

    pool = {}
    for line in open(a.chunks):
        r = json.loads(line)
        sec = r.get('section_id') or ''
        if (r.get('source') != 'paragraph'
                or r.get('content_type') not in ('Standard', 'Guidance', 'Option')
                or not (100 <= len(r.get('text', '')) <= 450)
                or sec.startswith('6P') or not sec[:1].isdigit() or sec in excluded):
            continue
        pool.setdefault(sec[0], {}).setdefault(sec, []).append(r)

    rng = random.Random(SEED)
    n = 0
    for part, k in QUOTA.items():
        for sec in rng.sample(sorted(pool.get(part, {})), k):
            r = rng.choice(sorted(pool[part][sec], key=lambda x: x['chunk_id']))
            n += 1
            print(json.dumps({'n': n, 'chunk_id': r['chunk_id'], 'section_id': r['section_id'],
                              'section_title': r['section_title'],
                              'content_type': r['content_type'], 'text': r['text']}))


if __name__ == '__main__':
    main()
