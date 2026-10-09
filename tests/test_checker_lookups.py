"""The checker's labels, lookups and exception check (9 October 2026).

  1. Links read from the graph and the text: the exceptions a provision names
     (by section, by paragraph, by the graph's EXCEPTS links), an exception
     said to exist "otherwise" with no place named, what else it refers to,
     the Option paragraphs of its section, the defined terms it uses.
  2. Labels: section number and title, paragraph, item, heading; table rows,
     figure descriptions and notes say what they are.
  3. Lookups: open a section (paged), a paragraph with its neighbours, a table
     or figure (notes, rows, row filter), a definition, a search; errors are
     answers, not crashes; everything is logged; a piece shown twice is
     listed by id only.
  4. The conversation with the API (`ask.converse`): earlier turns are sent
     back exactly as returned (thinking blocks included), every tool_use gets
     its tool_result first in the next message, the tools never change, no
     tool_choice is sent, the first message and the last tool are marked for
     caching, the lookup limit is kept, an empty reply is nudged once, a
     follow-up is sent when asked, and a re-run replays from the reply cache.
  5. The checker: reading rules and lookup rules in the prompt, labelled
     evidence, the exceptions named by the pointed provisions added, the
     exception check after an answer (once), what it found by itself
     recorded, authority raised from a looked-up Standard, and the plain
     single-call path when the model offers no conversation.

Everything here is made up (sections 9Z, 9Y; panels; ids). No sample question,
gold answer or MUTCD text is used.
"""
import copy
import hashlib
import json
import os
import re
import pickle
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from mrag.kg_vine import VineKG
from mrag.vine import Authority, CertificateStore, Operation, Status
from mrag.vine.anthropic_client import LIMIT_NOTE, cost_usd, make_ask_anthropic
from mrag.vine.lookup import Lookups, ManualView
from mrag.vine.model_verifiers import (LOOKUP_RULES, READING_RULES, build_prompt,
                                       make_llm_verifier)
from mrag.vine.network import ObligationType

TMP = Path(tempfile.mkdtemp())


# --------------------------------------------------------------------------- #
# A made-up manual and its graph
# --------------------------------------------------------------------------- #
def chunk(cid, sec, kind, ordinal, text, title, **kw):
    d = {"chunk_id": cid, "section_id": sec, "section_title": title, "content_type": kind,
         "ordinal": ordinal, "text": text, "source": kw.pop("source", "paragraph"),
         "parent_id": kw.pop("parent_id", None), "item": kw.pop("item", None),
         "lead_in": kw.pop("lead_in", None), "authority_inferred": kw.pop("inferred", False),
         "figure_refs": kw.pop("figure_refs", []), "table_refs": kw.pop("table_refs", []),
         "section_refs": kw.pop("section_refs", [])}
    d.update(kw)
    return d


