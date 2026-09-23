"""A semantic parser that reads the graph instead of asking a model.

Contract, deliberately identical to `make_semantic_parser`:

    parse(query, chunks, section_id="") -> (NetworkSpec | None, ParseReport)

so it drops into the same call site and the same repair/fallback machinery.

Why this can work now and could not before
------------------------------------------
The IR needs four things a parser must decide: which material is in scope,
which sentences are obligations, how they depend on one another, and what
evidence each one points at. Every one of those is already in the graph:

  scope        TERM / SIGNCODE / FIGURE / TABLE / SECTION nodes give a query
               somewhere to land. Until the figure and table layer was built
               these were dangling edge targets, so a query naming
               "Figure 2C-5" or "R3-8" matched nothing and the LLM had to
               guess from raw text.
  obligations  SENTENCE nodes are already atomic and already carry an
               authority (STANDARD / GUIDANCE / OPTION / SUPPORT).
  structure    `pieces` types each sentence -- CONDITION, EXCEPTION, POINTER,
               LOOKUP, COMPUTED, DELEGATED_JUDGMENT, SUBSTITUTION ... -- and
               ITEM_OF / EXCEPTS / REFERS_TO wire them together.
  evidence     REFERS_TO edges to real FIGURE and TABLE nodes become
               evidence_hint entries the verifiers can resolve.

Nothing here calls a model.
"""
from __future__ import annotations

import math
import pickle
import re
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .compile import Obligation, MergeSpec, NetworkSpec, GuardSpec
from .network import ObligationType, MergeType
from .parser import ParseReport


def default_graph_path() -> Path:
    """Where the graph lives, in order of precedence:
    MUTCD_GRAPH in the environment, then data/mutcd/graph_cache.pkl beside the
    package, then graph_cache.pkl next to the repository."""
    env = os.environ.get('MUTCD_GRAPH')
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    root = here.parent.parent.parent                 # repo root
    for cand in (root / 'data' / 'mutcd' / 'graph_cache.pkl',
                 root / 'graph_cache.pkl',
                 root.parent / 'graph_cache.pkl'):
        if cand.exists():
            return cand
    return root / 'data' / 'mutcd' / 'graph_cache.pkl'

# ---- piece type -> obligation type ---------------------------------------
_PIECE_TO_TYPE = {
    'EXCEPTION':           ObligationType.EXCEPTION.value,
    'CONDITION':           ObligationType.APPLICABILITY.value,
    'SELECTOR':            ObligationType.CLASSIFICATION.value,
    'DEFINITION':          ObligationType.DEFINITIONAL.value,
    'POINTER':             ObligationType.CROSS_REFERENCE.value,
    'LOOKUP':              ObligationType.NUMERICAL.value,
    'COMPUTED':            ObligationType.NUMERICAL.value,
    'SITE_VARIABLE':       ObligationType.NUMERICAL.value,
    'ARRANGEMENT':         ObligationType.VISUAL.value,
    'SUBSTITUTION':        ObligationType.APPLICABILITY.value,
    'DELEGATED_JUDGMENT':  ObligationType.APPLICABILITY.value,
}
_NUMERIC = re.compile(r'\b\d+(?:\.\d+)?\s*(?:ft|feet|in|inch|inches|mph|mile|miles|'
                      r'seconds?|s|%|vph|pph|lb|lbs|tons?)\b', re.I)
_VISUAL = re.compile(r'\b(colou?r|symbol|arrow|legend|shape|border|retroreflectiv|'
                     r'background|panel|stripe|marking)\w*\b', re.I)
_QUANTITY_WORDS = {'size', 'height', 'width', 'length', 'spacing', 'distance',
                   'clearance', 'offset', 'volume', 'warrant', 'interval',
                   'dimension', 'colour', 'color', 'position', 'location',
                   'placement', 'mounting'}
_LEGEND_STOP = {'WORK', 'ROAD', 'LANE', 'ONLY', 'SIGN', 'SIGNS', 'AHEAD',
                'STATE LAW', 'END', 'BEGIN', 'EXIT'}
