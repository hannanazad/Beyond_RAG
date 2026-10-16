"""Two changes to finding the provisions for Kq (15 October 2026).

  1. Manual terms, sentence by sentence. The definitions were matched against
     the whole question only, and the two best terms kept. A side fact in the
     question then took both places, and the sentence that named the device in
     everyday words never reached the manual's own term for it. Now each
     informative sentence also gets its best term, matched against that
     sentence; the whole question's two are kept as before.
  2. The paragraphs of a section that is the question's topic. The closure
     takes up to `anchor_section_chunks` normative paragraphs of the top
     sections. In page order a long section's early list items used up the
     places and its later paragraphs never arrived. With the finder on, a
     section whose normative paragraphs do not all fit now gives the ones the
     cross-encoder ranks best against the question; one that fits is taken
     whole, as before, and with the finder off nothing changes.

Everything here is made up (Part 9, sections 9Y.xx; panels, ripple marks). No
sample question, gold answer or MUTCD text is used.

Run: python3 tests/test_find_sentences.py
"""
import math
import pickle
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrag.config import CFG
from mrag.find_provisions import ProvisionFinder
from mrag.kg_vine import VineKG
from mrag.retrieval import Retriever

TMP = Path(tempfile.mkdtemp())
PART = "Part 9 Made-Up Panels"


def chunk(cid, sec, kind, ordinal, text, title, **kw):
    d = {"chunk_id": cid, "section_id": sec, "section_title": title, "content_type": kind,
         "ordinal": ordinal, "text": text, "source": kw.pop("source", "paragraph"),
         "parent_id": kw.pop("parent_id", None), "item": kw.pop("item", None),
         "lead_in": kw.pop("lead_in", None), "authority_inferred": False,
         "figure_refs": [], "table_refs": [], "section_refs": [],
         "part": PART, "chapter": f"Chapter {sec[:2]}. Made-Up Chapter"}
    d.update(kw)
    return d


LEAD = "The following words shall have these meanings:"
DEFS = ["1. Speed Panel-a made-up panel that shows the speed.",
        "2. Blue Speed Board-a made-up board that shows blue speed numbers.",
        "3. Ripple Mark-a made-up mark that includes wave codes or similar patterns.",
        "4. Panel Speed-see Speed Panel."]
CHUNKS = [chunk("Y02_Standard_01", "9Y.02", "Standard", 1,
                "Unless otherwise defined in this Section, words shall have their usual meaning.", "Definitions")]
CHUNKS += [chunk(f"Y02_Standard_02_item{i}", "9Y.02", "Standard", 2, d, "Definitions", source="list_item",
                 parent_id="Y02_P2", item=str(i), lead_in=LEAD) for i, d in enumerate(DEFS, 1)]
# the side fact's section: many paragraphs about speed panels
CHUNKS += [chunk(f"Y10_Standard_{n:02d}", "9Y.10", "Standard", n,
                 f"Each speed panel shall be blue and white, with the speed posted in row {n}.", "Speed Panels")
           for n in range(1, 9)]
# the provision that decides the question: none of the question's own words
CHUNKS += [chunk("Y20_Standard_01", "9Y.20", "Standard", 1,
                 "When ripple marks are used, a person shall not be able to see them.", "Machine Reading")]
# a long section: twelve list items in page order, then the paragraph that matters
CHUNKS += [chunk("Y30_Option_01", "9Y.30", "Option", 1, "Lanterns may be used to:", "Lanterns")]
CHUNKS += [chunk(f"Y30_Option_01_item{i}", "9Y.30", "Option", 1, f"{i}. Light corner number {i}.", "Lanterns",
                 source="list_item", parent_id="Y30_P1", item=str(i), lead_in="Lanterns may be used to:")
           for i in range(1, 13)]
CHUNKS += [chunk("Y30_Guidance_02", "9Y.30", "Guidance", 2, "Lanterns should be hung low.", "Lanterns"),
           chunk("Y30_Option_03", "9Y.30", "Option", 3,
                 "A bell may be rung together with or instead of the lanterns.", "Lanterns"),
           chunk("Y30_Support_04", "9Y.30", "Support", 4, "Lanterns help made-up readers.", "Lanterns"),
           chunk("FIGNOTE_9Y-1_01", "9Y.30", "Standard", 1,
                 "Figure 9Y-1. Lanterns used together with or instead of a bell at a corner.", "Lanterns",
                 source="figure_note", parent_id="Figure 9Y-1", item="1")]
# a short section: fits whole
CHUNKS += [chunk("Y40_Standard_01", "9Y.40", "Standard", 1, "Posts shall be grey.", "Posts"),
           chunk("Y40_Guidance_02", "9Y.40", "Guidance", 2, "Posts should be short.", "Posts"),
           chunk("Y40_Option_03", "9Y.40", "Option", 3, "Posts may be painted.", "Posts")]
BY_ID = {c["chunk_id"]: c for c in CHUNKS}