T1, T2, T0 = "Blue Panels", "Panel Exceptions", "Definitions"
CHUNKS = [
    chunk("Z02_Standard_01_item1", "9Z.02", "Standard", 1,
          "1. Panel Zone-the made-up strip beside a gravel lane.", T0,
          source="list_item", parent_id="Z02_P1", item="1",
          lead_in="The following words, when used here, shall have these meanings:"),
    chunk("Z01_Standard_01", "9Z.01", "Standard", 1,
          "Except as provided in Section 9Y.01, a blue panel shall be at least 7 feet high in a "
          "panel zone, as shown in Table 9Z-1.", T1, table_refs=["9Z-1"], section_refs=["9Y.01"]),
    chunk("Z01_Standard_02", "9Z.01", "Standard", 2,
          "Except as provided in Paragraphs 4 and 5 of this Section, a blue panel shall face east.",
          T1),
    chunk("Z01_Guidance_03", "9Z.01", "Guidance", 3,
          "Except as otherwise provided in this Manual, a blue panel should be square.", T1),
    chunk("Z01_Option_04", "9Z.01", "Option", 4, "A blue panel may face west near a park.", T1),
    chunk("Z01_Option_05", "9Z.01", "Option", 5, "A blue panel may face north on a bridge.", T1),
    chunk("Z01_Support_06", "9Z.01", "Support", 6,
          "Blue panels are described in Figure 9Z-2 (see Paragraph 2 in Section 9Y.01).", T1,
          figure_refs=["9Z-2"]),
    chunk("Z01_Standard_07", "9Z.01", "Standard", 7,
          "Except as otherwise provided in Table 9Z-1, a blue panel shall be lit.", T1,
          table_refs=["9Z-1"]),
    chunk("Y01_Standard_01", "9Y.01", "Standard", 1,
          "A blue panel on a bridge shall be at least 9 feet high.", T2),
    chunk("Y01_Standard_02", "9Y.01", "Standard", 2,
          "A blue panel shall not be used on a gravel lane near a school.", T2),
    chunk("TBLNOTE_9Z-1_01", "9Z.01", "Standard", 1,
          "Table 9Z-1. 1 The heights apply only to panels in a panel zone.", T1,
          source="table_note", parent_id="Table 9Z-1", item="1", inferred=True,
          table_refs=["9Z-1"]),
] + [chunk(f"Z01_Guidance_{n:02d}", "9Z.01", "Guidance", n, f"Made-up guidance line {n}.", T1)
     for n in range(8, 21)] + [
    chunk("Z01_Standard_21", "9Z.01", "Standard", 21,
          "Unless a blue panel is no longer serviceable (see definition in Section 9Y.01), it shall "
          "be kept.", T1),
    chunk("Z01_Standard_22", "9Z.01", "Standard", 22,
          "Except as provided in Sections 9X.01 through 9X.03, a blue panel shall be round.", T1),
    chunk("Z01_Standard_23", "9Z.01", "Standard", 23,
          "Except as provided in Section 9W.01, a blue panel shall be red.", T1),
    chunk("Z01_Standard_24", "9Z.01", "Standard", 24,
          "Unless provided otherwise elsewhere in this Manual, a blue panel shall be flat.", T1),
    chunk("Z01_Standard_25", "9Z.01", "Standard", 25,
          "Except as otherwise provided for temporary panels in Section 9Y.01, a panel shall be dry.", T1),
    chunk("Z01_Guidance_26", "9Z.01", "Guidance", 26,
          "Unless otherwise indicated by an engineering study, a panel should be blue.", T1),
    chunk("Z01_Standard_27", "9Z.01", "Standard", 27,
          "Unless specifically designated otherwise in this Manual or as provided in Paragraph 4 "
          "of this Section, a panel shall be square.", T1),
] + [chunk(f"X0{k}_Standard_01", f"9X.0{k}", "Standard", 1, f"Made-up rule {k} for round panels.",
           f"Round Panels {k}") for k in (1, 2, 3)] \
  + [chunk(f"W01_Standard_{n:02d}", "9W.01", "Standard", n, f"Made-up red panel rule {n}.", "Red Panels")
     for n in range(1, 11)] \
  + [chunk(f"Y02_Standard_01_item{k}", "9Y.02", "Standard", 1, f"{k}. " + "A made-up long item. " * 20,
           "Long List", source="list_item", parent_id="Y02_P1", item=str(k),
           lead_in="Panels shall meet the following:") for k in range(1, 61)]
ROWS = [{"chunk_id": f"vine:trow:Table 9Z-1#r{i}", "content_type": "TableRow", "section_id": "9Z.01",
         "section_title": T1, "ordinal": None, "source": "vine_graph", "table_refs": ["Table 9Z-1"],
         "graph_node": f"trow:Table 9Z-1#r{i}",
         "text": f"Table 9Z-1. Panel Heights. Panel: P{i}; Height: {6 + i} ft"} for i in range(1, 31)]
READING = {"chunk_id": "vine:reading:9Z-2#0:Figure 9Z-2", "content_type": "FigureReading",
           "section_id": "9Z.01", "source": "vine_graph", "figure_refs": ["Figure 9Z-2"],
           "graph_node": "reading:9Z-2#0", "text": "Figure 9Z-2 shows a square blue panel."}


def node(kind, section="", text="", pieces=()):
    return SimpleNamespace(kind=kind, section=section, text=text, authority=None, pieces=pieces)


N, E = {}, []
for c in CHUNKS:
    N[f"sent:{c['chunk_id']}#0"] = node("SENTENCE", c["section_id"], c["text"])
N["section:9Z.01"] = node("SECTION", "9Z.01", T1)
N["section:9Y.01"] = node("SECTION", "9Y.01", T2)
N["figure:Table 9Z-1"] = node("TABLE", "9Z.01", "Table 9Z-1. Panel Heights")
N["figure:Figure 9Z-2"] = node("FIGURE", "9Z.01", "Figure 9Z-2. Blue Panel")
N["reading:9Z-2#0"] = node("READING", "9Z.01", READING["text"])
N["term:panel zone"] = node("TERM", "", "panel zone")
for r in ROWS:
    N[r["graph_node"]] = node("TABLE_ROW", "9Z.01", r["text"], ("table=Table 9Z-1",))
    E.append(SimpleNamespace(src=r["graph_node"], rel="ROW_OF", dst="figure:Table 9Z-1", why=""))
