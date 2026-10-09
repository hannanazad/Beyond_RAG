"""Finding the governing provisions for Kq (mrag/find_provisions.py, 9 October 2026).

  1. Reading the question: its sentences, which of them say something of their
     own ("Does the manual allow this?" does not), and their order.
  2. Reading the manual's definition lists: "12. Term-a definition",
     "C. Term (ABBR) - The definition", "Term-see Other Term"; a lead-in
     paragraph is not a definition.
  3. What the ranker reads: Part, Section, heading, the lead-in of a list item,
     then the paragraph.
  4. Reciprocal-rank fusion, with weights.
  5. The finder: a manual term found through its definition (and the term it
     points to with "see"), sections found by their headings and their
     normative paragraphs (no notes, no Support), the pool (the whole question's
     own top results always kept, the cap), where each candidate came from, and
     the ranking (a question of one sentence is ranked by the whole question
     alone; a side fact in one sentence does not outvote the rest).
  6. retrieve_for_compile with the finder off is the old path (no "find"
     record); with it on, a provision that the whole-question search misses
     because a side fact pulls it away is found, and Kq keeps its size.

Everything here is made up (Part 9, sections 9Z.xx; panels, tiles). No sample
question, gold answer or MUTCD text is used.
"""
import json
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
from mrag.find_provisions import (ProvisionFinder, content_words, informative_sentences,
                                  parse_definition, ranking_text, rrf, sentences_of, take_turns)
from mrag.kg_vine import VineKG
from mrag.retrieval import Retriever

TMP = Path(tempfile.mkdtemp())
PART = "Part 9 Made-Up Panels"

# ---- 1. the question ----------------------------------------------------------------
Q = ("A county puts luminous squares along a gravel strip. The advisory speed there is 25 mph. "
     "Does the manual allow this?")
assert sentences_of(Q) == ["A county puts luminous squares along a gravel strip.",
                           "The advisory speed there is 25 mph.", "Does the manual allow this?"]
assert content_words("Does the manual allow this?") == [], "function words, 'manual' and asking words do not count"
assert content_words("The MUTCD says it") == ["says"]
assert content_words("It doesn’t say. Is this placement correct and compliant?") == ["say", "placement"], \
    "a curly apostrophe is read as a straight one"
assert sentences_of("A panel on U.S. Route 9 is blue. Is No. 4 allowed?") == \
    ["A panel on U.S. Route 9 is blue.", "Is No. 4 allowed?"], "abbreviations do not end a sentence"
assert sentences_of("- a blue panel stands here\n- it faces east\nWhat applies?") == \
    ["- a blue panel stands here", "- it faces east", "What applies?"], "each list item is a sentence"
assert sentences_of("- a blue panel stands\n  near the lane\n- it faces east") == \
    ["- a blue panel stands near the lane", "- it faces east"], "an item's indented continuation is the item"
assert sentences_of("A county puts squares along\na gravel strip.\nIs that allowed?") == \
    ["A county puts squares along a gravel strip.", "Is that allowed?"], "a wrapped sentence is one sentence"
assert sentences_of("The barrier is a Type A. The road is closed. Cones, drums, etc. The zone is short.") == \
    ["The barrier is a Type A.", "The road is closed.", "Cones, drums, etc.", "The zone is short."], \
    "'Type A.' and 'etc.' do end sentences"
assert informative_sentences(Q) == ["A county puts luminous squares along a gravel strip.",
                                    "The advisory speed there is 25 mph."]
assert informative_sentences("What height is required for a blue panel in a panel zone?") == [], \
    "one informative sentence: the whole question already is that sentence"
many = " ".join(f"Panel number {i} stands near strip {i}." for i in range(1, 9)) + " Which panel shall face east?"
got = informative_sentences(many, most=5)
assert len(got) == 5 and got[:4] == sentences_of(many)[:4] and got[-1] == "Which panel shall face east?", got
print("1. the question: sentences, informative ones, the first four and the last")

# ---- 2. definitions -----------------------------------------------------------------
assert parse_definition("12. Glow Tile-a made-up tile that includes quick-glow (QG) dots.") == \
    ("Glow Tile", "a made-up tile that includes quick-glow (QG) dots.")