N = {f"sent:{c['chunk_id']}#0": SimpleNamespace(kind="SENTENCE", section=c["section_id"], text=c["text"],
                                                 authority=None, pieces=()) for c in CHUNKS}
for sec in sorted({c["section_id"] for c in CHUNKS}):
    N[f"section:{sec}"] = SimpleNamespace(kind="SECTION", section=sec, text=sec, authority=None, pieces=())
GRAPH = TMP / "graph.pkl"
pickle.dump((N, [], CHUNKS), open(GRAPH, "wb"))
ITEMS = TMP / "items.jsonl"
ITEMS.write_text("")
kg = VineKG(GRAPH, items_path=ITEMS)

WORD = re.compile(r"[a-z0-9]+")
STOP = {"a", "an", "the", "of", "on", "at", "is", "be", "it", "to", "this", "there", "that", "shall",
        "should", "may", "does", "manual", "allow", "made", "up", "and", "in", "where", "for", "are", "with"}


def words(s):
    return [w for w in WORD.findall(s.lower()) if w not in STOP]


VOCAB = {}


class Text:
    def encode_both(self, texts):
        dense, sparse = [], []
        for t in texts:
            for w in words(t):
                VOCAB.setdefault(w, len(VOCAB))
        for t in texts:
            v = np.zeros(512, dtype=np.float32)
            sp = {}
            for w, n in Counter(words(t)).items():
                v[VOCAB[w]] += n
                sp[VOCAB[w]] = sp.get(VOCAB[w], 0.0) + float(n)
            dense.append(v)
            sparse.append(sp)
        return np.stack(dense), sparse


TEXT = Text()


class Store:
    def fetch_chunks_by_ids(self, name, ids, default_score=0.0):
        return [{"payload": BY_ID[i], "score": default_score} for i in ids if i in BY_ID]

    def search_chunks_hybrid(self, name, dense, sparse, top_k=30):
        mat, _ = TEXT.encode_both([c["text"] for c in CHUNKS])
        mat = mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
        s = mat @ (np.asarray(dense) / max(float(np.linalg.norm(dense)), 1e-8))
        order = sorted(range(len(CHUNKS)), key=lambda i: (-s[i], i))[:top_k]
        return [{"payload": CHUNKS[i], "score": float(s[i])} for i in order if s[i] > 0]


class Rerank:
    def rank(self, q, docs, top_k=6):
        qw = set(words(q))
        sc = [len(qw & set(words(d))) / math.sqrt(1 + len(set(words(d)))) for d in docs]
        order = sorted(range(len(docs)), key=lambda i: (-sc[i], i))[:top_k]
        return [(i, float(sc[i])) for i in order]


checks = 0


def check(cond, what):
    global checks
    assert cond, what
    checks += 1
    print(f"  ok  {what}")


Q = ("A town wants to print wave codes on its panels. "
     "The speed panels are blue, and the speed is posted on each speed panel. Is this allowed?")


def scored_lists(store, cfg):
    def run(texts):
        d, s = TEXT.encode_both(list(texts))
        return [[h["payload"] for h in store.search_chunks_hybrid("chunks", d[i], s[i], top_k=cfg.top_k_fused)]
                for i in range(len(texts))]
    return run


def finder(per_sentence):
    cfg = SimpleNamespace(top_k_fused=6, compile_sentence_queries=5, compile_list_depth=3,
                          compile_term_queries=2, compile_term_candidates=5, compile_heading_sections=1,
                          compile_heading_candidates=5, compile_heading_paragraphs=16, compile_pool_cap=20,
                          compile_sentence_terms=per_sentence)
    store = Store()
    return ProvisionFinder(kg, TEXT, store, Rerank(), "chunks", cfg, definition_sections=("9Y.02",)), store, cfg


# --------------------------------------------------------------------------- #
print("1. Manual terms, sentence by sentence")
fp, store, cfg = finder(0)
old = fp.candidates(Q, scored_lists(store, cfg))
check([t["term"] for t in old["terms"]] == ["Speed Panel", "Panel Speed"],
      "matched against the whole question only, the side fact takes both term places")
check("Y20_Standard_01" not in old["pool"], "so the deciding provision never enters the pool")

fp, store, cfg = finder(1)
new = fp.candidates(Q, scored_lists(store, cfg))
terms = {t["term"]: t["from"] for t in new["terms"]}
check(terms.get("Speed Panel") == "question" and terms.get("Panel Speed") == "question",
      "the whole question keeps its two terms")
check(terms.get("Ripple Mark") == "sentence 1",
      "the sentence naming the device in everyday words gets the manual's term for it")
check("Y20_Standard_01" in new["pool"] and "term: Ripple Mark" in new["sources"]["Y20_Standard_01"],
      "the deciding provision reaches the pool, through that term")
check(new["pool"][:len(old["pool"][:6])] == old["pool"][:6],
      "the whole question's own top results still come first")