E += [SimpleNamespace(src="sent:Z01_Standard_02#0", rel="EXCEPTS", dst="sent:Z01_Option_04#0", why="names 4"),
      SimpleNamespace(src="sent:Z01_Standard_01#0", rel="REFERS_TO", dst="figure:Table 9Z-1", why=""),
      SimpleNamespace(src="sent:Z01_Standard_01#0", rel="REFERS_TO", dst="section:9Y.01", why=""),
      SimpleNamespace(src="sent:Z01_Standard_01#0", rel="USES_TERM", dst="term:panel zone", why=""),
      SimpleNamespace(src="sent:TBLNOTE_9Z-1_01#0", rel="NOTE_OF", dst="figure:Table 9Z-1", why=""),
      SimpleNamespace(src="figure:Figure 9Z-2", rel="HAS_READING", dst="reading:9Z-2#0", why="")]
GRAPH = TMP / "graph.pkl"
pickle.dump((N, E, CHUNKS), open(GRAPH, "wb"))
ITEMS = TMP / "items.jsonl"
ITEMS.write_text("\n".join(json.dumps(x) for x in ROWS + [READING]))
kg = VineKG(GRAPH, items_path=ITEMS)
BY_ID = {c["chunk_id"]: c for c in CHUNKS + ROWS + [READING]}


class Store:
    def fetch_chunks_by_ids(self, name, ids, default_score=0.0):
        return [{"payload": BY_ID[i], "score": default_score} for i in ids if i in BY_ID]


def search(query):
    words = set(query.lower().split())
    scored = sorted(CHUNKS, key=lambda c: -len(words & set(c["text"].lower().split())))
    return scored[:3]


view = ManualView(kg, Store(), "chunks", search=search)

# ---- 1. links ---------------------------------------------------------------------
L1 = view.links(BY_ID["Z01_Standard_01"])
assert "Section 9Y.01" in L1.exceptions, L1
assert "Table 9Z-1" not in L1.exceptions, "a comma ends the exception clause"
assert "Table 9Z-1" in L1.refers_to and "Section 9Y.01" not in L1.refers_to, L1
assert L1.exception_ids[:2] == ["Y01_Standard_01", "Y01_Standard_02"], L1.exception_ids
assert L1.options_here == [4, 5], "1C.01: Options of the same section are listed for a Standard"
assert L1.terms == ["panel zone"], L1.terms
assert "Table 9Z-1" in L1.notes_of, "1A.04 P5: a table it names has notes"

L2 = view.links(BY_ID["Z01_Standard_02"])
assert L2.exceptions[:2] == ["Section 9Z.01 paragraph 4", "Section 9Z.01 paragraph 5"], L2.exceptions
assert L2.exception_ids == ["Z01_Option_04", "Z01_Option_05"], L2.exception_ids

L3 = view.links(BY_ID["Z01_Guidance_03"])
assert L3.open_exception == "except as otherwise provided in this manual", L3
assert not L3.exceptions
L7 = view.links(BY_ID["Z01_Standard_07"])
assert not L7.open_exception, "an 'otherwise' that names a table is not open-ended"
L6 = view.links(BY_ID["Z01_Support_06"])
assert "Section 9Y.01 paragraph 2" in L6.refers_to and not L6.exceptions and not L6.options_here
assert view.links(BY_ID["Z01_Option_04"]).options_here == [], "Options only for Standard/Guidance"
assert view.named_exception_ids([BY_ID["Z01_Standard_02"], BY_ID["Z01_Standard_01"]]) == \
    ["Z01_Option_04", "Z01_Option_05", "Y01_Standard_01", "Y01_Standard_02"]
L21 = view.links(BY_ID["Z01_Standard_21"])
assert not L21.exceptions and not L21.exception_ids and "Section 9Y.01" in L21.refers_to, \
    "a reference in parentheses inside an 'unless' clause is a reference, not an exception"
L22 = view.links(BY_ID["Z01_Standard_22"])
assert L22.exceptions == ["Section 9X.01", "Section 9X.02", "Section 9X.03"], L22.exceptions
assert L22.exception_ids == ["X01_Standard_01", "X02_Standard_01", "X03_Standard_01"]
L23 = view.links(BY_ID["Z01_Standard_23"])
assert L23.exceptions == ["Section 9W.01"] and L23.long_exception_sections == ["9W.01"]
assert not L23.exception_ids, "a long section named whole is named, not handed over in part"
assert view.links(BY_ID["Z01_Standard_24"]).open_exception.startswith("unless provided otherwise")
assert not view.links(BY_ID["Z01_Standard_25"]).open_exception, "it names a section"
assert not view.links(BY_ID["Z01_Guidance_26"]).open_exception, "an engineering study is no provision"
L27 = view.links(BY_ID["Z01_Standard_27"])
assert L27.open_exception.startswith("unless specifically designated otherwise"), L27
assert L27.exceptions == ["Section 9Z.01 paragraph 4"], "both parts of one clause are read"
retagged = {**BY_ID["TBLNOTE_9Z-1_01"], "source": "obligation_pointer"}
assert view.header(retagged).startswith("[TBLNOTE_9Z-1_01] note 1 to Table 9Z-1"), \
    "the graph's record decides what a piece is, not a re-tagged copy"
