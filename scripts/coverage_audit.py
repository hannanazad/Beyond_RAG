"""How much of the MUTCD ends up in chunks, measured against the MANUAL.

Two passes:
  A. body text (Times font), by area of the manual
  B. text printed inside figure/table crops (non-Times), which should appear
     only as note chunks -- cells and panel labels are deliberately excluded

usage: python coverage_audit.py <repo_root> <mutcd.pdf> <figures.jsonl>
"""
import sys, re, json, collections
sys.path.insert(0, sys.argv[1])
import pymupdf
from mrag import parsing as P, sign_codes as SC

pdf, figs_path = sys.argv[2], sys.argv[3]
figures = [json.loads(l) for l in open(figs_path) if l.strip()]
chunks = P.parse_chunks(pdf, sign_code_re=SC.get_sign_code_re(), figures=figures)
doc = pymupdf.open(pdf); toc = doc.get_toc()
norm = lambda t: re.sub(r"\s+", " ", t.translate({0x2010: 45, 0x2011: 45, 0x2012: 45,
                                                  0x2013: 45, 0x2014: 45})).strip()
blob = " || ".join(norm(c.text) for c in chunks)

body_start = min(p for l, t, p in toc if l == 1 and t.upper().startswith("PART 1"))
app_start = min(p for l, t, p in toc if l == 1 and t.lower().startswith("appendi"))
notes_pg = {p for l, t, p in toc if l == 3 and t.strip().startswith("Notes for Figure")}
def area(p):
    if p < body_start: return "front matter"
    if p >= app_start: return "appendices"
    return "Part 6 figure-notes pages" if p in notes_pg else "main body"

crop_by_page = collections.defaultdict(list)
for f in figures: crop_by_page[f["page_pdf"]].append(f)
def in_crop(p, bb):
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    for f in crop_by_page.get(p, []):
        x0, y0, x1, y1 = f["bbox"]
        if x0 <= cx <= x1 and y0 <= cy <= y1: return f
    return None

tot = collections.Counter(); miss = collections.Counter(); head = collections.Counter()
ctot = collections.Counter(); cmiss = collections.Counter()
for pno in range(1, doc.page_count + 1):
    page = doc.load_page(pno - 1); h = page.rect.height
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0: continue
        for ln in b["lines"]:
            t = norm("".join(s["text"] for s in ln["spans"]))
            sp = max(ln["spans"], key=lambda s: len(s["text"]))
            if len(t) < 25 or ln["bbox"][3] < 0.06 * h or ln["bbox"][1] > 0.935 * h: continue
            if sp["font"].startswith("Times"):
                a = area(pno); tot[a] += len(t)
                if t[:40] not in blob:
                    (head if (sp["font"] == "Times-Bold" and sp["size"] > 11.5) else miss)[a] += len(t)
            else:
                f = in_crop(pno, ln["bbox"])
                if not f: continue
                k = f["kind"]; ctot[k] += len(t)
                if t[:40] not in blob: cmiss[k] += len(t)

print(f"chunks: {len(chunks)}")
print("by source:", dict(collections.Counter(c.source for c in chunks)))
print("\nA. body text (Times):")
for a in tot:
    print(f"   {a:<28} {tot[a]:>9} chars | headings kept as titles {head[a]:>7} | other missing {miss[a]:>8} ({100*miss[a]/tot[a]:.2f}%)")
print("\nB. text inside crops (non-Times; only marked notes are kept on purpose):")
for k in ctot:
    print(f"   {k:<28} {ctot[k]:>9} chars | not in any chunk {cmiss[k]:>8} ({100*cmiss[k]/ctot[k]:.1f}%)")