check(len(new["terms"]) == len({t["term"] for t in new["terms"]}), "a term is not taken twice")

# --------------------------------------------------------------------------- #
print("2. A long topic section gives the paragraphs that match the question")
keep = {k: getattr(CFG, k) for k in ("anchor_sections", "anchor_section_chunks")}
try:
    CFG.anchor_sections, CFG.anchor_section_chunks = 1, 12
    r = Retriever(Store(), kg, TEXT, None, Rerank())
    seed = [dict(BY_ID["Y30_Guidance_02"])]
    q2 = "What may be used together with or instead of the lanterns at a corner?"

    def anchor_ids(query):
        got = r._close_kq(seed, 40, ("anchor_section",), query=query)
        return [c["chunk_id"] for c in got if c["source"] == "anchor_section"]

    page = anchor_ids(None)
    check(len(page) == 12 and "Y30_Option_03" not in page,
          "in page order the list items use up the places and Paragraph 3 never arrives (the old way)")
    best = anchor_ids(q2)
    check(len(best) == 12 and "Y30_Option_03" in best and best[0] == "Y30_Option_03",
          "ranked against the question, the paragraph that answers it comes first")
    check("Y30_Support_04" not in best, "Support is still not taken before the normative paragraphs")
    check("FIGNOTE_9Y-1_01" not in best, "a figure note is not ranked in place of a paragraph (notes have their own kind)")
    seed40 = [dict(BY_ID["Y40_Standard_01"])]
    got = r._close_kq(seed40, 40, ("anchor_section",), query="Are painted posts allowed?")
    check([c["chunk_id"] for c in got if c["source"] == "anchor_section"] == ["Y40_Guidance_02", "Y40_Option_03"],
          "a section that fits is taken whole, in page order, as before")
finally:
    for k, v in keep.items():
        setattr(CFG, k, v)

# --------------------------------------------------------------------------- #
print("3. retrieve_for_compile passes the question to the closure only with the finder on")
seen = {}
r = Retriever(Store(), kg, TEXT, None, Rerank())
orig = r._close_kq


def spy(*a, **kw):
    seen["query"] = kw.get("query")
    return orig(*a, **kw)


r._close_kq = spy
keep = {k: getattr(CFG, k) for k in ("compile_find_provisions", "top_k_fused", "compile_list_depth",
                                     "compile_pool_cap")}
try:
    CFG.top_k_fused, CFG.compile_list_depth, CFG.compile_pool_cap = 6, 3, 20
    CFG.compile_find_provisions = False
    r.retrieve_for_compile(Q, top_k=6, closure=True)
    check(seen.get("query") is None, "finder off: the closure is exactly the old one")
    CFG.compile_find_provisions = True
    r._finder = ProvisionFinder(kg, TEXT, r.store, r.rerank, CFG.coll_chunks, CFG, definition_sections=("9Y.02",))
    res = r.retrieve_for_compile(Q, top_k=6, closure=True)
    check(seen.get("query") == Q, "finder on: the closure ranks a long topic section against the question")
    check(all("from" in t for t in res.debug["find"]["terms"]), "the record says where each term came from")
finally:
    for k, v in keep.items():
        setattr(CFG, k, v)

# --------------------------------------------------------------------------- #
print("4. A retrieval change is also compared with the last accepted retrieval")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))
import retrieval_check as rc  # noqa: E402
import vine_run as vr  # noqa: E402


def res(cid, ok):
    return {"case_id": cid, "in_kq": {"9Y.10": ok}, "chunk_in_kq": ok}


accepted = {"store_items": 100, "results": [res("A", True), res("B", True), res("C", False)]}
g = vr.gate_against_accepted([res("A", True), res("B", True), res("C", True)], accepted, 100, rc.gate)
check(g["ok"] and g["gained"] == ["C"] and g["lost"] == [], "a case gained and none lost: it passes")
g = vr.gate_against_accepted([res("A", True), res("B", False), res("C", True)], accepted, 100, rc.gate)
check(not g["ok"] and g["lost_or_crashed"] == ["B"],
      "one gained and one lost: it stops, though the count is the same (the old gate let this through)")
g = vr.gate_against_accepted([res("A", True), {"case_id": "B"}, res("C", False)], accepted, 100, rc.gate)
check(not g["ok"] and g["lost_or_crashed"] == ["B"], "a case that crashed stops it")
check(vr.gate_against_accepted([res("A", True)], accepted, 99, rc.gate) is None
      and vr.gate_against_accepted([res("A", True)], {}, 100, rc.gate) is None,
      "nothing to compare with (another store, or no accepted file): no verdict, no crash")
check(vr.ACCEPTED_RETRIEVAL_CHECK.endswith("retrieval_check_r005fcc2_s0c3805.json"),
      "the accepted run is the 11 Oct one (retrieval code 005fcc2)")

print(f"\nALL SENTENCE-TERM AND TOPIC-SECTION TESTS PASSED ({checks} checks)")