print("1. links: exceptions by section, paragraph, range and graph; references in parentheses; "
      "long sections; open-ended exceptions; options; terms")

# ---- 2. labels --------------------------------------------------------------------
lab = view.label(BY_ID["Z01_Standard_01"])
assert lab.startswith('[Z01_Standard_01] Section 9Z.01 "Blue Panels" · paragraph 1 · Standard'), lab
assert "exceptions it names: Section 9Y.01" in lab and "Option paragraphs in this section: 4, 5" in lab
assert "item 1" in view.header(BY_ID["Z02_Standard_01_item1"])
assert "TABLE ROW of Table 9Z-1" in view.header(ROWS[0])
assert "FIGURE DESCRIPTION of Figure 9Z-2" in view.header(READING)
note = view.header(BY_ID["TBLNOTE_9Z-1_01"])
assert note.startswith("[TBLNOTE_9Z-1_01] note 1 to Table 9Z-1") and "heading inferred" in note, note
assert "(information only)" in view.header(BY_ID["Z01_Support_06"])
print("2. labels: section, title, paragraph, item, heading; rows, readings and notes say what they are")

# ---- 3. lookups -------------------------------------------------------------------
lk = Lookups(view, max_lookups=5)
txt, err = lk.run("open_section", {"section": "9Z.01"})
assert not err and "showing paragraphs 1 to 10" in txt and "from_paragraph=11" in txt, txt[:300]
txt, err = lk.run("open_section", {"section": "Section 9z.01", "from_paragraph": 26})
assert not err and lk.log[-1]["section"] == "9Z.01", "the section id is logged in one form"
assert "TBLNOTE" not in txt, "notes are not paragraphs of the section"
txt, err = lk.run("open_section", {"section": "9Z.01", "from_paragraph": 11})
assert "[Z01_Guidance_11]" in txt and "[Z01_Standard_01]" not in txt
txt, err = lk.run("open_paragraph", {"section": "9Z.01", "paragraph": 2})
assert "(already shown above)" in txt and txt.count("[Z01_") == 3, txt
txt, err = lk.run("open_paragraph", {"section": "9Z.01", "paragraph": 99})
assert err and "no paragraph 99" in txt
txt, err = lk.run("open_section", {"section": "1Q.77"})
assert err and "no Section" in txt
txt, err = lk.run("bogus_tool", {})
assert err
txt, err = lk.run("open_paragraph", {"section": "9Z.01"})
assert err and "does not fit" in txt
lk3 = Lookups(view)
lk3.show([{**BY_ID["TBLNOTE_9Z-1_01"], "source": "established_evidence_note"}])
txt, err = lk3.run("open_section", {"section": "9Z.01"})
assert "TBLNOTE" not in txt and "27 paragraphs" in txt, "a re-tagged note is still not a paragraph"
txt, err = lk3.run("open_paragraph", {"section": "9Y.02", "paragraph": 1})
assert not err and len(txt) < 13000 and "60 list items" in txt and "from_item=" in txt, txt[:300]
k = int(re.search(r"from_item=(\d+)", txt).group(1))
txt2, err = lk3.run("open_paragraph", {"section": "9Y.02", "paragraph": 1, "from_item": k})
assert f"[Y02_Standard_01_item{k}]" in txt2 and "[Y02_Standard_01_item1]" not in txt2
txt, err = Lookups(view).run("open_section", {"section": "9Y.02"})
assert "continues: open_paragraph" in txt and len(txt) < 13000, txt[:300]
lk2 = Lookups(view)
txt, err = lk2.run("open_table_or_figure", {"id": "Table 9Z-1"})
assert not err and "30 rows, showing 1 to 20" in txt and "from_row=21" in txt and "[TBLNOTE_9Z-1_01]" in txt
assert "[vine:trow:Table 9Z-1#r1] Panel: P1; Height: 7 ft" in txt, "rows are compact, caption removed"
txt, err = lk2.run("open_table_or_figure", {"id": "Table 9Z-1", "row_contains": "P17"})
assert "1 contain 'P17'" in txt and "#r17]" in txt and "#r16]" not in txt, txt[:400]
txt, err = lk2.run("open_table_or_figure", {"id": "Table 9Z-1", "from_row": 40})
assert "none from row 40 on" in txt
txt, err = lk2.run("open_table_or_figure", {"id": "Figure 9Z-2"})
assert "FIGURE DESCRIPTION" in txt
txt, err = lk2.run("define_term", {"term": "Panel Zone"})
assert not err and "[Z02_Standard_01_item1]" in txt
txt, err = lk2.run("define_term", {"term": "zone"})
assert err and '"panel zone"' in txt, "close defined terms are offered"
txt, err = lk2.run("search_manual", {"query": "blue panel bridge"})
assert not err and "[Y01_Standard_01]" in txt
assert lk2.used == 7 and all("returned" in e and "new" in e for e in lk2.log)
assert [s["name"] for s in Lookups(ManualView(kg, Store(), "chunks")).specs()] == \
    ["open_section", "open_paragraph", "open_table_or_figure", "define_term"], "no search without one"
