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
from .semantics import QUANTITY_HEADS
from .graph_links import canonical_speed


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



# The manual's own list of things it measures, reused on the question side so
# both halves are read with one vocabulary. Longest first, so "mounting height"
# wins over "height" and "sight distance" over "distance".
_QUANTITY_HEADS_LONGEST_FIRST = sorted(QUANTITY_HEADS, key=len, reverse=True)

# head phrase -> the kind name `semantics.py` stamps on an extracted value.
_HEAD_TO_KIND = {h: h.upper().replace(' ', '_').replace('-', '_')
                 for h in QUANTITY_HEADS}


# A sign size is written as a pair -- "24 x 24 inches" -- and the first number
# carries no unit of its own, so a plain number-plus-unit scan sees only the
# second one and loses the dimension. Table 2B-1's own note says these are
# "width x height", so the pair is one fact, not two.
_FACT_DIM = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:x|×|by)\s*(\d+(?:\.\d+)?)\s*(inches|inch|in\.|feet|foot|ft\.?)\b',
    re.I)

# A number with a unit, as a question states it.
_FACT_NUM = re.compile(
    r'(\d+(?:\.\d+)?)\s*(mph|feet|foot|ft\.?|inches|inch|in\.|miles|seconds|percent|lanes?)\b',
    re.I)
_FACT_UNIT = {'foot': 'feet', 'ft': 'feet', 'ft.': 'feet',
              'inch': 'inches', 'in.': 'inches', 'lane': 'lanes'}

# HOW A QUESTION SAYS WHAT THE MANUAL SAYS DIFFERENTLY
#
# The manual writes "a mounting height of 7 feet". A person writes "its bottom
# is 7 feet above the sidewalk". Same fact, and the manual's own extractor --
# which looks backward for a named head like "mounting height" -- finds nothing
# in the second one. Measured on the sample question: five numbers stated, one
# typed.
#
# So these are question-side paraphrases, each mapping to a kind the manual
# ALREADY draws. Same rule as the speed vocabulary in graph_links: add a phrase
# when a question is found to state something the manual states differently;
# never add one that invents a distinction the manual itself does not make.
#
# (patterns are matched against the text just before, and just after, the number)
_FACT_BEFORE = [
    (r'\bbottom\s+(?:is|at|sits)?\s*$',            'MOUNTING_HEIGHT'),
    (r'\bmounted\s+(?:at\s+)?$',                   'MOUNTING_HEIGHT'),
    (r'\bmounting height\s+(?:of\s+)?$',           'MOUNTING_HEIGHT'),
    (r'\bheight\s+(?:of\s+)?$',                    'HEIGHT'),
    (r'\b(?:measur\w+|panel|sign)\s+(?:of\s+)?$',  'SIZE'),
    (r'\bsize\s+(?:of\s+)?$',                      'SIZE'),
    (r'\bwidth\s+(?:of\s+)?$',                     'WIDTH'),
    (r'\bprojects?\s+$',                           'PROJECTION'),
    (r'\bprojecting\s+$',                          'PROJECTION'),
    (r'\bclearance\s+(?:of\s+)?$',                 'CLEARANCE'),
    (r'\b(?:offset|set back|setback)\s+(?:by\s+)?$', 'OFFSET'),
]
_FACT_AFTER = [
    (r'^\s*(?:x|×)\s*\d',                          'SIZE'),      # "24 x 24 inches"
    (r'^\s*-?\s*high\b',                           'HEIGHT'),    # "12-inch-high"
    (r'^\s*-?\s*wide\b',                           'WIDTH'),
    (r'^\s*above\b',                               'MOUNTING_HEIGHT'),
    (r'^\s*into the (?:walkway|sidewalk)',         'PROJECTION'),
]


import operator as _op

# The comparison a condition's operator means. "?" and "example" are not
# comparisons and are deliberately absent -- an untestable condition must not
# be reported as satisfied.
_CMP = {'<=': _op.le, '<': _op.lt, '>=': _op.ge, '>': _op.gt,
        '==': _op.eq, '=': _op.eq}

