"""retrieve_for_compile must return Kq as a SUBGRAPH: the notes that condition
a cited table, the definitions of the terms used, the sections cited, and the
sibling items of a split list. Stubbed store/models; the graph is the real one."""
import sys, json, pickle
sys.path.insert(0, "/home/claude/tests"); sys.path.insert(0, "/home/claude/w2")
import stubs, numpy as np
from mrag.kg import KG
import mrag.retrieval as R

g = pickle.load(open("/home/claude/analysis/graph_v6.gpickle", "rb"))
kg = KG(g)
rows = {r["chunk_id"]: r for r in json.load(open("/home/claude/analysis/chunks_v6.json"))}
print("graph defined terms:", len(kg.defined_terms()))

# 2A.05 exercises all four closure kinds: it cites 5 sections, holds 10
# split list items, and its figures/tables carry 4 notes.
SEED = [c for c in rows if c.startswith("MUTCD11e_2A05_")][:8]

class Store:
    def fetch_chunks_by_ids(self, coll, ids, default_score=0.0):
        return [{"score": default_score, "payload": rows[i]} for i in ids if i in rows]
    def search_chunks_hybrid(self, *a, **k):
        return [{"score": 0.9, "payload": rows[i]} for i in SEED]
class Text:
    def encode_both(self, t): return [np.zeros(4)], [{}]
class Rank:
    def rank(self, q, docs, top_k): return [(i, 1.0 - i*0.01) for i in range(min(top_k, len(docs)))]

R.CFG.figure_relevance_filter = False
ret = R.Retriever(Store(), kg, Text(), None, Rank())

# ---- 1. closure off = the old behaviour --------------------------------
base = ret.retrieve_for_compile("sign placement and legibility", closure=False)
print("\nwithout closure:", len(base.chunks), "chunks |", base.debug.get("closure"))
assert base.debug.get("closure") is None

# ---- 2. closure on ------------------------------------------------------
r = ret.retrieve_for_compile("sign placement and legibility")
print("with closure   :", len(r.chunks), "chunks | by reason:", r.debug["closure"])
assert len(r.chunks) > len(base.chunks)
by_src = {}
for c in r.chunks: by_src[c.get("source", "searched")] = by_src.get(c.get("source", "searched"), 0) + 1
print("sources:", by_src)

# the note that carries the condition on the table must be in Kq
ids = {c["chunk_id"] for c in r.chunks}
notes = [c for c in r.chunks if c.get("source") == "note"]
assert notes, "no notes reached Kq"
print("\nnotes in Kq:", [c["chunk_id"] for c in notes][:4])

# every reason must actually contribute, not just the biggest one
for reason in ("cited_section", "note", "definition", "sibling_item"):
    assert r.debug["closure"].get(reason, 0) > 0, f"{reason} contributed nothing"
print("every closure reason contributed:", r.debug["closure"])

# ---- 3. definitions arrive for the terms the provisions use -------------
defs = [c for c in r.chunks if c.get("source") == "definition"]
print("\ndefinitions pulled in:", len(defs))
for d in defs[:4]:
    print("   ", d["chunk_id"], "|", d["text"][:70])
assert defs, "no definitions reached Kq"

# ---- 4. the budget is respected and split across reasons ----------------
small = ret.retrieve_for_compile("sign placement", closure_budget=8)
print("\nbudget 8 ->", small.debug["n_closure_chunks"], "closure chunks:", small.debug["closure"])
assert small.debug["n_closure_chunks"] <= 8
assert len(small.debug["closure"]) >= 3, "budget consumed by one reason"

# ---- 5. no duplicates between searched and closure ----------------------
allids = [c["chunk_id"] for c in r.chunks]
assert len(allids) == len(set(allids)), "Kq contains duplicates"
print("\nno duplicate chunks in Kq:", len(allids), "unique")
print("\nCOMPILE CLOSURE TESTS PASSED")