# search results are saved by query, so a replay sees the same pieces
from mrag.vine.lookup import _make_search
order = {"ids": ["Z01_Standard_01", "Y01_Standard_01"]}
fake_ret = SimpleNamespace(
    text=SimpleNamespace(encode_both=lambda qs: (list(qs), [{}])),
    store=SimpleNamespace(search_chunks_hybrid=lambda coll, d, sp, top_k=30:
                          [{"payload": BY_ID[i]} for i in order["ids"]],
                          fetch_chunks_by_ids=Store().fetch_chunks_by_ids),
    rerank=None)
sv = ManualView(kg, Store(), "chunks")
sv.search = _make_search(fake_ret, "chunks", sv, str(TMP / "cache_s"))
first = [p["chunk_id"] for p in sv.search("blue panel")]
order["ids"] = ["Y01_Standard_02"]                    # the search would now rank differently
assert [p["chunk_id"] for p in sv.search("blue panel")] == first, "replayed from the saved ids"
assert [p["chunk_id"] for p in sv.search("another query")] == ["Y01_Standard_02"]
print("3. lookups: paging by size, long paragraphs, neighbours, rows and row filter, definitions, "
      "search (saved by query), errors, log")


# --------------------------------------------------------------------------- #
# 4. The conversation with the API, against a strict stand-in
# --------------------------------------------------------------------------- #
class FakeAPI:
    """Replies by a script; checks the client keeps the API's rules."""

    def __init__(self, script):
        self.script = list(script)       # each: list of content blocks, stop_reason
        self.returned = []
        self.bodies = []
        self.tools_sha = None

    def __call__(self, sess, url, headers=None, json=None, timeout=None):
        body = copy.deepcopy(json)       # as sent: the client's lists grow afterwards
        self.bodies.append(body)
        assert "tool_choice" not in body and "thinking" not in body and "temperature" not in body
        msgs = body["messages"]
        assert msgs[0]["content"][-1].get("cache_control") == {"type": "ephemeral"}
        if body.get("tools"):
            assert body["tools"][-1].get("cache_control") == {"type": "ephemeral"}
            sha = hashlib.sha256(repr(body["tools"]).encode()).hexdigest()
            assert self.tools_sha in (None, sha), "tools changed"
            self.tools_sha = sha
        for k, m in enumerate(msgs):
            if m["role"] == "assistant":
                assert m["content"] in self.returned, "an assistant turn was changed"
                assert any(b.get("type") in ("text", "tool_use") for b in m["content"]), \
                    "an empty reply was sent back"
                uses = [b["id"] for b in m["content"] if b.get("type") == "tool_use"]
                if uses:
                    nxt = msgs[k + 1]["content"]
                    assert [b["type"] for b in nxt[:len(uses)]] == ["tool_result"] * len(uses)
                    assert [b["tool_use_id"] for b in nxt[:len(uses)]] == uses
        content, stop = self.script.pop(0)
        self.returned.append(content)
        r = SimpleNamespace(status_code=200, headers={"request-id": "req_t"}, text="")
        r.json = lambda: {"model": body["model"], "stop_reason": stop, "content": content,
                          "usage": {"input_tokens": 100, "cache_creation_input_tokens": 1000,
                                    "cache_read_input_tokens": 2000, "output_tokens": 50}}
        return r


def think(n):
    return {"type": "thinking", "thinking": "", "signature": f"sig{n}"}


def use(i, name, args):
    return {"type": "tool_use", "id": f"toolu_{i}", "name": name, "input": args}


def text(s):
    return {"type": "text", "text": s}


os.environ["ANTHROPIC_API_KEY"] = "test"
calls_seen = []


def tool(name, args):
    calls_seen.append(name)
    return f"result of {name}", False