assert parse_definition("13. Glow Dot-see Glow Tile.") == ("Glow Dot", "see Glow Tile.")
assert parse_definition("14. Two-Way Panel Strip-a strip with panels both ways.") == \
    ("Two-Way Panel Strip", "a strip with panels both ways."), "a hyphen inside a term is followed by a capital"
assert parse_definition("C. Panel Driving System (PDS) - The made-up system that reads the panels.") == \
    ("Panel Driving System (PDS)", "The made-up system that reads the panels.")
assert parse_definition("F. Dynamic Panel Task (DPT) - All of the real-time work of a panel.") == \
    ("Dynamic Panel Task (DPT)", "All of the real-time work of a panel."), \
    "a lettered entry is split at its spaced dash, not at a hyphen inside the definition"
assert parse_definition("Unless otherwise defined in this Section, words shall have their usual meaning.") is None
assert parse_definition("Words used in Part 9 for low-speed panels are defined here.") is None, \
    "only numbered or lettered entries are definitions"
assert parse_definition("15. Right-of-Way Panel—the panel that assigns the strip.") == \
    ("Right-of-Way Panel", "the panel that assigns the strip."), "a long dash is the separator when there is one"
assert parse_definition("16. Built-up Strip—see Gravel Strip.") == ("Built-up Strip", "see Gravel Strip.")
assert parse_definition("17. Glow Tile-a tile—made up—that glows.") == ("Glow Tile", "a tile—made up—that glows."), \
    "a long dash inside the definition is not the separator"
print("2. definitions: numbered, lettered, 'see', hyphenated terms; a lead-in is not one")

# ---- 3. what the ranker reads ---------------------------------------------------------
t = ranking_text({"part": PART, "section_id": "9Z.10", "section_title": "Glow Tiles",
                  "lead_in": "Glow tiles shall meet the following:", "text": "1. They shall be round."})
assert t == f"{PART} — Section 9Z.10 Glow Tiles\nGlow tiles shall meet the following:\n1. They shall be round.", t
assert ranking_text({"section_id": "9Z.10", "section_title": "Glow Tiles", "lead_in": "None", "text": "x"}) == \
    "Section 9Z.10 Glow Tiles\nx"
assert ranking_text({"part": "None", "section_id": "9Z.10", "section_title": None, "text": "x"}) == \
    "Section 9Z.10\nx", "'None' as text is no value"
assert len(ranking_text({"text": "y" * 5000})) == 1500
print("3. the ranker reads Part, Section, heading, lead-in, then the paragraph")

# ---- 4. fusion -----------------------------------------------------------------------------
f = rrf([["a", "b", "c"], ["c", "b", "a"]])
assert [x for x, _ in f] == ["a", "c", "b"], "a tie keeps the order first seen"
assert abs(f[0][1] - (1 / 61 + 1 / 63)) < 1e-12 and abs(f[2][1] - 2 / 62) < 1e-12, f
f = rrf([["a", "b"], ["b", "a"]], weights=[1.0, 0.5])
assert [x for x, _ in f] == ["a", "b"]
assert take_turns(list("abcdef"), [list("xbyz"), list("aqr")], 8) == list("axbqcydr"), \
    "whole, sentence 1, whole, sentence 2, ...; an id already taken is skipped"
assert take_turns(list("ab"), [list("xyz")], 6) == list("axbyz"), "a ranking that runs out gives its turn"
assert take_turns([], [list("xy"), list("pq")], 3) == list("xpy")
assert take_turns(list("abc"), [], 2) == list("ab"), "one view: its own order"
print("4. reciprocal-rank fusion (the pool), taking turns (the slots)")


# ---- a made-up manual ---------------------------------------------------------------------
def chunk(cid, sec, kind, ordinal, text, title, **kw):
    d = {"chunk_id": cid, "section_id": sec, "section_title": title, "content_type": kind,
         "ordinal": ordinal, "text": text, "source": kw.pop("source", "paragraph"),
         "parent_id": kw.pop("parent_id", None), "item": kw.pop("item", None),
         "lead_in": kw.pop("lead_in", None), "authority_inferred": False,
         "figure_refs": [], "table_refs": [], "section_refs": kw.pop("section_refs", []),
         "part": PART, "chapter": f"Chapter {sec[:2]}. Made-Up Chapter"}
    d.update(kw)
    return d