_STOP = {'the', 'a', 'an', 'of', 'for', 'on', 'in', 'at', 'to', 'is', 'are',
         'be', 'what', 'which', 'when', 'where', 'how', 'do', 'does', 'must',
         'shall', 'should', 'may', 'and', 'or', 'with', 'from', 'by', 'that',
         'this', 'it', 'as', 'can', 'if', 'used', 'use', 'sign', 'signs'}


def _stem(w: str) -> str:
    """Crude singular form. 'sizes'->'size', 'markings'->'marking'."""
    for suf in ('ies', 'es', 's'):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)] + ('y' if suf == 'ies' else '')
    return w


def _stem_set(text: str) -> set:
    return {_stem(w) for w in re.findall(r'[a-z]{4,}', text.lower())
            if w not in _STOP}


@dataclass
class Anchor:
    kind: str          # term | signcode | figure | table | section | quantity
    node: str
    matched: str
    weight: float = 1.0


class GraphParser:
    def __init__(self, graph_path: 'str | Path | None' = None):
        path = Path(graph_path) if graph_path else default_graph_path()
        if not path.exists():
            raise FileNotFoundError(
                f'graph not found at {path}. Build it with '
                f'`python -m mrag.vine.graph_enrich --pdf MUTCD.pdf '
                f'--in raw.pkl --out {path}`, or set MUTCD_GRAPH.')
        self.N, self.E, self.C = pickle.load(open(path, 'rb'))
        self.graph_path = path
        self.out: Dict[str, List] = defaultdict(list)
        self.inn: Dict[str, List] = defaultdict(list)
        for e in self.E:
            self.out[str(e.src)].append(e)
            self.inn[str(e.dst)].append(e)
        self.caption_words = {k: _stem_set(v.text) for k, v in self.N.items()
                              if v.kind in ('FIGURE', 'TABLE') and v.text}
        df: Counter = Counter()
        for ws in self.caption_words.values():
            df.update(ws)
        import math
        total = max(1, len(self.caption_words))
        self.idf = {w: math.log(total / (1 + c)) for w, c in df.items()}
        self.sec_title = {k.split(':', 1)[1]: v.text for k, v in self.N.items()
                          if v.kind == 'SECTION' and v.text}
        self.title_words = {s_: _stem_set(t) for s_, t in self.sec_title.items()}
        tdf: Counter = Counter()
        for ws in self.title_words.values():
            tdf.update(ws)
        ttot = max(1, len(self.title_words))
        self.tidf = {w: math.log(ttot / (1 + c)) for w, c in tdf.items()}
        self.by_section: Dict[str, List[str]] = defaultdict(list)
        for k, v in self.N.items():
            if v.kind == 'SENTENCE' and v.section:
                self.by_section[v.section].append(k)
        # lookup tables for anchoring
        self.terms = {v.text.lower(): k for k, v in self.N.items() if v.kind == 'TERM'}
        self.signcodes = {v.text.upper(): k for k, v in self.N.items() if v.kind == 'SIGNCODE'}
        self.figures = {k.split(':', 1)[1].lower(): k for k, v in self.N.items()
                        if v.kind in ('FIGURE', 'TABLE')}
        self.signnames = self._sign_names()
        self.chunk_of = {}
        for k, v in self.N.items():
            if v.kind == 'SENTENCE' and k.startswith('sent:'):
                self.chunk_of[k] = k[5:].split('#')[0]

    def _sign_names(self) -> Dict[str, str]:
        """Word legends people actually type, mapped to the sign code the
        manual uses. Harvested from sentences that name both."""
        pat = re.compile(r'\b([A-Z][A-Z \-]{2,28}[A-Z])\s*\(([A-Z]{1,3}\d{1,2}-\d{1,3}[a-zA-Z]?P?)\)')
        names: Dict[str, str] = {}
        for k, v in self.N.items():
            if v.kind not in ('SENTENCE', 'NOTE'):
                continue
            for m in pat.finditer(v.text):
                legend, code = m.group(1).strip(), m.group(2).upper()
                legend = re.sub(r'^(A|AN|THE)\s+', '', legend)
                if len(legend) < 4 or legend in _LEGEND_STOP:
                    continue
                if f'signcode:{code}' in self.N:
                    names.setdefault(legend, f'signcode:{code}')
        return names

    # ------------------------------------------------------------------ #
    # 1. anchor the query in the graph                                    #
    # ------------------------------------------------------------------ #
    def anchors(self, query: str) -> List[Anchor]:
        q = query.strip()
        found: List[Anchor] = []

        for m in re.finditer(r'\b(Figure|Table)\s+(\d+[A-Z]?-\d+[a-z]?)\b', q, re.I):
            word, ident = m.group(1).lower(), m.group(2).lower()
            cand = f"{word} {ident}"
            if cand in self.figures:
                found.append(Anchor('figure', self.figures[cand], m.group(0), 3.0))

        qw = _stem_set(q)
        if qw:
            for k, cw in self.caption_words.items():
                shared = qw & cw
                if not shared:
                    continue
                # rare words carry the signal; "road" and "sign" carry none
                wgt = sum(self.idf.get(w, 0.0) for w in shared)
                if wgt >= 6.0:
                    found.append(Anchor('caption', k, self.N[k].text[:44], wgt / 4))

        for m in re.finditer(r'\b([A-Z]{1,3}\d{1,2}-\d{1,3}[a-zA-Z]?P?)\b', q):
            code = m.group(1).upper()
            if code in self.signcodes:
                found.append(Anchor('signcode', self.signcodes[code], code, 3.0))

        for m in re.finditer(r'\b(\d[A-Z]\.\d{2})\b', q):
            key = f'section:{m.group(1)}'
            if key in self.N:
                found.append(Anchor('section', key, m.group(1), 4.0))

        for legend, node in self.signnames.items():
            if re.search(r'\b' + re.escape(legend) + r'\b', q, re.I):
                found.append(Anchor('signname', node, legend, 2.5))

        low = q.lower()
        for term, node in self.terms.items():
            if len(term) >= 5 and term in low:
                found.append(Anchor('term', node, term, 1.0 + len(term) / 40))

        for m in re.finditer(r'\b(speed|width|height|distance|spacing|length|'
                             r'volume|clearance|offset|taper)\b', low):
            found.append(Anchor('quantity', f'q:{m.group(1)}', m.group(1), 0.5))
        return found

    # ------------------------------------------------------------------ #
    # 2. pick the governing section                                       #
    # ------------------------------------------------------------------ #
    def score_sections(self, query: str, anchors: List[Anchor]
                       ) -> List[Tuple[str, float]]:
        """Additive scoring, measured best of the variants tried.

        Signals, strongest first: an explicit section id; a sign legend that
        appears in a heading; a heading whose rare words the query shares; the
        sections that cite an anchored figure, table, term or sign code; and a
        bag-of-words backstop. Section size corrects for sprawl and for stubs.
        """
        score: Counter = Counter()
        for a in anchors:
            if a.kind == 'section':
                score[a.node.split(':', 1)[1]] += a.weight * 4
                continue
            boost = (3.0 if a.kind in ('figure', 'signname', 'signcode')
                     else 1.1 if a.kind == 'caption' else 1.0)
            for e in self.inn.get(a.node, []):
                v = self.N.get(str(e.src))
                if v is not None and v.section:
                    score[v.section] += a.weight * boost

        qstem = _stem_set(query)
        legends = {a.matched.lower() for a in anchors if a.kind == 'signname'}
        for sec, tw in self.title_words.items():
            if not tw:
                continue
            shared = qstem & tw
            if shared:
                rare = sum(self.tidf.get(w, 0.0) for w in shared)
                score[sec] += 9.0 * rare * (0.35 + len(shared) / len(tw))
            tl = self.sec_title[sec].lower()
            for lg in legends:
                if lg in tl:
                    score[sec] += 40.0

        words = [w for w in re.findall(r'[a-z]{4,}', query.lower())
                 if w not in _STOP]
        if words:
            for sec, nodes in self.by_section.items():
                if sec in score:
                    continue
                hit = sum(1 for nid in nodes[:40] for w in words
                          if w in self.N[nid].text.lower())
                if hit:
                    score[sec] += hit * 0.15

        for sec in list(score):
            n = len(self.by_section.get(sec, []))
            if not n:
                continue
            if n > 12:
                score[sec] /= (1 + math.log10(n / 12))
            if n < 4:
                score[sec] *= n / 4.0

        CONTEXT = {'6': ('work zone', 'temporary', 'construction', 'flagger',
                         'taper', 'detour', 'incident'),
                   '7': ('school', 'student', 'children'),
                   '8': ('railroad', 'rail', 'grade crossing', 'train', 'lrt',
                         'light rail', 'transit'),
                   '9': ('bicycle', 'bike', 'cyclist', 'shared-use', 'path')}
        low = query.lower()
        for sec in list(score):
            w = CONTEXT.get(sec[0])
            if w and not any(x in low for x in w):
                score[sec] *= 0.35
        return score.most_common(6)

    # ------------------------------------------------------------------ #
    # 3. build the spec from the graph                                    #
    # ------------------------------------------------------------------ #
    def _evidence(self, node_id: str) -> List[Dict[str, str]]:
        hints = []
        for e in self.out.get(node_id, []):
            d = str(e.dst)
            if d.startswith('figure:'):
                body = d.split(':', 1)[1]
                kind = 'table' if body.startswith('Table') else 'figure'
                hints.append({'type': kind, 'id': body})
            elif d.startswith('section:'):
                hints.append({'type': 'section', 'id': d.split(':', 1)[1]})
        # de-duplicate, keep order
        seen, out = set(), []
        for h in hints:
            k = (h['type'], h['id'])
            if k not in seen:
                seen.add(k)
                out.append(h)
        return out[:4]

    def _type_of(self, v) -> str:
        for p in v.pieces:
            if p in _PIECE_TO_TYPE:
                return _PIECE_TO_TYPE[p]
        if v.quantities or _NUMERIC.search(v.text):
            return ObligationType.NUMERICAL.value
        if _VISUAL.search(v.text):
            return ObligationType.VISUAL.value
        return ObligationType.APPLICABILITY.value

    def build(self, query: str, section_id: str,
              report: ParseReport) -> Optional[NetworkSpec]:
        nodes = sorted(self.by_section.get(section_id, []),
                       key=lambda k: (self.N[k].ordinal or 0, k))
        if len(nodes) > 150:
            report.notes.append(
                f'section {section_id} has {len(nodes)} sentences; it is a '
                f'collection, not a rule set -- not compiled')
            return None
        if not nodes:
            report.notes.append(f'section {section_id} has no sentence nodes')
            return None

        obligations: List[Obligation] = []
        idmap: Dict[str, str] = {}
        n = 0
        for nid in nodes:
            v = self.N[nid]
            auth = re.sub(r'\s*\(.*?\)', '', (v.authority or 'STANDARD')).strip().upper()
            if auth not in ('STANDARD', 'GUIDANCE', 'OPTION', 'SUPPORT'):
                report.notes.append(f'unknown authority {v.authority!r} on {nid}; skipped')
                continue
            if auth == 'SUPPORT':
                continue                       # support is never an obligation
            if len(v.text.strip()) < 12:
                continue                       # "Notes 1." and similar stubs
            n += 1
            oid = f'g{n}'
            idmap[nid] = oid
            obligations.append(Obligation(
                id=oid, claim=v.text.strip(), type=self._type_of(v),
                authority=auth, evidence_hint=self._evidence(nid),
                source_chunk=self.chunk_of.get(nid, '')))
        if not obligations:
            report.notes.append(f'section {section_id} yielded no obligations')
            return None

        # dependencies the manual states in structure, not prose
        by_id = {o.id: o for o in obligations}
        for nid, oid in idmap.items():
            for e in self.out.get(nid, []):
                dst = str(e.dst)
                if e.rel == 'ITEM_OF':
                    lead = dst.replace('lead:', 'sent:') + '#0'
                    if lead in idmap and idmap[lead] != oid:
                        by_id[oid].requires.append(idmap[lead])
                elif e.rel == 'EXCEPTS' and dst in idmap:
                    by_id[oid].type = ObligationType.EXCEPTION.value

        exceptions = [o.id for o in obligations
                      if o.type == ObligationType.EXCEPTION.value]
        base = [o.id for o in obligations
                if o.id not in exceptions and o.authority in ('STANDARD', 'GUIDANCE')]
        if not base:                            # every Standard read as an exception
            base = [o.id for o in obligations if o.authority == 'STANDARD']
            exceptions = [e for e in exceptions if e not in base]

        merges: List[MergeSpec] = []
        terminal: str
        if len(base) >= 2:
            merges.append(MergeSpec(id='m_base', claim='all required checks hold',
                                    kind=MergeType.CONJUNCTION.value, inputs=base))
            terminal = 'm_base'
        elif base:
            terminal = base[0]
        else:
            terminal = obligations[0].id

        if exceptions:
            merges.append(MergeSpec(
                id='m_exc', claim='the rule holds unless an exception applies',
                kind=MergeType.EXCEPTION.value, inputs=[terminal] + exceptions))
            terminal = 'm_exc'

        spec = NetworkSpec(query=query, terminal=terminal, obligations=obligations,
                           merges=merges, source='graph_parser')
        return spec

    # ------------------------------------------------------------------ #
    # 4. the drop-in entry point                                          #
    # ------------------------------------------------------------------ #
    def parse(self, query: str, chunks: Sequence[Dict[str, Any]] = (),
              section_id: str = '') -> Tuple[Optional[NetworkSpec], ParseReport]:
        report = ParseReport()
        report.attempts = 1
        anchors = self.anchors(query)
        report.notes.append('anchors: ' + (', '.join(
            f'{a.kind}:{a.matched}' for a in anchors) or 'none'))

        candidates = [(section_id, 99.0)] if section_id else []
        candidates += [c for c in self.score_sections(query, anchors)
                       if c[0] != section_id]
        if not candidates:
            report.source = 'failed'
            report.notes.append('the query did not anchor anywhere in the graph')
            return None, report
        report.notes.append('sections: ' + ', '.join(
            f'{s}({sc:.1f})' for s, sc in candidates[:4]))

        for sec, _ in candidates[:4]:
            spec = self.build(query, sec, report)
            if spec is None:
                continue
            problems = spec.problems()
            if problems:
                report.problems.append(problems)
                report.notes.append(f'section {sec} rejected: {problems[:2]}')
                continue
            report.source = 'graph_parser'
            report.notes.append(f'compiled from section {sec}')
            return spec, report

        report.source = 'failed'
        return None, report