fake = FakeAPI([
    ([think(1), use(1, "open_section", {"section": "9Z.01"}),
      use(2, "define_term", {"term": "panel zone"})], "tool_use"),
    ([think(2), use(3, "open_paragraph", {"section": "9Z.01", "paragraph": 2})], "tool_use"),
    ([think(3)], "end_turn"),                                     # empty: nudged once
    ([think(4), text('{"status": "TRUE", "evidence": ["x"]}')], "end_turn"),
    ([think(5), text('{"status": "FALSE", "evidence": ["x"]}')], "end_turn"),
])
requests.Session.post = lambda sess, url, **kw: fake(sess, url, **kw)
cache = TMP / "cache_a"
ask = make_ask_anthropic("claude-sonnet-5-5", cache_dir=str(cache), say=lambda *_: None)
asked = []


def follow(t):
    asked.append(t)
    return "read this exception too" if len(asked) == 1 else None


out, tr = ask.converse("PROMPT ONE", [], [{"name": "open_section", "description": "d",
                                           "input_schema": {"type": "object"}}],
                       tool, max_lookups=12, after_answer=follow)
assert out == '{"status": "FALSE", "evidence": ["x"]}', out
assert calls_seen == ["open_section", "define_term", "open_paragraph"]
assert tr["turns"] == 5 and tr["lookups"] == 3 and tr["nudged"] and tr["follow_ups"] == 1, tr
nudge_req = fake.bodies[3]["messages"]
assert nudge_req[-2]["role"] == "user" and nudge_req[-2]["content"][0]["type"] == "tool_result"
assert nudge_req[-1]["role"] == "user" and nudge_req[-1]["content"][0]["type"] == "text", \
    "the empty reply is not sent back; a new user message asks"
last = fake.bodies[-1]["messages"]
assert last[-1]["content"][0]["text"] == "read this exception too"
assert len(list(cache.glob("*.json"))) == 5
cost = cost_usd(ask.calls)
assert abs(cost - 5 * (100 * 2 + 1000 * 2.5 + 2000 * 0.10 + 50 * 10) / 1e6) < 1e-9, cost

# replay from the reply cache: no API call at all
requests.Session.post = lambda *a, **k: (_ for _ in ()).throw(AssertionError("API called"))
calls_seen.clear()
asked.clear()
ask2 = make_ask_anthropic("claude-sonnet-5-5", cache_dir=str(cache), cache_only=True)
out2, tr2 = ask2.converse("PROMPT ONE", [], [{"name": "open_section", "description": "d",
                                              "input_schema": {"type": "object"}}],
                          tool, max_lookups=12, after_answer=follow)
assert out2 == out and all(c["cached"] for c in ask2.calls) and len(ask2.calls) == 5
assert cost_usd(ask2.calls) == 0.0

# the limit: refused lookups get the note; asking on and on stops the conversation
fake2 = FakeAPI([([think(i), use(i, "open_section", {"section": "9Z.01"})], "tool_use")
                 for i in range(10)])
requests.Session.post = lambda sess, url, **kw: fake2(sess, url, **kw)
ask3 = make_ask_anthropic("claude-sonnet-5-5", cache_dir=None, say=lambda *_: None)
out3, tr3 = ask3.converse("PROMPT TWO", [], [{"name": "open_section", "description": "d",
                                              "input_schema": {"type": "object"}}],
                          tool, max_lookups=2)
assert out3 == "" and tr3["stopped"] == "kept asking for lookups after the limit", tr3
assert tr3["lookups"] == 2 and tr3["refused_lookups"] == 3
refused = fake2.bodies[3]["messages"][-1]["content"][0]
assert refused["is_error"] is True and refused["content"] == LIMIT_NOTE
# the stop reason comes first: refusal, a cut-off tool call, the context window
for stop, blocks, want in [
        ("refusal", [think(1), text('{"status": "FALSE", "evidence": ["x"]}')], ""),
        ("max_tokens", [think(1), use(9, "open_section", {"sect": "9Z"})], ""),
        ("model_context_window_exceeded", [think(1), text('{"status": "TRUE"')], "")]:
    fk = FakeAPI([(blocks, stop)])
    requests.Session.post = lambda sess, url, fk=fk, **kw: fk(sess, url, **kw)
    calls_seen.clear()
    a = make_ask_anthropic("claude-sonnet-5-5", cache_dir=None, say=lambda *_: None)
    o, t = a.converse("PROMPT THREE", [], [{"name": "open_section", "description": "d",
                                            "input_schema": {"type": "object"}}], tool)
    assert o == want and t["stopped"] == stop and not calls_seen, (stop, o, t)