DEF_LEAD = "The following words shall have these meanings:"
CHUNKS = [
    chunk("Z02_Standard_01", "9Z.02", "Standard", 1,
          "Unless otherwise defined in this Section, words shall have their usual meaning.", "Definitions"),
    chunk("Z02_Standard_02_item1", "9Z.02", "Standard", 2,
          "1. Glow Tile-a made-up reflective tile that includes glow dots.", "Definitions",
          source="list_item", parent_id="Z02_P2", item="1", lead_in=DEF_LEAD),
    chunk("Z02_Standard_02_item2", "9Z.02", "Standard", 2, "2. Glow Dot-see Glow Tile.", "Definitions",
          source="list_item", parent_id="Z02_P2", item="2", lead_in=DEF_LEAD),
    chunk("Z02_Standard_02_item3", "9Z.02", "Standard", 2,
          "3. Gravel Strip-the made-up edge of a gravel lane.", "Definitions",
          source="list_item", parent_id="Z02_P2", item="3", lead_in=DEF_LEAD),
    # the provision that decides the question above; only its heading uses the question's words
    chunk("Z10_Standard_01", "9Z.10", "Standard", 1,
          "They shall not be visible to pedestrians at night.", "Luminous Squares"),
    chunk("Z10_Guidance_02", "9Z.10", "Guidance", 2, "They should be lit from below.", "Luminous Squares"),
    chunk("Z10_Support_03", "9Z.10", "Support", 3, "They help made-up readers.", "Luminous Squares"),
    chunk("TBLNOTE_9Z-10_01", "9Z.10", "Standard", 1, "Table 9Z-10. 1 They are counted per lane.",
          "Luminous Squares", source="table_note", parent_id="Table 9Z-10", item="1"),
    # a section named by its heading only
    chunk("Z12_Standard_01", "9Z.12", "Standard", 1, "It shall be used where a new strip begins.",
          "Added Strip Panels"),
    chunk("Z12_Option_02", "9Z.12", "Option", 2, "It may be omitted on a short strip.", "Added Strip Panels"),
] + [chunk(f"Z11_Guidance_{n:02d}", "9Z.11", "Guidance", n,
           f"The advisory speed of {20 + n} mph should be shown on panel {n}.",
           "Advisory Speeds") for n in range(1, 9)] \
  + [chunk(f"Z2{k}_Standard_01", f"9Z.2{k}", "Standard", 1, f"Made-up filler rule {k} about blue posts.",
           f"Blue Posts {k}") for k in range(0, 10)]
BY_ID = {c["chunk_id"]: c for c in CHUNKS}


def node(kind, section="", text=""):
    return SimpleNamespace(kind=kind, section=section, text=text, authority=None, pieces=())


N = {f"sent:{c['chunk_id']}#0": node("SENTENCE", c["section_id"], c["text"]) for c in CHUNKS}
for sec in sorted({c["section_id"] for c in CHUNKS}):
    N[f"section:{sec}"] = node("SECTION", sec, sec)
GRAPH = TMP / "graph.pkl"
pickle.dump((N, [], CHUNKS), open(GRAPH, "wb"))
ITEMS = TMP / "items.jsonl"
ITEMS.write_text("")
kg = VineKG(GRAPH, items_path=ITEMS)

# ---- lexical stand-ins for the encoder, the store's search and the cross-encoder
WORD = re.compile(r"[a-z0-9]+")
STOP = {"a", "an", "the", "of", "on", "at", "is", "be", "it", "to", "this", "there", "that", "shall",
        "should", "may", "does", "manual", "allow", "made", "up", "and", "in", "where", "for"}


def words(s):
    return [w for w in WORD.findall(s.lower()) if w not in STOP]


VOCAB = {w: i for i, w in enumerate(sorted({w for c in CHUNKS for w in words(c["text"] + " " + c["section_title"])}
                                         | {"county", "puts", "advisory", "glow", "dots", "along"}))}


class Text:
    def encode_both(self, texts):
        dense, sparse = [], []
        for t in texts:
            v = np.zeros(len(VOCAB) + 1, dtype=np.float32)
            sp = {}
            for w, n in Counter(words(t)).items():
                i = VOCAB.get(w, len(VOCAB))
                v[i] += n
                sp[i] = sp.get(i, 0.0) + float(n)
            dense.append(v)
            sparse.append(sp)
        return np.stack(dense), sparse