_UNIT_SAME = [{'feet', 'foot', 'ft'}, {'inches', 'inch', 'in'},
              {'mph'}, {'seconds', 'sec', 's'}, {'lanes', 'lane'},
              {'miles', 'mile'}, {'percent', '%'}]


def _units_comparable(a: Optional[str], b: Optional[str]) -> bool:
    """Only compare like with like. 7 feet does not satisfy a 7-inch limit."""
    if not a or not b:
        return False
    a, b = a.lower().rstrip('.'), b.lower().rstrip('.')
    if a == b:
        return True
    return any(a in grp and b in grp for grp in _UNIT_SAME)


# THE SUBJECT SLOT
#
# Zhang & El-Gohary's four-tuple for a regulatory requirement is
#   <Subject, Attribute, Comparison, Quantity>
# plus Subject Restriction. We already had the last three: Attribute is the
# quantity kind, Comparison is the operator, Quantity is the value and unit.
# Subject was missing, and its absence has a specific, measured cost -- a
# condition matcher with no Subject fired "The Bicycle Signal sign shall have a
# minimum size of 24 inches" on a question about a regulatory turn-prohibition
# sign. The arithmetic was right and the answer was wrong.
#
# The MUTCD gives the subject of a sign away in its own code. The series letter
# is the device family, and it is the same scheme the manual organises its
# chapters by, so it needs no list to maintain.
_SIGN_SERIES = {
    'R': 'regulatory sign', 'W': 'warning sign', 'M': 'route sign',
    'D': 'guide sign', 'I': 'general service sign', 'E': 'expressway guide sign',
    'G': 'general information sign', 'OM': 'object marker',
    'EM': 'emergency management sign',
}

# Section headings are written ATTRIBUTE of SUBJECT -- "Size of Regulatory
# Signs", "Mounting Height of Signs". 170 of 953 split this way, and the split
# is exactly the focus/subject distinction the scorer has been summing together
# and losing: "size" is what is asked, "regulatory signs" is what it is asked
# about.
_TITLE_SPLIT = re.compile(r'\s+of\s+', re.I)

# A heading naming one of these is naming a device, so the heading is a subject.
# A heading with none of them -- "Mounting Height", "Dimensions" -- is naming an
# attribute and governs every device.
_DEVICE_NOUN = re.compile(
    r'\b(signs?|signals?|markings?|plaques?|devices?|markers?|beacons?|'
    r'barricades?|cones?|islands?|crossings?|gates?|lights?|arrows?|'
    r'assemblys?|assemblies|lines?|crosswalks?|legends?|symbols?)\b', re.I)


@dataclass
class Fact:
    """A measured value a question states, typed the way the manual types it."""
    kind: str
    value: float
    unit: str
    said: str = ''


@dataclass
class Candidate:
    """One section that compiled, kept so the certificate can name what else
    was in the running and on what score it lost."""
    section: str
    score: float
    spec: NetworkSpec
    title: str = ''
    obligations: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {'section': self.section, 'title': self.title,
                'score': round(self.score, 2), 'obligations': self.obligations}