# two empty replies in a row: no answer
fk = FakeAPI([([think(1)], "end_turn"), ([], "end_turn")])
requests.Session.post = lambda sess, url, **kw: fk(sess, url, **kw)
o, t = make_ask_anthropic("claude-sonnet-5-5", cache_dir=None).converse("PROMPT FOUR", [], [], tool)
assert o == "" and t["stopped"] == "empty reply" and t["nudged"]
print("4. conversation: turns echoed, results first, tools fixed, caching marks, limit, nudge "
      "without sending the empty reply back, stop reasons, follow-up, replay from cache, "
      "cost with cache tokens")


# --------------------------------------------------------------------------- #
# 5. The checker with lookups
# --------------------------------------------------------------------------- #
class Retriever:
    def __init__(self):
        self.kg = kg
        self.store = Store()
        self.text = None
        self.rerank = None

    def retrieve_for_obligation(self, query, claim, certificates=None, top_k=None):
        return SimpleNamespace(chunks=[BY_ID["Z01_Support_06"]], figures=[], debug={})


def op_of(claim, source="Z01_Standard_02", authority=Authority.GUIDANCE):
    return Operation(id="o1", claim=claim, produces="s_o1", verifier="llm",
                     obligation_type=ObligationType.EXCEPTION, normative_authority=authority,
                     source_chunk=source, evidence_hint=[])


class ScriptAsk:
    """A model function with `converse`, answering from a script of decisions."""

    def __init__(self, plan):
        self.plan = plan
        self.prompts = []
        self.calls = []

    def __call__(self, prompt, images=None):
        self.prompts.append(prompt)
        return json.dumps({"status": "TRUE", "evidence": ["Z01_Standard_02"],
                           "basis": "Z01_Standard_02", "confidence": 0.9, "reason": "plain"})

    def converse(self, prompt, images, tools, call_tool, max_lookups=12, after_answer=None):
        self.prompts.append(prompt)
        self.tools = [t["name"] for t in tools]
        self.results = [call_tool(n, a) for n, a in self.plan.get("lookups", [])]
        replies = list(self.plan["replies"])
        self.follow = []
        while True:
            r = json.dumps(replies.pop(0))
            more = after_answer(r) if after_answer else None
            if more and replies:
                self.follow.append(more)
                continue
            return r, {"turns": 2, "lookups": len(self.results), "refused_lookups": 0,
                       "follow_ups": len(self.follow), "nudged": False, "stopped": ""}


# (a) the prompt: rules, labels, the named exceptions of the pointed provision
sa = ScriptAsk({"replies": [{"status": "UNKNOWN", "evidence": [], "reason": "x"}]})
v = make_llm_verifier(sa, Retriever(), max_lookups=7)
cert = v(op_of("Panel P faces east as the manual requires for this case."), CertificateStore())
p = sa.prompts[0]
assert READING_RULES in p and "At most 7" in p and "LOOKING FURTHER" in p
assert "and search_manual" not in p, "no search offered when the retriever cannot search"
assert '[Z01_Standard_02] Section 9Z.01 "Blue Panels" · paragraph 2 · Standard' in p
assert "[Z01_Option_04]" in p and "[Z01_Option_05]" in p, "named exceptions were added"
assert p.index("[Z01_Option_04]") < p.index("[Z01_Support_06]"), "before what the search added"
assert p.rstrip().endswith("Panel P faces east as the manual requires for this case."), \
    "the claim is repeated at the end"
assert cert.provenance["named_exceptions"] == ["Z01_Option_04", "Z01_Option_05"]
assert cert.provenance["lookups_used"] == 0 and sa.tools[0] == "open_section"

# (b) the exception check: an answer resting on Z01_Standard_01, whose named
#     exception (9Y.01) was never read, is sent back once with it; the second
#     answer cites the exception, found by the checker, and FALSE rests on a
#     Standard so the Guidance-labelled check carries Standard.
sa = ScriptAsk({"lookups": [("open_paragraph", {"section": "9Z.01", "paragraph": 1})],
                "replies": [
                    {"status": "TRUE", "evidence": ["Z01_Standard_01"], "basis": "Z01_Standard_01",
                     "confidence": 0.8, "reason": "first"},
                    {"status": "FALSE", "evidence": ["Y01_Standard_02", "Z01_Standard_01"],
                     "basis": "Y01_Standard_02", "confidence": 0.9, "reason": "the exception"}]})
v = make_llm_verifier(sa, Retriever())
cert = v(op_of("Panel P on a gravel lane near a school is allowed here."), CertificateStore())
assert len(sa.follow) == 1 and "[Y01_Standard_02]" in sa.follow[0], sa.follow
assert cert.status is Status.FALSE and cert.provenance["handed_over_exceptions"][:2] == \
    ["Y01_Standard_01", "Y01_Standard_02"]