TEXT = Text()
MAT, _ = TEXT.encode_both([c["text"] for c in CHUNKS])
MAT = MAT / np.maximum(np.linalg.norm(MAT, axis=1, keepdims=True), 1e-8)


class Store:
    def __init__(self):
        self.searches = []

    def fetch_chunks_by_ids(self, name, ids, default_score=0.0):
        return [{"payload": BY_ID[i], "score": default_score} for i in ids if i in BY_ID]

    def search_chunks_hybrid(self, name, dense, sparse, top_k=30):
        self.searches.append(top_k)
        s = MAT @ (np.asarray(dense) / max(float(np.linalg.norm(dense)), 1e-8))
        order = sorted(range(len(CHUNKS)), key=lambda i: (-s[i], i))[:top_k]
        return [{"payload": CHUNKS[i], "score": float(s[i])} for i in order if s[i] > 0]


class Rerank:
    def __init__(self):
        self.queries = []

    def rank(self, q, docs, top_k=6):
        self.queries.append(q)
        qw = set(words(q))
        sc = [len(qw & set(words(d))) / math.sqrt(1 + len(set(words(d)))) for d in docs]
        order = sorted(range(len(docs)), key=lambda i: (-sc[i], i))[:top_k]
        return [(i, float(sc[i])) for i in order]


CFG_T = SimpleNamespace(top_k_fused=6, compile_sentence_queries=5, compile_list_depth=3,
                        compile_term_queries=2, compile_term_candidates=5, compile_heading_sections=1,
                        compile_heading_candidates=5, compile_heading_paragraphs=16, compile_pool_cap=12)

# ---- 5. the finder ------------------------------------------------------------------------
store, rr = Store(), Rerank()
fp = ProvisionFinder(kg, TEXT, store, rr, "chunks", CFG_T, definition_sections=("9Z.02",))
dq, sq = TEXT.encode_both(["Where are glow dots allowed?"])
terms = fp.manual_terms("Where are glow dots allowed?", dq[0], sq[0], 2)
assert fp._def_terms == ["Glow Tile", "Glow Dot", "Gravel Strip"], "the lead-in is not a definition"
names = [(x["term"], x["see"]) for x in terms]
assert ("Glow Dot", "Glow Tile") in names, names
assert all(x["chunk_id"].startswith("Z02_") for x in terms)
assert ProvisionFinder(kg, TEXT, store, rr, "chunks", CFG_T).manual_terms("x", dq[0], sq[0], 2) == [], \
    "no definition section in this graph under the manual's own ids: no terms, no crash"

dq, sq = TEXT.encode_both(["Which added strip panel goes where a new strip begins?"])
heads = fp.heading_sections("Which added strip panel goes where a new strip begins?", dq[0], sq[0], 1)
assert heads[0]["section"] == "9Z.12" and "Added Strip Panels" in heads[0]["heading"], heads
assert PART in heads[0]["heading"], "the heading carries the Part and the Chapter"
assert fp.section_paragraphs("9Z.10") == ["Z10_Standard_01", "Z10_Guidance_02"], \
    "normative paragraphs only: no Support, no table note"


def scored_lists(texts):
    d, s = TEXT.encode_both(list(texts))
    return [[h["payload"] for h in store.search_chunks_hybrid("chunks", d[i], s[i], top_k=CFG_T.top_k_fused)]
            for i in range(len(texts))]


found = fp.candidates(Q, scored_lists)
assert found["views"] == [Q] + found["sentences"] and len(found["sentences"]) == 2
whole = [p["chunk_id"] for p in scored_lists([Q])[0]]
assert "Z10_Standard_01" not in whole and any(c.startswith("Z11_") for c in whole), \
    f"the side fact pulls the whole-question search away: {whole}"