def make_graph_parser(graph_path: 'str | Path | None' = None):
    """Same signature shape as make_semantic_parser, minus the `ask` callable."""
    gp = GraphParser(graph_path)
    return gp.parse


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='parse a query against the graph')
    ap.add_argument('query', nargs='*', help='question to parse')
    ap.add_argument('--graph', type=Path, default=None)
    args = ap.parse_args()
    parse = make_graph_parser(args.graph)
    if args.query:
        spec, rep = parse(' '.join(args.query))
        for n in rep.notes:
            print('   ', n[:160])
        if spec:
            print(spec.to_json()[:2000])
        raise SystemExit(0)
    queries = [
        'What size must a STOP sign be on a conventional road?',
        'When is a Speed Limit sign required to be retroreflective?',
        'taper length for a merging taper in a work zone',
        'crosswalk markings at a roundabout',
        'What does Figure 2C-5 require for horizontal alignment signs?',
        'R3-8 lane control sign placement',
    ]
    for q in queries:
        spec, rep = parse(q)
        print('=' * 78)
        print('Q:', q)
        for nte in rep.notes[:3]:
            print('   ', nte[:150])
        if spec is None:
            print('    -> no spec')
            continue
        print(f'    -> {len(spec.obligations)} obligations, {len(spec.merges)} merges, '
              f'terminal={spec.terminal}, source={spec.source}')
        for o in spec.obligations[:3]:
            print(f'       [{o.authority}/{o.type}] {o.claim[:88]}')
            if o.evidence_hint:
                print(f'          evidence: {o.evidence_hint}')