assert cert.provenance["cited_handed_over_exceptions"] == ["Y01_Standard_02"]
assert cert.provenance["first_answer"] == "TRUE", "the answer before the exceptions is kept"
assert cert.provenance["found_by_checker"] == ["Z01_Standard_01"], "found by its own lookup"
assert cert.normative_authority is Authority.STANDARD
assert cert.provenance["authority_from"]["basis"] == "Y01_Standard_02"
assert [e.id for e in cert.evidence] == ["Y01_Standard_02", "Z01_Standard_01"]
assert cert.provenance["lookups"][0]["tool"] == "open_paragraph"

# (c) an open-ended exception: asked once to look for the specific provision
sa = ScriptAsk({"lookups": [("open_paragraph", {"section": "9Z.01", "paragraph": 3})],
                "replies": [
                    {"status": "TRUE", "evidence": ["Z01_Guidance_03"], "basis": "Z01_Guidance_03",
                     "confidence": 0.8, "reason": "first"},
                    {"status": "TRUE", "evidence": ["Z01_Guidance_03"], "basis": "Z01_Guidance_03",
                     "confidence": 0.8, "reason": "looked, nothing else"}]})
v = make_llm_verifier(sa, Retriever())
cert = v(op_of("Panel P is square as the manual recommends."), CertificateStore())
assert len(sa.follow) == 1 and "except as otherwise provided" in sa.follow[0]
assert cert.provenance["asked_to_look_for_specific_provision"] == ["Z01_Guidance_03"]
assert cert.status is Status.TRUE

# (c2) a long section named whole as an exception: asked to open it
sa = ScriptAsk({"lookups": [("open_paragraph", {"section": "9Z.01", "paragraph": 23})],
                "replies": [
                    {"status": "TRUE", "evidence": ["Z01_Standard_23"], "basis": "Z01_Standard_23",
                     "confidence": 0.8, "reason": "first"},
                    {"status": "TRUE", "evidence": ["Z01_Standard_23"], "basis": "Z01_Standard_23",
                     "confidence": 0.8, "reason": "second"}]})
v = make_llm_verifier(sa, Retriever())
cert = v(op_of("Panel P is red as required."), CertificateStore())
assert len(sa.follow) == 1 and "Section 9W.01" in sa.follow[0], sa.follow
assert cert.provenance["asked_to_open_sections"] == ["9W.01"]
assert "search_manual" not in sa.follow[0], "search is not offered when there is none"

# (d) an UNKNOWN is never sent back; a cited id never shown is dropped
sa = ScriptAsk({"replies": [{"status": "UNKNOWN", "evidence": ["Q99_Made_Up"], "reason": "no"},
                            {"status": "TRUE", "evidence": [], "reason": "never asked"}]})
v = make_llm_verifier(sa, Retriever())
cert = v(op_of("Panel P faces east."), CertificateStore())
assert not sa.follow and cert.status is Status.UNKNOWN
assert cert.provenance["fabricated_evidence_ids"] == ["Q99_Made_Up"]

# (e) without `converse`, or with max_lookups=0: one call, labels, no lookup rules
class PlainAsk(ScriptAsk):
    converse = None


pa = PlainAsk({})
v = make_llm_verifier(pa, Retriever())
cert = v(op_of("Panel P faces east."), CertificateStore())
assert cert.status is Status.TRUE and "LOOKING FURTHER" not in pa.prompts[0]
assert READING_RULES in pa.prompts[0] and "· paragraph 2 · Standard" in pa.prompts[0]
assert "lookups" not in cert.provenance
sa = ScriptAsk({"replies": [{"status": "UNKNOWN", "evidence": [], "reason": "x"}]})
v = make_llm_verifier(sa, Retriever(), max_lookups=0)
v(op_of("Panel P faces east."), CertificateStore())
assert "LOOKING FURTHER" not in sa.prompts[0] and not hasattr(sa, "tools")

# (f) without the VINE graph: the plain evidence form, as before
plain_prompt, allowed = build_prompt(op_of("Panel P faces east."), [BY_ID["Z01_Standard_02"]], [])
assert "[Z01_Standard_02] (9Z.01 Standard)" in plain_prompt and allowed == ["Z01_Standard_02"]
assert READING_RULES in plain_prompt and LOOKUP_RULES.split("\n")[0] not in plain_prompt
print("5. checker: rules and labels in the prompt, named exceptions added, exception check once, "
      "open-ended exceptions, found-by-checker, authority from a looked-up Standard, plain path")

print("\nALL CHECKER LOOKUP TESTS PASSED")