assert found["pool"][:6] == whole, "the whole question's own top results stay first in the pool"
assert len(found["pool"]) <= CFG_T.compile_pool_cap
assert "Z10_Standard_01" in found["pool"], found["pool"]
ways = found["sources"]["Z10_Standard_01"]
assert ways and "question" not in ways, f"found by another way of looking, not the whole question: {ways}"
ranked, rankings = fp.rank(found["views"], found["pool"], found["payloads"], 6)
assert set(rankings) == {"question", "sentence 1", "sentence 2"}
top = [c for c, _ in ranked]
assert rankings["question"][:4] == [c for c in rankings["question"] if c.startswith("Z11_")][:4], \
    "the whole question's own ranking is pulled by the side fact"
assert "Z10_Standard_01" in top, (top, rankings)
assert top[0] == rankings["question"][0] and top[1] == rankings["sentence 1"][0], "taken in turn"
assert sum(1 for c in top if c.startswith("Z11_")) <= 4, "one side fact does not take every slot"
whole_scores = dict(rr.rank(Q, [ranking_text(found["payloads"][c]) for c in found["pool"]], len(found["pool"])))
assert all(abs(sc - whole_scores[found["pool"].index(c)]) < 1e-12 for c, sc in ranked), \
    "each chosen paragraph carries its score against the whole question"
# one view only: the order is the cross-encoder's own
r1, k1 = fp.rank(["luminous squares pedestrians"], found["pool"], found["payloads"], 3)
docs = [ranking_text(found["payloads"][c]) for c in found["pool"]]
assert [c for c, _ in r1] == [found["pool"][i] for i, _ in rr.rank("luminous squares pedestrians", docs, 3)]
assert fp.rank([], found["pool"], found["payloads"], 3) == ([], {})
print("5. finder: terms through definitions and 'see', headings, normative paragraphs, the pool, "
      "where each came from, ranking by every view")

# ---- 6. retrieve_for_compile, off and on -----------------------------------------------------
keep = {k: getattr(CFG, k) for k in ("top_k_fused", "compile_find_provisions", "compile_list_depth",
                                     "compile_pool_cap", "compile_heading_sections", "compile_term_candidates",
                                     "compile_heading_candidates")}
import mrag.find_provisions as FPM
keep_defs = FPM.DEFINITION_SECTIONS
try:
    CFG.top_k_fused, CFG.compile_list_depth, CFG.compile_pool_cap = 6, 3, 12
    CFG.compile_heading_sections, CFG.compile_term_candidates, CFG.compile_heading_candidates = 1, 5, 5
    r = Retriever(Store(), kg, TEXT, None, Rerank())
    CFG.compile_find_provisions = False
    off = r.retrieve_for_compile(Q, top_k=6, closure=False)
    assert "find" not in off.debug and r._finder is None, "the old path does not build the finder"
    assert "Z10_Standard_01" not in {c["chunk_id"] for c in off.chunks}, "the old path misses it"
    assert all("found_by" not in c for c in off.chunks)

    CFG.compile_find_provisions = True
    r2 = Retriever(Store(), kg, TEXT, None, Rerank())
    r2._finder = ProvisionFinder(kg, TEXT, r2.store, r2.rerank, CFG.coll_chunks, CFG,
                                 definition_sections=("9Z.02",))
    on = r2.retrieve_for_compile(Q, top_k=6, closure=False)
    ids = [c["chunk_id"] for c in on.chunks]
    assert "Z10_Standard_01" in ids, ids
    assert len(on.chunks) == len(off.chunks), "Kq keeps its size"
    searched = [c for c in on.chunks if c["source"] == "searched"]
    assert searched and all(isinstance(c.get("found_by"), list) for c in searched)
    f = on.debug["find"]
    assert f["pool"] == len(f["pool_ids"]) == len(f["pool_sections"]) and set(f["rankings"]) >= {"question"}
    assert f["pool_sections"][f["pool_ids"].index("Z10_Standard_01")] == "9Z.10"
    json.dumps(on.debug)              # the record is plain JSON
    # the default finder is built once and kept
    r3 = Retriever(Store(), kg, TEXT, None, Rerank())
    r3.retrieve_for_compile(Q, top_k=4, closure=False)
    first = r3._finder
    r3.retrieve_for_compile("Which added strip panel is used?", top_k=4, closure=False)
    assert first is not None and r3._finder is first
finally:
    for k, v in keep.items():
        setattr(CFG, k, v)
print("6. retrieve_for_compile: off is the old path; on finds what a side fact hid, same Kq size")

print("\nALL FIND-PROVISIONS TESTS PASSED")
