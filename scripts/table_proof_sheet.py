"""Render a transcribed table beside the page it came from, for checking.

A transcription that validates cleanly can still be WRONG: "W*; G >= 7" read
as "W >= 7" passes every structural check and puts the number on the wrong
variable. Only a human comparing the two can catch that, so this puts the
source render and the transcription side by side in reading order rather than
leaving someone to diff JSON against an image.

usage: python scripts/table_proof_sheet.py <tables.jsonl> <mutcd.pdf> <figures.jsonl> <out_dir>
"""
import html
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mrag.vine.table_data import load                      # noqa: E402

CSS = """
body{font:13px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f4f4f4}
h2{margin:0 0 4px;font-size:16px}
.meta{color:#555;margin-bottom:10px}
.warn{background:#fff3cd;border-left:4px solid #e0a800;padding:6px 10px;margin:8px 0}
.pair{display:flex;gap:14px;align-items:flex-start;background:#fff;padding:14px;
      margin:14px;border:1px solid #ddd;border-radius:6px}
.pair>div{flex:1;min-width:0}
img{max-width:100%;border:1px solid #999}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{border:1px solid #bbb;padding:3px 5px;vertical-align:top}
th{background:#eee;text-align:left}
.q{color:#0a5;font-weight:600}
.fn{color:#a00;font-size:10px;vertical-align:super}
.missing{color:#888;font-style:italic}
.notes{margin-top:8px;font-size:12px}
.notes li{margin-bottom:3px}
"""


def cell_html(c) -> str:
    if c.missing:
        body = f'<span class="missing">{html.escape(c.text or c.missing)}</span>'
    else:
        body = html.escape(c.text)
    if c.quantities:
        qs = "; ".join(f"{q.name} {q.comparator} {q.value}"
                       + (f" {q.unit}" if q.unit else "") for q in c.quantities)
        body += f'<br><span class="q">{html.escape(qs)}</span>'
    elif c.number is not None:
        body += f'<br><span class="q">{c.number}{" " + c.unit if c.unit else ""}</span>'
    elif c.minimum is not None or c.maximum is not None:
        lo = "" if c.minimum is None else f"{c.minimum} &le; "
        hi = "" if c.maximum is None else f" &le; {c.maximum}"
        body += f'<br><span class="q">{lo}x{hi}{" " + c.unit if c.unit else ""}</span>'
    elif c.formula:
        body += f'<br><span class="q">{html.escape(c.formula)}</span>'
    for m in c.footnotes:
        body += f'<span class="fn">{html.escape(m)}</span>'
    return body


def main(tables_path, pdf_path, figures_path, out_dir):
    import pymupdf
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    crops = {os.path.basename(c["image_path"]): c
             for c in map(json.loads, Path(figures_path).read_text().splitlines())
             if c.get("kind") == "Table"}
    # a crop whose filename lacks the sheet suffix is still findable by page
    by_page = {}
    for name, c in crops.items():
        by_page.setdefault((c["figure_id"], c["page_pdf"]), c)

    parts = [f"<style>{CSS}</style>"]
    for t in load(tables_path):
        crop = crops.get(t.crop_file) or by_page.get((t.table_id, t.page_pdf))
        img_name = ""
        if crop:
            x0, y0, x1, y1 = crop["bbox"]
            pix = doc.load_page(t.page_pdf - 1).get_pixmap(
                dpi=200, clip=pymupdf.Rect(max(0, x0 - 6), max(0, y0 - 6), x1 + 6, y1 + 6))
            img_name = f"{t.table_id.replace(' ', '_')}_s{t.sheet or 0}.png"
            pix.save(out / img_name)

        head = "".join(f"<th>{html.escape(l)}</th>" for l in t.column_labels)
        body = "".join("<tr>" + "".join(f"<td>{cell_html(c)}</td>" for c in row) + "</tr>"
                       for row in t.rows)
        notes = "".join(f"<li><b>{html.escape(n.marker)}</b> {html.escape(n.text)}"
                        + (f" <i>[{n.chunk_id}]</i>" if n.chunk_id else "") + "</li>"
                        for n in t.footnotes)
        warn = "" if t.verified else ('<div class="warn">Not yet checked by a human. '
                                      'Compare every number against the render on the left.</div>')
        parts.append(f"""
<div class="pair">
  <div>
    <h2>{html.escape(t.table_id)}{f' — sheet {t.sheet}' if t.sheet else ''}</h2>
    <div class="meta">page {t.page_pdf} (printed {html.escape(t.page_printed)}) ·
        {html.escape(t.kind)} · {len(t.rows)} rows × {len(t.column_labels)} cols</div>
    {f'<img src="{img_name}">' if img_name else '<i>no crop found</i>'}
  </div>
  <div>
    <h2>{html.escape(t.title)}</h2>
    {warn}
    <table><tr>{head}</tr>{body}</table>
    {f'<div class="notes"><b>Footnotes</b><ul>{notes}</ul></div>' if notes else ''}
  </div>
</div>""")
    (out / "proof_sheet.html").write_text("\n".join(parts), encoding="utf-8")
    print(f"proof sheet -> {out/'proof_sheet.html'}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
