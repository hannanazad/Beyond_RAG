"""retrieve_for_obligation with stubbed store/models: checks the anchor cap
and the pinning of established-evidence notes."""
import sys, types, pickle
sys.path.insert(0, "/home/claude/tests"); sys.path.insert(0, "/home/claude/w2")
import stubs, numpy as np
from mrag.kg import KG
import mrag.retrieval as R

kg = KG(pickle.load(open("/mnt/user-data/uploads/graph.gpickle", "rb")))
import json
rows = {r["chunk_id"]: r for r in map(json.loads, open("/mnt/user-data/uploads/chunks.jsonl"))}

class Store:
    def __init__(self): self.fetched = []
    def fetch_chunks_by_ids(self, coll, ids, default_score=0.0):
        self.fetched.append(list(ids))
        return [{"score": default_score, "payload": rows[i]} for i in ids if i in rows]
    def search_chunks_hybrid(self, *a, **k):
        # search returns unrelated chunks so the note can only arrive by pinning
        ids = [c for c in rows if c.startswith("MUTCD11e_2B04_")][:20]
        return [{"score": 0.9, "payload": rows[i]} for i in ids]
class Text:
    def encode_both(self, t): return [np.zeros(4)], [{}]
class Rank:
    def rank(self, q, docs, top_k): return [(i, 1.0 - i * 0.01) for i in range(min(top_k, len(docs)))]

R.CFG.figure_relevance_filter = False
ret = R.Retriever(Store(), kg, Text(), None, Rank())
certs = [{"claim": "taper governs", "status": "TRUE",
          "evidence": [{"type": "table", "id": "Table 6B-4"},
                       {"type": "section", "id": "1C.02"}]},
         {"claim": "unresolved", "status": "UNKNOWN",
          "evidence": [{"type": "section", "id": "6B.01"}]}]
r = ret.retrieve_for_obligation("taper", "the taper length meets the formula", certificates=certs)
d = r.debug
print("established sections :", d["established_sections"])
print("established tables   :", d["established_tables"])
print("oversized, not pulled:", d["oversized_sections_not_pulled_whole"])
print("established notes    :", d["established_notes"])
print("anchor chunks pulled :", d["anchor_chunks"])
print("pinned notes         :", d.get("pinned_notes"))
print("chunks returned      :", len(r.chunks))

assert ("1C.02", 297) in d["oversized_sections_not_pulled_whole"], "1C.02 must not be swallowed"
assert d["anchor_chunks"] < 100, f"anchor pool still huge: {d['anchor_chunks']}"
assert "MUTCD11e_TBLNOTE_6B-4_01" in d["established_notes"]
assert d["pinned_notes"] == ["MUTCD11e_TBLNOTE_6B-4_01"], d.get("pinned_notes")
assert r.chunks[0]["chunk_id"] == "MUTCD11e_TBLNOTE_6B-4_01"
assert len(r.chunks) <= R.CFG.top_k_obligation_chunks
print("\nfirst chunk:", r.chunks[0]["chunk_id"], "|", r.chunks[0]["text"][:70])

# no certificates -> no pinning, no crash
r2 = ret.retrieve_for_obligation("taper", "some obligation")
assert r2.debug.get("pinned_notes") in (None, []) and r2.chunks
print("\nno certificates: chunks", len(r2.chunks), "| pinned", r2.debug.get("pinned_notes"))

# a small section is still pulled whole
r3 = ret.retrieve_for_obligation("stop", "the plaque is required",
    certificates=[{"claim": "x", "status": "TRUE", "evidence": [{"type": "section", "id": "2B.04"}]}])
assert r3.debug["oversized_sections_not_pulled_whole"] == []
assert r3.debug["anchor_chunks"] > 0
print("small section 2B.04 pulled whole: anchor chunks", r3.debug["anchor_chunks"])
print("\nOBLIGATION RETRIEVAL TESTS PASSED")