class GraphParser:
    # Weight of the cross-reference term in score_sections. Swept on the
    # 20-query gold set; see the comment at its use. Exposed as a class
    # attribute so it can be re-fitted, or set to 0.0 to ablate it, without
    # editing the scorer.
    W_CROSSREF: float = 1.0

    # Caption anchoring. See the comment at their use in `anchors`.
    # CAPTION_FLOOR          minimum shared rarity before a caption is considered
    # CAPTION_COVERAGE_POW   how hard to favour captions that match a large share
    #                        of themselves; 0.0 reproduces the old sum-only rule
    # CAPTION_MAX            how many captions may survive, whatever the query length
    # Weight of the "what is this question about" anchor, scaled by how
    # specific the matched quantity kind is. 0.0 ablates it.
    # Weight of the section-heading word-overlap term. This was 9.0 and was
    # the dominant term by an order of magnitude: on a scenario question a
    # section scored 198 on its title while the section the manual itself
    # names for the sign in question scored 40. Every structural signal --
    # cross-references, the table's Section column, what the question asks
    # about -- was being outvoted by spelling.
    # Weight per section whose stated conditions the question's facts satisfy.
    # 0.0 ablates it.
    # How much a section's score survives when its stated subject cannot be
    # the question's subject. 1.0 ablates the Subject slot entirely.
    W_SUBJECT: float = 0.25

    W_SATISFIED: float = 0.0

    W_HEADING: float = 9.0

    W_ASKS_ABOUT: float = 1.0

    CAPTION_FLOOR: float = 6.0
    CAPTION_COVERAGE_POW: float = 0.5
    CAPTION_MAX: int = 8

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
        # Keyed on the node id, not on `text`. The id is what the node is
        # named by and cannot drift; `text` is a content field, and keying on
        # it meant one enrichment step writing a legend there silently made
        # every affected code unfindable.
        self.signcodes = {k.split(':', 1)[1].upper(): k
                          for k, v in self.N.items() if v.kind == 'SIGNCODE'}
        self.figures = {k.split(':', 1)[1].lower(): k for k, v in self.N.items()
                        if v.kind in ('FIGURE', 'TABLE')}
        self.signnames = self._sign_names()
        self.chunk_of = {}
        for k, v in self.N.items():
            if v.kind == 'SENTENCE' and k.startswith('sent:'):
                self.chunk_of[k] = k[5:].split('#')[0]
        # The manual's own index: for every node the manual names out loud,
        # which sections name it and how often. 6,519 REFERS_TO edges, unused
        # for routing until now.
        self._subj_cache: Dict[str, set] = {}
        self.cited_by: Dict[str, Counter] = defaultdict(Counter)
        for e in self.E:
            if e.rel != 'REFERS_TO':
                continue
            v = self.N.get(str(e.src))
            if v is not None and v.section:
                self.cited_by[str(e.dst)][v.section] += 1

    def _sign_names(self) -> Dict[str, str]:
        """Word legends people actually type, mapped to the sign code the
        manual uses. Harvested from sentences that name both, and from the
        sign-size tables, which name a legend for codes the body text never
        mentions at all (Busway Crossing, Shared-Use Path Destination, ...)."""
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
        # The table legends are printed in title case, not the small caps the
        # pattern above needs, so they are read from the node instead. They
        # are kept in a SEPARATE map: a table's "Sign or Plaque" column holds
        # a descriptive name, not the legend printed on the sign, and some of
        # those names are ordinary phrases. Harvesting "Work Zone" (G20-5aP)
        # into the same map as a real legend sent the heading bonus to 6G.08
        # "Work Zone and Higher Fines Signs" and pushed 6B.08 "Tapers" off the
        # top for a taper query. These match, but never win a heading.
        self.sign_labels: Dict[str, str] = {}
        for k, v in self.N.items():
            if v.kind != 'SIGNCODE':
                continue
            for piece in (v.pieces or []):
                if not piece.startswith('name='):
                    continue
                legend = re.sub(r'\s*\(plaque\)\s*$', '', piece[5:]).strip()
                legend = re.sub(r'^(A|AN|THE)\s+', '', legend, flags=re.I)
                if len(legend) < 4 or legend.upper() in _LEGEND_STOP:
                    continue
                if legend.upper() in names:
                    continue
                self.sign_labels.setdefault(legend.upper(), k)
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
            # WHY THIS IS NOT A PLAIN THRESHOLD ANY MORE
            #
            # It used to be: add up the rarity of the words a caption shares
            # with the query, and keep the caption if the total reached 6.0.
            # A sum has no notion of how long the query is, so the test got
            # looser the more the user typed. A four-word query only cleared
            # 6.0 on a genuinely rare word; a 150-word scenario cleared it by
            # piling up ordinary ones -- road, sign, inches, curb, sidewalk --
            # until almost any caption qualified.
            #
            # Measured on a real scenario question: 71 anchors fired, 65 of
            # them captions, and the one anchor that mattered (signcode R3-2)
            # was 1 in 71 and was outvoted. The same question in 14 words
            # produced 21 anchors and routed correctly.
            #
            # So the test is now about match QUALITY, not accumulated weight.
            # `coverage` is how much of the caption's own vocabulary was hit,
            # which a long query cannot inflate -- piling on more query words
            # does not make a caption match itself any better. And only the
            # best CAPTION_MAX captions survive, which bounds the flood no
            # matter how long the query is.
            cands = []
            for k, cw in self.caption_words.items():
                shared = qw & cw
                if not shared:
                    continue
                wgt = sum(self.idf.get(w, 0.0) for w in shared)
                if wgt < self.CAPTION_FLOOR:
                    continue
                coverage = len(shared) / max(1, len(cw))
                cands.append((wgt * (coverage ** self.CAPTION_COVERAGE_POW), wgt, k))
            cands.sort(reverse=True)
            for _, wgt, k in cands[:self.CAPTION_MAX]:
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

        # Table-column names. Weaker than a real legend and, being ordinary
        # English in places, deliberately barred from the heading bonus.
        for legend, node in self.sign_labels.items():
            if re.search(r'\b' + re.escape(legend) + r'\b', q, re.I):
                found.append(Anchor('signlabel', node, legend, 1.5))

        low = q.lower()
        for term, node in self.terms.items():
            if len(term) >= 5 and term in low:
                found.append(Anchor('term', node, term, 1.0 + len(term) / 40))

        # WHAT THE QUESTION IS ASKING ABOUT
        #
        # Everything above matches the question by spelling. This matches it by
        # the same vocabulary the manual was read with: `semantics.QUANTITY_HEADS`
        # is the list of things the MUTCD measures, and every sentence that
        # states a value now carries its kind and a MEASURES edge. So asking
        # "what is this question about" becomes a graph lookup rather than a
        # word count.
        #
        # This is the only anchor that says what the question WANTS rather than
        # what it MENTIONS. In a scenario question the difference is the whole
        # problem: "a No Left Turn sign ... evaluate its mounting height" names
        # a left turn and asks about a height, and only this anchor can tell
        # those two roles apart.
        # Longest head wins and shorter ones inside it are suppressed:
        # "mounting height" must not also fire "height". The manual separates
        # those two and so must the question -- 27 sentences measure a mounting
        # height, 66 measure some height, and treating them as the same thing
        # throws away the distinction the reading was done to capture.
        #
        # Weight is by specificity, for the same reason rare words beat common
        # ones everywhere else here: a kind measured by six sentences points
        # somewhere, a kind measured by two hundred points nowhere.
        low = ' ' + q.lower() + ' '
        claimed: List[Tuple[int, int]] = []
        for head in _QUANTITY_HEADS_LONGEST_FIRST:
            kind = _HEAD_TO_KIND.get(head)
            key = f'quantity:{kind}' if kind else None
            if not key or key not in self.N:
                continue
            for m in re.finditer(r'\b' + re.escape(head) + r's?\b', low):
                if any(a <= m.start() and m.end() <= b for a, b in claimed):
                    continue          # inside a longer head already matched
                claimed.append((m.start(), m.end()))
                n_meas = len(self.inn.get(key, []))
                if not n_meas:
                    continue
                spec = math.log(len(self.by_section) / n_meas)
                if spec > 0:
                    found.append(Anchor('asks_about', key, head,
                                        self.W_ASKS_ABOUT * spec))
                break

        for m in re.finditer(r'\b(speed|width|height|distance|spacing|length|'
                             r'volume|clearance|offset|taper)\b', low):
            found.append(Anchor('quantity', f'q:{m.group(1)}', m.group(1), 0.5))
        return found

    # ------------------------------------------------------------------ #
    # 2. pick the governing section                                       #
    # ------------------------------------------------------------------ #
    def score_sections(self, query: str, anchors: List[Anchor],
                       top: int = 6) -> List[Tuple[str, float]]:
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
                     else 2.0 if a.kind == 'signlabel'
                     else 1.1 if a.kind == 'caption' else 1.0)
            # The node may name its own governing section. A SIGNCODE built
            # from a sign-size table carries the Section column the manual
            # printed beside it -- the manual saying where that sign is
            # defined. That is a stronger signal than "some section cites
            # this node", and for a code the body text never mentions it is
            # the only signal there is: nothing points into such a node, so
            # the loop below would score nothing at all.
            own = self.N.get(a.node)
            if own is not None and own.section and own.section in self.by_section:
                score[own.section] += a.weight * boost * 2.0
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
                score[sec] += self.W_HEADING * rare * (0.35 + len(shared) / len(tw))
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
        # ---- conditions the question's facts actually satisfy ---------------
        # Evidence, not coincidence. A section earns points here because a
        # provision it contains demonstrably applies to the situation stated,
        # checked numerically with units. Scored per satisfied condition and
        # damped, so a section holding many thresholds cannot win by volume.
        if self.W_SATISFIED:
            # A satisfied condition only counts if the provision is about the
            # same kind of device. "The Bicycle Signal sign shall have a minimum
            # size of 24 inches" is satisfied by a 24-inch panel and is not
            # about a regulatory turn-prohibition sign. Without this gate the
            # arithmetic is right and the answer is wrong -- which is the exact
            # failure the certificate exists to prevent.
            #
            # The subject comes from the question's own anchors: the chapter of
            # a sign code it names, or of a section/figure it names. If the
            # question names no subject, no gate is applied and every satisfied
            # condition counts.
            subject_chapters = set()
            for a in anchors:
                if a.kind not in ('signcode', 'signname', 'section', 'figure'):
                    continue
                n = self.N.get(a.node)
                sec = (n.section if n is not None else '') or ''
                if sec:
                    subject_chapters.add(sec.split('.')[0])
            per_sec: Counter = Counter()
            for _nid, sec, _why in self.satisfied(self.facts(query)):
                if not sec:
                    continue
                if subject_chapters and sec.split('.')[0] not in subject_chapters:
                    continue
                per_sec[sec] += 1
            for sec, n in per_sec.items():
                if sec in self.by_section:
                    score[sec] += self.W_SATISFIED * (1.0 + math.log(n))

        # ---- the manual's own cross-references -----------------------------
        # A section that names Table 2B-1 eight times is telling you it is
        # about regulatory sign sizes. This is applied AFTER the size and
        # context corrections, deliberately: it is a statement about topic,
        # not about how much text a section happens to contain, so shrinking
        # it for sprawl would be reading it as the wrong kind of evidence.
        #
        # Rarity matters more than count here. Figure 6B-2 is named by dozens
        # of sections and separates nothing; Table 2B-1 is named by four and
        # separates everything. So each reference is weighted by how few
        # sections make it, and the count is damped by a log so one section
        # citing a figure twenty times cannot swamp the field.
        #
        # THE WEIGHT IS NOT PRINCIPLED. Swept on the 20-query gold set:
        #   0.0 -> 12 best / 13 acceptable   (the term off)
        #   1.0 -> 14 best / 15 acceptable   <- shipped
        #   2.0 -> 14 best / 14 acceptable
        #   4.0 -> 13 best / 13 acceptable
        #   8.0 -> 10 best / 11 acceptable
        # Twenty queries cannot separate 1.0 from 2.0 honestly; the gap is one
        # question. Set W_CROSSREF = 0.0 to ablate. Re-fit on a real dev set
        # before quoting the number anywhere.
        n_sections = max(1, len(self.by_section))
        for a in anchors:
            if a.kind not in ('figure', 'caption', 'table'):
                continue
            citers = self.cited_by.get(a.node)
            if not citers:
                continue
            rare = math.log(n_sections / len(citers))
            if rare <= 0:
                continue
            for sec, n in citers.items():
                score[sec] += self.W_CROSSREF * rare * math.log(1 + n)

        # ---- the Subject slot -----------------------------------------------
        # A provision about a bicycle signal face cannot answer a question about
        # a regulatory turn-prohibition sign, however many words they share.
        # Applied last, as a damping of sections whose stated subject cannot be
        # the question's -- not as a hard filter, because the subject is read
        # off a heading and a heading can be wrong or elliptical.
        if self.W_SUBJECT < 1.0:
            qs = self.subjects(query)
            if qs:
                for sec in list(score):
                    if not self.subject_compatible(sec, qs):
                        score[sec] *= self.W_SUBJECT

        return score.most_common(top)

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
    def _subject_of_section(self, sec: str) -> set:
        """What a section is ABOUT, as opposed to what it says about it.

        Read off the heading. "Size of Regulatory Signs" is about regulatory
        signs; "size" is the attribute. Where there is no "of", the whole
        heading is taken as the subject, which is right for "Movement
        Prohibition Signs" and harmless for "Mounting Height".
        """
        cached = self._subj_cache.get(sec)
        if cached is not None:
            return cached
        title = self.sec_title.get(sec, '') or ''
        parts = _TITLE_SPLIT.split(title, 1)
        if len(parts) == 2:
            subject_text = parts[1]
        elif _DEVICE_NOUN.search(title):
            # "Movement Prohibition Signs" -- the whole heading is the subject
            subject_text = title
        else:
            # "Mounting Height", "Dimensions", "Retroreflectivity" -- an
            # attribute with no device named, so the section governs EVERY
            # device. Returning an empty set means "no subject stated", and a
            # section with no subject must never be excluded by a subject test:
            # 2A.15 Mounting Height applies to a regulatory sign as much as to
            # a warning one, and is one of the sections our worked example
            # needs.
            subject_text = ''
        # drop the sign codes a heading lists in brackets; they are handled
        # separately and far more precisely by the code itself
        subject_text = re.sub(r'\([^)]*\)', ' ', subject_text)
        words = _stem_set(subject_text)
        self._subj_cache[sec] = words
        return words

    def subject_compatible(self, sec: str, q_subjects: set) -> bool:
        """Could a provision in this section be about what the question is about?

        Deliberately permissive. A section that names no device governs every
        device, and a question that names none is asking generally -- in both
        cases there is nothing to contradict, so nothing is excluded. Only a
        stated subject on BOTH sides, with no overlap, is a mismatch.
        """
        if not q_subjects:
            return True
        s = self._subject_of_section(sec)
        if not s:
            return True
        return bool(s & q_subjects)

    def subjects(self, q: str) -> set:
        """What a question is about: the devices it names, however it names them.

        Three sources, in the order the literature extracts them. A sign code is
        the most precise -- R3-2 names one device and, through the sign-size
        table, its governing section. A legend ("No Left Turn") names the same
        device in words. The series letter gives the family, so a question about
        R3-2 is known to be about a regulatory sign even when it never says so,
        which is what lets a provision in 2B.03 about regulatory signs apply to
        it and one in 4H.03 about signal faces not.
        """
        found: set = set()
        for m in re.finditer(r'\b([A-Z]{1,3}\d{1,3}(?:-\d{1,3}[a-zA-Z]{0,2})?P?)\b', q):
            code = m.group(1).upper()
            key = f'signcode:{code}'
            if key not in self.N:
                continue
            found.add(code.lower())
            series = re.match(r'^([A-Z]{1,3})', code).group(1)
            family = _SIGN_SERIES.get(series) or _SIGN_SERIES.get(series[:1])
            if family:
                found |= _stem_set(family)
            sec = self.N[key].section
            if sec:
                found |= self._subject_of_section(sec)
        for legend, node in list(self.signnames.items()) + list(self.sign_labels.items()):
            # A single common word is not a device name by itself. "BUSINESS"
            # is a real legend (M4-3P) and "LEFT" is a real legend (E11-2), but
            # a question saying "a business area" or "No Left Turn" is naming
            # neither -- and letting them through put route plaques and
            # expressway guide signs into the question's subject, which then
            # excused sections that should have been ruled out.
            #
            # But requiring two words threw away "STOP sign", which is the
            # subject of half the gold set. The distinction is not length, it
            # is whether the question writes the legend AS a device: "STOP
            # sign" names one, "a business area" does not.
            one_word = ' ' not in legend.strip()
            pat = r'\b' + re.escape(legend) + r'\b'
            if one_word:
                pat += r'\s+(?:sign|plaque|marking|signal|beacon|assembly|symbol)s?\b'
            if re.search(pat, q, re.I):
                found |= _stem_set(legend)
                # A legend names a sign, so it names that sign's FAMILY too.
                # Without this, "STOP sign" gave the subject {stop, plaque} and
                # 2B.03 "Size of Regulatory Signs" was judged incompatible --
                # the correct section, excluded, because nothing recorded that
                # a STOP sign is a regulatory sign. The code says so: R1-1.
                code = node.split(':', 1)[1] if ':' in node else ''
                m2 = re.match(r'^([A-Z]{1,3})', code.upper())
                if m2:
                    fam = _SIGN_SERIES.get(m2.group(1)) or _SIGN_SERIES.get(m2.group(1)[:1])
                    if fam:
                        found |= _stem_set(fam)
                sec = self.N[node].section if node in self.N else ''
                if sec:
                    found |= self._subject_of_section(sec)
        return found

    def facts(self, q: str) -> List[Fact]:
        """The measured values a question states, typed like the manual's own.

        This is the half that was missing. The manual's numbers carry their
        meaning -- not "35" but SPEED_LIMIT_POSTED 35 mph. A question's numbers
        carried nothing, so a section's condition had nothing to be checked
        against and routing fell back to counting shared words.
        """
        out: List[Fact] = []
        taken: List[Tuple[int, int]] = []
        for m in _FACT_DIM.finditer(q):
            unit = _FACT_UNIT.get(m.group(3).lower(), m.group(3).lower())
            taken.append((m.start(), m.end()))
            # width x height, per Table 2B-1's own note. Width is the value a
            # size condition is keyed on; the pair is kept in `said`.
            out.append(Fact(kind='SIZE', value=float(m.group(1)), unit=unit,
                            said=q[max(0, m.start() - 28):m.end()].strip()))
        for m in _FACT_NUM.finditer(q):
            if any(a <= m.start() < b for a, b in taken):
                continue
            raw_unit = m.group(2).lower()
            unit = _FACT_UNIT.get(raw_unit, raw_unit)
            val = float(m.group(1))
            before = q[max(0, m.start() - 60):m.start()].lower()
            after = q[m.end():m.end() + 36].lower()
            kind: Optional[str] = None
            if unit == 'mph':
                # the manual's own speed classifier, widened for question wording
                kind, _alts = canonical_speed(q, m.start(), m.end())
            if kind is None:
                for pat, k in _FACT_AFTER:
                    if re.search(pat, after):
                        kind = k
                        break
            if kind is None:
                for pat, k in _FACT_BEFORE:
                    if re.search(pat, before):
                        kind = k
                        break
            if kind is None:
                # fall back to the manual's noun vocabulary, nearest head wins
                for head in _QUANTITY_HEADS_LONGEST_FIRST:
                    if re.search(r'\b' + re.escape(head) + r's?\b', before):
                        kind = _HEAD_TO_KIND[head]
                        break
            if kind:
                out.append(Fact(kind=kind, value=val, unit=unit,
                                said=q[max(0, m.start() - 28):m.end() + 12].strip()))
        return out

    def satisfied(self, facts: List[Fact]) -> List[Tuple[str, str, str]]:
        """Sentences whose stated condition these facts actually satisfy.

        WHY THIS IS DIFFERENT FROM EVERY OTHER SIGNAL HERE
        A shared word is not evidence. "Speed" appears in 542 sentences across
        189 sections carrying 28 distinct meanings, so matching on it tells you
        almost nothing. A satisfied condition is evidence: the manual said
        "where the posted speed limit is 35 mph or less", the question said the
        posted limit is 35, and that provision now demonstrably applies. It can
        be put on a certificate; a word count cannot.

        Returns (node id, section, why) for each sentence whose condition holds.
        """
        if not facts:
            return []
        hits: List[Tuple[str, str, str]] = []
        for nid, node in self.N.items():
            if node.kind not in ('SENTENCE', 'NOTE'):
                continue
            if 'CONDITION' not in (node.pieces or []):
                continue
            for cond in (node.quantities or []):
                kind, num, op = cond.get('kind'), cond.get('number'), cond.get('op')
                if not kind or num is None or op not in _CMP:
                    continue
                try:
                    threshold = float(str(num).replace(',', ''))
                except ValueError:
                    continue
                for f in facts:
                    if f.kind != kind:
                        continue
                    if not _units_comparable(f.unit, cond.get('unit')):
                        continue
                    if _CMP[op](f.value, threshold):
                        hits.append((nid, node.section,
                                     f'{kind} {f.value:g} satisfies "{op} {num}"'))
                    break
        return hits

    def parse_ranked(self, query: str, chunks: Sequence[Dict[str, Any]] = (),
                     section_id: str = '', k: int = 5
                     ) -> Tuple[List['Candidate'], ParseReport]:
        """Compile the best k sections, not just the first one that works.

        The scorer already ranked several sections and `parse` already walked
        them -- it just returned the first that compiled and dropped the rest
        on the floor. When the ranking was wrong the answer was wrong and
        nothing in the output said so. Keeping the runners-up costs one extra
        compile each and turns a silent misroute into a named alternative the
        certificate can carry.

        Returns the candidates best-first. An empty list means nothing in the
        graph compiled, which is a refusal, not an error.
        """
        report = ParseReport()
        report.attempts = 1
        anchors = self.anchors(query)
        report.notes.append('anchors: ' + (', '.join(
            f'{a.kind}:{a.matched}' for a in anchors) or 'none'))

        # Ask the scorer for more sections than we mean to keep. Some of the
        # top ones will be rejected at compile time, and a rejection should
        # not cost a slot. Measured on the gold set: the correct section is
        # ranked 1st 12/20 of the time but is inside the top 5 17/20, so the
        # depth of this pool is what decides whether the right answer is in
        # the candidate set at all.
        pool = max(10, k * 3)
        candidates = [(section_id, 99.0)] if section_id else []
        candidates += [c for c in self.score_sections(query, anchors, top=pool)
                       if c[0] != section_id]
        if not candidates:
            report.source = 'failed'
            report.notes.append('the query did not anchor anywhere in the graph')
            return [], report
        report.notes.append('sections: ' + ', '.join(
            f'{s}({sc:.1f})' for s, sc in candidates[:6]))

        # Look at more sections than we intend to keep: some of the top ones
        # will be rejected (6P.01 is a collection of Typical Application notes,
        # not a rule set), and a rejection should not cost us a slot.
        out: List[Candidate] = []
        for sec, score in candidates:
            if len(out) >= k:
                break
            spec = self.build(query, sec, report)
            if spec is None:
                continue
            problems = spec.problems()
            if problems:
                report.problems.append(problems)
                report.notes.append(f'section {sec} rejected: {problems[:2]}')
                continue
            out.append(Candidate(section=sec, score=score, spec=spec,
                                 title=self.sec_title.get(sec, ''),
                                 obligations=len(spec.obligations)))

        if not out:
            report.source = 'failed'
            return [], report

        report.source = 'graph_parser'
        report.notes.append(f'compiled from section {out[0].section}')
        if len(out) > 1:
            report.notes.append('alternatives: ' + ', '.join(
                f'{c.section}({c.score:.1f}, {c.obligations} obligations)'
                for c in out[1:]))
        return out, report

    def parse(self, query: str, chunks: Sequence[Dict[str, Any]] = (),
              section_id: str = '') -> Tuple[Optional[NetworkSpec], ParseReport]:
        """Drop-in for `make_semantic_parser`: returns the single best spec.

        The alternatives are not lost -- they are named in `report.notes`
        under 'alternatives:'. Call `parse_ranked` to get their specs.
        """
        ranked, report = self.parse_ranked(query, chunks, section_id)
        return (ranked[0].spec if ranked else None), report


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
