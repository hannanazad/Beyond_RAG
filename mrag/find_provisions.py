"""Finding the governing provisions for a question -- the search half of Kq.

WHY (measured on DEV, 7 October 2026, `retrieval_test_20261007_052206.json`)
---------------------------------------------------------------------------
17 of the 154 DEV cases lost a needed section or paragraph before the parser
ever saw it. Reading them against the manual shows four causes:

1. **The question's extra facts pull the search away.** A scenario carries
   facts that do not decide anything (an advisory speed, a speed limit, the
   length of a job). One search over the whole text is pulled toward the
   sections those facts are about (2C.12 advisory speeds instead of 2C.46
   Added Lane signs).
2. **Everyday words, not the manual's words.** "QR-style pattern" for what
   the manual calls a *scanning graphic* (1C.02, item 209: "includes ... quick-
   response (QR) codes"); "automated vehicles" for *driving automation system*
   (1C.02 item 15: "Automated Vehicle-see Driving Automation System");
   "reflectors on posts" for *delineators*. The manual's definitions say which
   of its terms mean what.
3. **The right section is named by its heading, not by its text.** The
   manual is organised by Part, Chapter and Section (1A.04 Paragraph 9), and
   its headings name the device or situation: "Added Lane Signs (W4-3 and
   W4-6)", "EXIT CLOSED Panel", "Pavement Markings for Two-Way Left-Turn Lanes".
   An engineer looks a device up by its heading first.
4. **A paragraph read without its heading.** The ranker saw a paragraph's text
   alone. "Shall be applied by knowledgeable persons" says nothing about
   temporary traffic control until one reads that it sits in Section 6C.01.

WHAT THIS DOES (no language model; the same encoder and reranker as before)
--------------------------------------------------------------------------
More places to look, one judge, several views of the question:

    candidates  = search(whole question)
                + search(each informative sentence of the question)
                + search(each manual term whose definition matches the question)
                + the normative paragraphs of the sections whose headings
                  match the question
    ranked by   the cross-encoder, reading each paragraph WITH its Part,
                Section and heading (and a list item with its lead-in), against
                the whole question and against each informative sentence
    slots       taken in turn: one by the whole question's ranking, one by a
                sentence's ranking (the sentences taking turns), and so on

Why turns and not a vote: the whole question contains the side fact, so its
own ranking is pulled the same way as the side fact's sentence; a vote across
views then gives the side fact most of the say (measured on a made-up case in
tests/test_find_provisions.py). Taking turns gives every fact the question
states its own best provisions in Kq, and the whole question still fills half
the slots in its own order -- what it ranked in its top half is kept, as before.
A question of one informative sentence is ranked by the whole question alone,
as before -- over more candidates, and with each paragraph read with its heading.

A sentence is informative when it has at least three content words (words
other than function words, the words "manual" or "MUTCD", which every
question shares, and the words a question asks with: "allowed", "required",
"correct"). "Does the manual allow this?" is not; it adds nothing to search or
rank by.

The searched part of Kq keeps the same number of slots, so Kq does not grow.
Cross-reference expansion and the closure run on the result exactly as before.

Every candidate records where it came from (`sources`), and every view's
ranking is kept (`rankings`), so a run shows which way of looking brought each
provision in and how each view ranked it.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

log = logging.getLogger("mrag.find_provisions")

__all__ = ["sentences_of", "informative_sentences", "content_words", "parse_definition",
           "ranking_text", "rrf", "take_turns", "ProvisionFinder", "DEFINITION_SECTIONS"]

_SENT_SPLIT = re.compile(r"(?<=[.?!])\s+(?=[A-Z\"'(])")
# a piece that ends like this did not end a sentence: "U.S.", "D.C.", "Mr.", "vs."
# ("Type A." and "etc." do end sentences; "No. 4" and "Sec. 2" never split, a digit follows)
_ABBREV_END = re.compile(r"(?:\b[A-Z]\.){2,3}$|\b(?:Mr|Mrs|Ms|Dr|vs)\.$")
# a line that starts like this is an item of its own, not the rest of the line before
_ITEM_START = re.compile(r"^\s*(?:[-*•–]|\d{1,2}[.)]|[a-zA-Z][.)])\s")
# "209. Scanning Graphic-a graphic designed ..." ; "15. Automated Vehicle-see Driving
# Automation System." A hyphen inside a term ("Two-Way") is followed by a capital.
# Only numbered (or lettered) entries are read, so an ordinary paragraph with a
# hyphenated word is never taken for a definition.
_DEF_HEAD = re.compile(r"^\s*\d{1,3}\.\s*([A-Z0-9][^\n]{1,90}?)\s*[‐-―-]{1,2}\s*(?=[a-z(])(.*)$", re.S)
# the same entry written with a long dash: "12. Right-of-Way Assignment—the ..."
_DEF_LONG_DASH = re.compile(r"^\s*\d{1,3}\.\s*([A-Z0-9][^\n—–]{1,90}?)\s*[—–]\s*(\S.*)$", re.S)
# 5A.03 writes its terms as "A. Automated Driving System (ADS) - The hardware ...":
# a letter, the term, then a dash with a space on each side.
_DEF_LETTERED = re.compile(r"^\s*[A-Z]\.\s+([A-Z0-9][^\n]{1,90}?)\s+[‐-―-]{1,2}\s+(\S.*)$", re.S)
# the manual's own definition sections (1C.02 Words and Phrases; 5A.03 for Part 5)
DEFINITION_SECTIONS = ("1C.02", "5A.03")
_SEE = re.compile(r"^\s*see\s+([A-Z][A-Za-z0-9 ,/&'()-]{2,60}?)\s*\.?\s*$")
_NOTE_SOURCES = ("figure_note", "table_note")
_NORMATIVE = ("Standard", "Guidance", "Option")
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
# English function words, the two words every question about the manual shares, and
# the words a question asks with ("is it allowed", "is it required") -- none says
# which provision governs
_FUNCTION_WORDS = frozenset("""
a an the and or but nor if then than so yet of to in on at by for from with without into
onto over under about after before between through during within upon via per
is are was were be been being am do does did done doing has have had having can could may
might must shall should will would
this that these those it its it's there here what which who whom whose when where why how
whether not no any all each every some such as also only just very more most other another
same own both either neither too
i we you he she they them their theirs our ours your yours his her hers my mine me us him
don't doesn't didn't isn't aren't wasn't weren't can't cannot couldn't won't wouldn't shouldn't
mustn't hasn't haven't hadn't
manual mutcd
allow allowed allows permitted require required requires correct compliant acceptable ok okay
proper appropriate
""".split())


_TERM_SMALL = {"of", "and", "or", "the", "a", "an", "to", "for", "in", "on", "at", "by", "with"}


def _looks_like_term(t: str) -> bool:
    """A heading-like name: every word capitalised (or a number, a bracket, or a
    small joining word); lower case only inside a hyphenated word (Right-of-Way)."""
    return all(w[:1].isupper() or w[:1].isdigit() or w[:1] in "([" or w in _TERM_SMALL
               for w in t.split())


def parse_definition(body: str) -> Optional[Tuple[str, str]]:
    """(term, definition) of one entry of a definition list, or None."""
    body = body or ""
    m = _DEF_LETTERED.match(body)
    if not m:
        long_dash = _DEF_LONG_DASH.match(body)
        m = long_dash if long_dash and _looks_like_term(long_dash.group(1)) else _DEF_HEAD.match(body)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


def sentences_of(text: str) -> List[str]:
    """The sentences of a text, in order. A list item on its own line is a
    sentence; a sentence wrapped onto the next line is one; "U.S." does not end
    a sentence."""
    lines: List[str] = []
    last_is_item = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        item = bool(_ITEM_START.match(line))
        # a sentence wrapped onto the next line is one sentence (a list item's
        # own continuation is indented)
        wrapped = (lines and not re.search(r"[.?!:]$", lines[-1]) and not item
                   and (not last_is_item or raw[:1].isspace()))
        if wrapped:
            lines[-1] = f"{lines[-1]} {line}"
        else:
            lines.append(line)
            last_is_item = item
    out: List[str] = []
    for line in lines:
        for p in _SENT_SPLIT.split(line):
            p = p.strip()
            if not p:
                continue
            if out and _ABBREV_END.search(out[-1]):
                out[-1] = f"{out[-1]} {p}"
            else:
                out.append(p)
    return out


def content_words(text: str) -> List[str]:
    """The words of a text other than function words, "manual"/"MUTCD" and the
    asking words ("allowed", "required", "correct", ...)."""
    return [w for w in _WORD.findall((text or "").translate(_APOSTROPHES).lower())
            if w not in _FUNCTION_WORDS and len(w) > 1]


def informative_sentences(text: str, most: int = 5, min_content: int = 3) -> List[str]:
    """The sentences of a question that say something of their own (at least
    `min_content` content words). A question of one such sentence gives none:
    the whole question already is that sentence. More than `most`: the first
    `most - 1` and the last (the last usually asks)."""
    sents = [s for s in sentences_of(text) if len(content_words(s)) >= min_content]
    if len(sents) <= 1:
        return []
    if most > 0 and len(sents) > most:
        sents = sents[:most - 1] + sents[-1:]
    return sents[:max(most, 0)]


def _clean(v: Any) -> str:
    """A field as text; None, "None" and "null" (as some records carry them) are ''."""
    t = str(v if v is not None else "").strip()
    return "" if t.lower() in ("none", "null") else t


def ranking_text(payload: Dict[str, Any], limit: int = 1500) -> str:
    """What the cross-encoder reads for one paragraph: where it sits in the
    manual (Part, Section and heading), the lead-in of a list item, then the
    paragraph."""
    sec = _clean(payload.get("section_id"))
    title = _clean(payload.get("section_title"))
    part = _clean(payload.get("part"))
    head = " — ".join(x for x in (part, f"Section {sec} {title}".strip() if sec else title) if x)
    lead = _clean(payload.get("lead_in"))
    body = str(payload.get("text") or "")
    parts = [x for x in (head, lead, body) if x]
    return "\n".join(parts)[:limit]


def rrf(lists: Sequence[Sequence[str]], k: int = 60,
        weights: Optional[Sequence[float]] = None) -> List[Tuple[str, float]]:
    """Reciprocal-rank fusion of ranked id lists. Ties keep first-seen order."""
    score: Dict[str, float] = defaultdict(float)
    for i, lst in enumerate(lists):
        w = 1.0 if weights is None else float(weights[i])
        for r, x in enumerate(lst, 1):
            score[x] += w / (k + r)
    return sorted(score.items(), key=lambda kv: -kv[1])


def _sparse_dot(q: Dict[int, float], d: Dict[int, float]) -> float:
    if len(q) > len(d):
        q, d = d, q
    return float(sum(v * d.get(t, 0.0) for t, v in q.items()))


class _LocalIndex:
    """A small in-memory hybrid index (dense + sparse, fused by rank)."""

    def __init__(self, texts: List[str], dense: np.ndarray, sparse: List[Dict[int, float]]):
        self.texts = texts
        d = np.asarray(dense, dtype=np.float32)
        norms = np.linalg.norm(d, axis=1, keepdims=True)
        self.dense = d / np.maximum(norms, 1e-8)
        self.sparse = sparse

    def search(self, qd: np.ndarray, qs: Dict[int, float], top: int) -> List[int]:
        qd = np.asarray(qd, dtype=np.float32)
        qd = qd / max(float(np.linalg.norm(qd)), 1e-8)
        ds = self.dense @ qd
        d_rank = list(np.argsort(-ds, kind="stable")[:max(top * 3, top)])
        if qs:
            ss = np.array([_sparse_dot(qs, s) for s in self.sparse], dtype=np.float32)
            s_rank = list(np.argsort(-ss, kind="stable")[:max(top * 3, top)])
            fused = rrf([[str(i) for i in d_rank], [str(i) for i in s_rank]])
            return [int(i) for i, _ in fused[:top]]
        return [int(i) for i in d_rank[:top]]


class ProvisionFinder:
    """Builds the candidate pool for `retrieve_for_compile` and ranks it.

    `kg` is the VINE graph (chunk records and sections); `text` the encoder
    (`encode_both`); `store` the vector store; `rerank` the cross-encoder. The
    heading and definition indexes are built once, on first use, with the same
    encoder.
    """

    def __init__(self, kg, text, store, rerank, collection: str, cfg,
                 definition_sections: Sequence[str] = DEFINITION_SECTIONS) -> None:
        self.kg, self.text, self.store, self.rerank = kg, text, store, rerank
        self.collection = collection
        self.cfg = cfg
        self.definition_sections = tuple(definition_sections)
        self._headings: Optional[_LocalIndex] = None
        self._heading_secs: List[str] = []
        self._defs: Optional[_LocalIndex] = None
        self._defs_built = False
        self._def_terms: List[str] = []
        self._def_ids: List[str] = []

    # ------------------------------------------------------------- indexes
    def _records(self) -> Dict[str, Dict[str, Any]]:
        return getattr(self.kg, "_chunk", {}) or {}

    def _section_chunks(self, sec: str) -> List[str]:
        f = getattr(self.kg, "chunks_for_section", None)
        return list(f(sec)) if f is not None else []

    def _build_headings(self) -> None:
        recs = self._records()
        by_sec: Dict[str, Dict[str, Any]] = {}
        for c in recs.values():
            sec = str(c.get("section_id") or "")
            if sec and sec not in by_sec:
                by_sec[sec] = c
        secs = sorted(by_sec)
        texts = []
        for s in secs:
            c = by_sec[s]
            bits = [_clean(c.get(k)) for k in ("part", "chapter")]
            bits.append(f"Section {s} {_clean(c.get('section_title'))}".strip())
            texts.append(" — ".join(b for b in bits if b))
        if not texts:
            self._headings, self._heading_secs = None, []
            return
        dense, sparse = self.text.encode_both(texts)
        self._headings = _LocalIndex(texts, dense, sparse)
        self._heading_secs = secs

    def _build_definitions(self) -> None:
        recs = self._records()
        ids, names, texts = [], [], []
        for sec in self.definition_sections:
            for cid in self._section_chunks(sec):
                c = recs.get(cid) or {}
                if c.get("source") in _NOTE_SOURCES:
                    continue
                body = str(c.get("text") or "")
                parsed = parse_definition(body)
                if not parsed:
                    continue
                ids.append(cid)
                names.append(parsed[0])
                texts.append(body[:600])
        if not texts:
            self._defs = None
            self._defs_built = True
            return
        dense, sparse = self.text.encode_both(texts)     # if this fails, the next call tries again
        self._defs = _LocalIndex(texts, dense, sparse)
        self._def_terms = names
        self._def_ids = ids
        self._defs_built = True

    def _judge(self, query: str, docs: List[str], most: int) -> List[Tuple[int, float]]:
        if self.rerank is None:
            return [(j, 0.0) for j in range(min(most, len(docs)))]
        return list(self.rerank.rank(query, docs, top_k=most))

    # ---------------------------------------------------------------- steps
    def manual_terms(self, query: str, qd, qs, most: int) -> List[Dict[str, Any]]:
        """The manual's terms whose definitions match the question."""
        if most <= 0:
            return []
        if not self._defs_built:
            self._build_definitions()
        if self._defs is None:
            return []
        cand = self._defs.search(qd, qs, top=int(getattr(self.cfg, "compile_term_candidates", 10)))
        docs = [self._defs.texts[i] for i in cand]
        out = []
        for j, score in self._judge(query, docs, most):
            i = cand[j]
            parsed = parse_definition(self._defs.texts[i])
            see = _SEE.match(parsed[1] if parsed else "")
            out.append({"term": self._def_terms[i], "chunk_id": self._def_ids[i],
                        "see": see.group(1).strip() if see else "", "score": float(score)})
        return out

    def heading_sections(self, query: str, qd, qs, most: int) -> List[Dict[str, Any]]:
        """The sections whose headings match the question."""
        if most <= 0:
            return []
        if self._headings is None:
            self._build_headings()
        if self._headings is None:
            return []
        cand = self._headings.search(qd, qs, top=int(getattr(self.cfg, "compile_heading_candidates", 15)))
        docs = [self._headings.texts[i] for i in cand]
        return [{"section": self._heading_secs[cand[j]], "heading": docs[j], "score": float(s)}
                for j, s in self._judge(query, docs, most)]

    def section_paragraphs(self, sec: str) -> List[str]:
        """Normative paragraphs of a section, in the manual's order."""
        recs = self._records()
        return [i for i in self._section_chunks(sec)
                if (recs.get(i) or {}).get("content_type") in _NORMATIVE
                and (recs.get(i) or {}).get("source") not in _NOTE_SOURCES]

    # ---------------------------------------------------------------- whole
    def candidates(self, query: str,
                   scored_lists: Callable[[List[str]], List[List[Dict[str, Any]]]]) -> Dict[str, Any]:
        """Candidate chunk payloads from the four ways of looking, the views of
        the question to rank them by, and the record of where each came from.

        `scored_lists(texts) -> [[payload, ...], ...]` runs the pipeline's own
        hybrid search (and its scoring) for each text, best first."""
        cfg = self.cfg
        per_list = int(getattr(cfg, "compile_list_depth", 15))
        whole_depth = int(getattr(cfg, "top_k_fused", 30))
        sents = [s for s in informative_sentences(
            query, most=int(getattr(cfg, "compile_sentence_queries", 5))) if s != query.strip()]
        texts = [query] + sents
        dense, sparse = self.text.encode_both(texts)
        terms = self.manual_terms(query, dense[0], sparse[0],
                                  int(getattr(cfg, "compile_term_queries", 2)))
        term_texts: List[str] = []
        for t in terms:
            term_texts.append(t["term"])
            if t["see"]:
                term_texts.append(t["see"])
        term_texts = list(dict.fromkeys(term_texts))
        heads = self.heading_sections(query, dense[0], sparse[0],
                                      int(getattr(cfg, "compile_heading_sections", 2)))

        lists = scored_lists(texts + term_texts)
        sources: Dict[str, List[str]] = defaultdict(list)
        payloads: Dict[str, Dict[str, Any]] = {}
        ranked_lists: List[List[str]] = []
        names = ["question"] + [f"sentence {i + 1}" for i in range(len(sents))] \
            + [f"term: {t}" for t in term_texts]
        for name, lst in zip(names, lists):
            depth = whole_depth if name == "question" else per_list
            ids: List[str] = []
            for p in lst[:depth]:
                cid = str((p or {}).get("chunk_id") or "")
                if not cid or cid in ids:
                    continue
                payloads.setdefault(cid, p)
                if name not in sources[cid]:
                    sources[cid].append(name)
                ids.append(cid)
            ranked_lists.append(ids)
        head_ids: List[str] = []
        per_sec = int(getattr(cfg, "compile_heading_paragraphs", 16))
        for h in heads:
            ids = self.section_paragraphs(h["section"])[:per_sec]
            if not ids:
                continue
            for hit in self.store.fetch_chunks_by_ids(self.collection, ids):
                p = hit.get("payload") or {}
                cid = str(p.get("chunk_id") or "")
                if cid and cid not in head_ids:
                    payloads.setdefault(cid, p)
                    sources[cid].append(f"heading: {h['section']}")
                    head_ids.append(cid)
        ranked_lists.append(head_ids)
        pool = [cid for cid, _ in rrf(ranked_lists)]
        cap = int(getattr(cfg, "compile_pool_cap", 90))
        # what the whole-question search found first always stays in the pool
        first = ranked_lists[0][:whole_depth] if ranked_lists else []
        pool = list(dict.fromkeys(first + pool))[:max(cap, len(first))]
        return {"pool": pool, "payloads": payloads, "sources": dict(sources),
                "views": texts, "sentences": sents, "terms": terms,
                "term_queries": term_texts, "headings": heads}

    def rank(self, views: List[str], pool: List[str], payloads: Dict[str, Dict[str, Any]],
             want: int) -> Tuple[List[Tuple[str, float]], Dict[str, List[str]]]:
        """The cross-encoder's order of the pool against each view of the
        question (`views[0]` is the whole question), the slots taken in turn
        (see `take_turns`). Each chosen paragraph carries the cross-encoder's
        score against the whole question.

        Returns the top `want` and every view's full ranking."""
        if not pool or want <= 0 or not views:
            return [], {}
        docs = [ranking_text(payloads[c]) for c in pool]
        rankings: Dict[str, List[str]] = {}
        orders: List[List[str]] = []
        whole_score: Dict[str, float] = {}
        for i, v in enumerate(views):
            ranked = self.rerank.rank(v, docs, top_k=len(docs))
            order = [pool[j] for j, _s in ranked]
            if i == 0:
                whole_score = {pool[j]: float(sc) for j, sc in ranked}
            rankings["question" if i == 0 else f"sentence {i}"] = order
            orders.append(order)
        chosen = take_turns(orders[0], orders[1:], want)
        return [(c, whole_score.get(c, 0.0)) for c in chosen], rankings


def take_turns(whole: Sequence[str], sentences: Sequence[Sequence[str]], want: int) -> List[str]:
    """`want` ids, taken in turn: the next of the whole question's ranking,
    then the next of one sentence's ranking (the sentences taking turns), and
    so on. An id already taken is skipped; a ranking that runs out gives its
    turn to the others."""
    out: List[str] = []
    seen = set()
    pos = [0] * (1 + len(sentences))
    lists = [list(whole)] + [list(x) for x in sentences]

    def next_from(i: int) -> Optional[str]:
        lst = lists[i]
        while pos[i] < len(lst):
            x = lst[pos[i]]
            pos[i] += 1
            if x not in seen:
                return x
        return None

    turn = 0                      # which sentence is next
    whole_next = True
    while len(out) < want:
        got = None
        if whole_next:
            got = next_from(0)
        if got is None and sentences:
            for _ in range(len(sentences)):
                j = 1 + turn % len(sentences)
                turn += 1
                got = next_from(j)
                if got is not None:
                    break
        if got is None and not whole_next:
            got = next_from(0)
        if got is None:
            break
        seen.add(got)
        out.append(got)
        whole_next = not whole_next
    return out
