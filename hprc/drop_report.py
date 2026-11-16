"""Drop report: for every question of a VINE run, every Standard, Guidance and
Option the parser was shown, and what happened to it at each later stage.

It only READS files. It does not change the pipeline, does not call any model,
does not need a GPU, and does not use any gold answer. Plain Python 3, standard
library only.

For each provision shown to the parser it says what the parser did with it:
  CHECKED        a check rests on it (its source_chunk is this provision, or a
                 check named for it in the plan's "provisions" account rests on
                 it, or, for a whole paragraph, a check's evidence hint names
                 that section and paragraph);
  SET ASIDE      the plan's account calls it "not related", with a reason;
  ADDED BY CODE  the parser left it out and the code added a plain check for it;
  LEFT OUT       the parser left it out, and the code added no check because a
                 check rests on ANOTHER item of the same paragraph;
  NOT ACCOUNTED  none of these (should not happen when the plan is valid; also
                 shown for every provision of a question whose plan failed).
and, for the checks that rest on it: each result (TRUE, FALSE, UNKNOWN, ...),
the checker's reason when UNKNOWN, whether a check counts in the final decision
(reached from the plan's terminal through merge inputs, requirements and
guards), and whether the answer cites the provision (its own id, or for a list
item the id of its paragraph).

What it CANNOT show: a provision that retrieval never found. It was never shown
to the parser, so nothing records it. The question summary lists every section
that was shown, so a reader can see whether a section the question needs is
missing altogether.

usage:
  python3 drop_report.py RUN_FILE OUT_DIR --kq KQ_FILE
  python3 drop_report.py RUN_FILE OUT_DIR --chunks CHUNKS_JSONL [VINE_ITEMS_JSONL]

  RUN_FILE  the vine_run_*.json written by the execute stage
  OUT_DIR   a folder for the report (made if missing)
  --kq      the Kq file the plans were made from: its name is in the run file
            (parse_manifest.kq_file), in $MRAG_BASE_DIR/parser_runs_faster/.
            This is exactly what the parser was shown. Advised.
  --chunks  without a Kq file: the manual's pieces (mmrag_cache_v3/chunks.jsonl
            and vine_data/vine_items.jsonl). The provisions shown are then
            read from the plans' own accounts.

writes:
  OUT_DIR/provisions.csv  one row per (question, provision shown); opens in Excel
  OUT_DIR/questions.csv   one row per question: status, counts, sections shown
  OUT_DIR/report.md       per question: every provision the parser left out or
                          set aside (with its reason), every check left open,
                          every check the decision or the answer does not use
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

NORMATIVE = ("Standard", "Guidance", "Option")
HEADING_ORDER = {"Standard": 0, "Guidance": 1, "Option": 2}
CLASS_ORDER = {"NOT ACCOUNTED": 0, "LEFT OUT": 1, "ADDED BY CODE": 2, "SET ASIDE": 3, "CHECKED": 4}
ID_RE = re.compile(r"MUTCD11e_[A-Za-z0-9.\-]+(?:_[A-Za-z0-9.\-]+)*")
ITEM_RE = re.compile(r"_item[A-Za-z0-9]+$")


def stop(msg):
    sys.exit("drop_report: STOPPED: " + msg)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_chunks(paths):
    meta = {}
    for p in paths or []:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    if r.get("chunk_id"):
                        meta[str(r["chunk_id"])] = r
    return meta


def para_key(c):
    """(section, paragraph) of a piece, as the parser's own code reads it."""
    if not c:
        return ("", "")
    return (str(c.get("section_id") or ""), str(c.get("ordinal") or ""))


def rests_on(o, cid, meta):
    """Same rule as mrag/vine/parser.py rests_on: the check's source_chunk is
    that provision (or another item of the same paragraph), or one of its
    evidence hints names that section and paragraph."""
    if str(o.get("source_chunk") or "") == cid:
        return True
    sec, para = para_key(meta.get(cid))
    if not sec or not para:
        return False
    if para_key(meta.get(str(o.get("source_chunk") or ""))) == (sec, para):
        return True
    return hint_names(o, cid, meta)


def hint_names(o, cid, meta):
    sec, para = para_key(meta.get(cid))
    return bool(sec and para) and any(
        isinstance(h, dict) and str(h.get("type") or "") == "section" and str(h.get("id") or "").strip() == sec
        and str(h.get("paragraph") or "").strip() == para for h in o.get("evidence_hint") or [])


def guard_states(g, out):
    if not g:
        return out
    if isinstance(g, dict):
        if "state" in g:
            out.append(str(g["state"]))
        for k, v in g.items():
            if k not in ("state", "status") and isinstance(v, (dict, list)):
                guard_states(v, out)
    elif isinstance(g, list):
        for x in g:
            guard_states(x, out)
    return out


def in_decision(spec):
    """Every check and merge the final decision is built from: reached from the
    terminal through merge inputs, requirements and guards."""
    obl = {o["id"]: o for o in spec.get("obligations") or []}
    mer = {m["id"]: m for m in spec.get("merges") or []}
    seen, todo = set(), [spec.get("terminal")]
    while todo:
        x = todo.pop()
        if not x or x in seen:
            continue
        seen.add(x)
        if x in mer:
            todo += list(mer[x].get("inputs") or [])
            todo += guard_states(mer[x].get("guard"), [])
        if x in obl:
            todo += list(obl[x].get("requires") or [])
            todo += guard_states(obl[x].get("guard"), [])
    return seen


def cited_ids(answer):
    """Ids the answer cites: in its text (a trailing full stop or dash removed)
    and in answer.citations."""
    ids = set()
    if isinstance(answer, dict):
        text = answer.get("text") or ""
        for c in answer.get("citations") or []:
            if isinstance(c, dict) and c.get("id"):
                ids.add(str(c["id"]))
    else:
        text = str(answer or "")
    for m in ID_RE.findall(text):
        ids.add(m.rstrip(".-"))
    return ids


def is_cited(cid, meta, ids):
    if cid in ids:
        return True
    # a list item counts as cited when its own paragraph is cited, except the
    # definitions list of 1C.02 (one paragraph holding hundreds of definitions)
    parent = ITEM_RE.sub("", cid)
    return parent != cid and parent in ids and para_key(meta.get(cid))[0] != "1C.02"


def short(s, n=300):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 3] + "..."


def cell(v):
    """Excel: never start a cell with a formula sign."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not rows:
            w.writerow(["(no rows)"])
            return
        w.writerow(list(rows[0].keys()))
        for r in rows:
            w.writerow([cell(v) for v in r.values()])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_file")
    ap.add_argument("out_dir")
    ap.add_argument("--kq")
    ap.add_argument("--chunks", nargs="*", default=[])
    a = ap.parse_args(argv)

    run = load_json(a.run_file)
    if not isinstance(run, dict) or not isinstance(run.get("plans"), dict) or not run["plans"]:
        stop(f"{a.run_file} has no plans: give the vine_run_*.json file the execute stage wrote")
    plans, execs = run["plans"], run.get("executions") or {}
    kq = {}
    if a.kq:
        kq = load_json(a.kq)
        want = str((run.get("parse_manifest") or {}).get("kq_file") or "")
        if want and Path(a.kq).name != want:
            stop(f"the run's plans were made from {want}, but --kq is {Path(a.kq).name}")
        bad = []
        for qid, p in plans.items():
            k = kq.get(qid) if isinstance(kq, dict) else None
            if not isinstance(k, dict) or not isinstance(k.get("chunks"), list):
                bad.append(f"{qid}: not in the Kq file")
            elif str(k.get("question")) != str((p or {}).get("question")):
                bad.append(f"{qid}: the Kq file holds another question text")
            elif (p or {}).get("kq_size") is not None and int(p["kq_size"]) != len(k["chunks"]):
                bad.append(f"{qid}: {len(k['chunks'])} pieces in the Kq file, the plan says {p['kq_size']}")
        if bad:
            stop("the Kq file does not match this run: " + "; ".join(bad[:10])
                 + (f" ... and {len(bad) - 10} more" if len(bad) > 10 else ""))
    meta = load_chunks(a.chunks)
    if not kq and not meta:
        stop("give --kq (advised) or --chunks: the report needs each provision's paragraph")
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    prov_rows, q_rows, md = [], [], []
    md.append(f"# Drop report: {Path(a.run_file).name}\n")
    md.append(f"- code commit {run.get('commit')}, retrieval {run.get('retrieval_commit')}, "
              f"store {run.get('store')}; parser instructions "
              f"{str((run.get('parse_manifest') or {}).get('instructions_sha256') or '')[:8]}")
    md.append(f"- provisions shown read from: {'the Kq file ' + Path(a.kq).name if kq else 'the plans (no Kq file given)'}")
    md.append("- A provision retrieval never found was never shown to the parser and cannot appear here. "
              "Check the list of sections shown for each question.\n")
    totals = Counter()

    for qid in plans:
        p = plans[qid] or {}
        e = execs.get(qid) or {}
        spec = p.get("spec") or {}
        kq_chunks = ((kq.get(qid) or {}).get("chunks") or []) if kq else []
        qmeta = dict(meta)
        for c in kq_chunks:
            if c.get("chunk_id"):
                qmeta[str(c["chunk_id"])] = c
        if kq:
            shown = OrderedDict()
            for c in kq_chunks:
                cid = str(c.get("chunk_id") or "")
                if cid and str(c.get("content_type") or "") in NORMATIVE and cid not in shown:
                    shown[cid] = str(c.get("content_type"))
        else:
            shown = OrderedDict((str(x.get("id")), str((qmeta.get(str(x.get("id"))) or {}).get("content_type") or "?"))
                                for x in spec.get("provisions") or [])
        account = {}
        for x in spec.get("provisions") or []:
            account[str(x.get("id") or "").strip().strip("[]").strip()] = x
        obligations = spec.get("obligations") or []
        obl_by_id = {str(o.get("id")): o for o in obligations}
        certs = {str(c.get("id")): c for c in e.get("certificates") or []}
        decision = in_decision(spec) if spec else set()
        ids_cited = cited_ids(e.get("answer"))
        review = {str(x.get("provision") or ""): x for x in ((e.get("plan_review") or {}).get("added") or [])}
        if not spec:
            status = "PLAN FAILED"
        elif not execs.get(qid):
            status = "NOT EXECUTED"
        elif e.get("error"):
            status = "EXECUTION ERROR: " + short(e.get("error"), 120)
        else:
            status = "ok"
        sections = OrderedDict()
        for c in kq_chunks or [qmeta.get(i) or {} for i in shown]:
            s = str(c.get("section_id") or "")
            if s:
                sections[s] = sections.get(s, 0) + 1

        counts = Counter()
        rows_q = []
        for cid, heading in shown.items():
            entry = account.get(cid) or {}
            named = entry.get("checked_by") or []
            named = [named] if isinstance(named, str) else [str(x) for x in named if str(x).strip()]
            is_item = bool(ITEM_RE.search(cid))
            # checks that rest on this provision itself
            own = [o for o in obligations
                   if str(o.get("source_chunk") or "") == cid
                   or (str(o.get("id")) in named and rests_on(o, cid, qmeta))
                   or (not is_item and hint_names(o, cid, qmeta))]
            other_item = [o for o in obligations if o not in own and rests_on(o, cid, qmeta)]
            named_bad = [i for i in named if i not in obl_by_id or not rests_on(obl_by_id[i], cid, qmeta)]
            set_aside = bool(str(entry.get("not_related") or "").strip())
            note = ""
            if own:
                what = "ADDED BY CODE" if entry.get("added_by_code") else "CHECKED"
            elif set_aside:
                what = "SET ASIDE"
            elif other_item and not named_bad:
                what = "LEFT OUT"
                note = ("no check of its own; another item of the same paragraph is checked by "
                        + " ".join(str(o["id"]) for o in other_item))
            else:
                what = "NOT ACCOUNTED"
                if named_bad:
                    note = "the plan names " + " ".join(named_bad) + " for it, but they do not rest on it"
                elif not spec:
                    note = "no plan"
            results = [(str(o["id"]), str((certs.get(str(o["id"])) or {}).get("status") or "not run")) for o in own]
            open_why = [f"{o['id']}: " + short((certs.get(str(o["id"])) or {}).get("reason"), 250) for o in own
                        if str((certs.get(str(o["id"])) or {}).get("status")) == "UNKNOWN"]
            used = any(str(o["id"]) in decision for o in own)
            cited = is_cited(cid, qmeta, ids_cited)
            rv = review.get(cid)
            rv_cert = (certs.get(str(rv.get("id"))) or certs.get("s_" + str(rv.get("id"))) or {}) if rv else {}
            c = qmeta.get(cid) or {}
            row = OrderedDict([
                ("question", qid), ("question_status", status), ("heading", heading),
                ("section", c.get("section_id") or ""), ("paragraph", c.get("ordinal") or ""), ("provision", cid),
                ("parser", what),
                ("parser_reason_if_set_aside", short(entry.get("not_related"), 400) if what == "SET ASIDE" else ""),
                ("note", note), ("checks", " ".join(f"{i}={s}" for i, s in results)),
                ("in_final_decision", ("yes" if used else "no") if own else ""),
                ("cited_in_answer", ("yes" if cited else "no") if own else ""),
                ("why_open", " | ".join(open_why)),
                ("review_added_check", (f"{rv.get('id')}={rv_cert.get('status') or 'not run'}" if rv else "")),
                ("text", short(c.get("text"), 500)),
            ])
            rows_q.append(row)
            counts[(what, heading)] += 1
            if own and any(s == "UNKNOWN" for _, s in results):
                counts[("OPEN", heading)] += 1
            if own and not used:
                counts[("OUTSIDE DECISION", heading)] += 1
            if own and not cited:
                counts[("NOT CITED", heading)] += 1
        rows_q.sort(key=lambda r: (CLASS_ORDER[r["parser"]], HEADING_ORDER.get(r["heading"], 9),
                                   r["section"], str(r["paragraph"]), r["provision"]))
        prov_rows += rows_q
        totals.update(counts)

        def n(what, h=None):
            return sum(v for (w, hh), v in counts.items() if w == what and (h is None or hh == h))
        q_rows.append(OrderedDict([
            ("question", qid), ("question_status", status), ("decision", e.get("terminal")),
            ("plan_outcome", p.get("outcome")),
            ("shown_standard", sum(1 for h in shown.values() if h == "Standard")),
            ("shown_guidance", sum(1 for h in shown.values() if h == "Guidance")),
            ("shown_option", sum(1 for h in shown.values() if h == "Option")),
            ("checked", n("CHECKED")), ("added_by_code", n("ADDED BY CODE")),
            ("left_out", n("LEFT OUT")), ("not_accounted", n("NOT ACCOUNTED")),
            ("set_aside_standard", n("SET ASIDE", "Standard")), ("set_aside_guidance", n("SET ASIDE", "Guidance")),
            ("set_aside_option", n("SET ASIDE", "Option")),
            ("checked_left_open", n("OPEN")), ("checked_outside_decision", n("OUTSIDE DECISION")),
            ("checked_not_cited", n("NOT CITED")), ("review_added", len(review)),
            ("sections_shown", " ".join(f"{s}({k})" for s, k in sections.items())),
        ]))

        md.append(f"## {qid}  (decision: {e.get('terminal')}; plan: {p.get('outcome')}; {status})\n")
        md.append(f"- Shown: {q_rows[-1]['shown_standard']} Standards, {q_rows[-1]['shown_guidance']} Guidance, "
                  f"{q_rows[-1]['shown_option']} Options. Checked {n('CHECKED')}; set aside {n('SET ASIDE')} "
                  f"(Standards {n('SET ASIDE', 'Standard')}, Guidance {n('SET ASIDE', 'Guidance')}, Options "
                  f"{n('SET ASIDE', 'Option')}); left out {n('LEFT OUT')}; added by code {n('ADDED BY CODE')}; "
                  f"not accounted {n('NOT ACCOUNTED')}.")
        md.append(f"- Sections shown: {', '.join(sections) or 'none'}")
        for what, title in (("NOT ACCOUNTED", "NOT ACCOUNTED"),
                            ("LEFT OUT", "Left out by the parser (another item of the paragraph is checked; "
                                         "no check of its own)"),
                            ("ADDED BY CODE", "Left out by the parser; the code added a check")):
            rs = [r for r in rows_q if r["parser"] == what]
            if rs:
                md.append(f"- **{title} ({len(rs)}):**")
                for r in rs:
                    md.append(f"  - {r['provision']} ({r['heading']}) {r['checks']} {r['note']}".rstrip())
        for h in ("Standard", "Guidance", "Option"):
            aside = [r for r in rows_q if r["parser"] == "SET ASIDE" and r["heading"] == h]
            # the many one-line definitions of Section 1C.02 go on one line here (all are in provisions.csv)
            defs = [r for r in aside if r["section"] == "1C.02" and ITEM_RE.search(r["provision"])
                    and not r["review_added_check"]]
            aside = [r for r in aside if r not in defs]
            if aside or defs:
                md.append(f"- **{h} set aside by the parser ({len(aside) + len(defs)}):**")
                if defs:
                    md.append(f"  - {len(defs)} definitions of Section 1C.02: "
                              + ", ".join(r["provision"].rsplit("_", 1)[-1] for r in defs))
                for r in aside:
                    flag = f" [review added {r['review_added_check']}]" if r["review_added_check"] else ""
                    md.append(f"  - {r['provision']}{flag}: {r['parser_reason_if_set_aside']}")
        opened = [r for r in rows_q if r["why_open"]]
        if opened:
            md.append(f"- **Checked but left open (UNKNOWN) ({len(opened)}):**")
            for r in opened:
                md.append(f"  - {r['provision']} ({r['heading']}): {r['why_open']}")
        outside = [r for r in rows_q if r["in_final_decision"] == "no"]
        if outside:
            md.append(f"- Checked but not part of the final decision ({len(outside)}): "
                      + ", ".join(f"{r['provision']} [{r['checks']}]" for r in outside))
        notcited = [r for r in rows_q if r["cited_in_answer"] == "no"]
        if notcited:
            md.append(f"- Checked but not cited in the answer ({len(notcited)}): "
                      + ", ".join(r["provision"] for r in notcited))
        md.append("")

    write_csv(out / "provisions.csv", prov_rows)
    write_csv(out / "questions.csv", q_rows)

    def t(what, h=None):
        return sum(v for (w, hh), v in totals.items() if w == what and (h is None or hh == h))
    bad_q = [r["question"] + " (" + r["question_status"] + ")" for r in q_rows if r["question_status"] != "ok"]
    head = [f"- {len(q_rows)} questions, {len(prov_rows)} provisions shown: checked {t('CHECKED')}; set aside "
            f"{t('SET ASIDE')} (Standards {t('SET ASIDE', 'Standard')}, Guidance {t('SET ASIDE', 'Guidance')}, "
            f"Options {t('SET ASIDE', 'Option')}); left out {t('LEFT OUT')}; added by code {t('ADDED BY CODE')}; "
            f"not accounted {t('NOT ACCOUNTED')}.",
            f"- Checked but left open: {t('OPEN')}; checked but outside the final decision: {t('OUTSIDE DECISION')}; "
            f"checked but not cited in the answer: {t('NOT CITED')}.",
            f"- Questions with a failed plan or an execution error: {', '.join(bad_q) if bad_q else 'none'}.\n"]
    md[4:4] = head
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(head))
    print(f"wrote {out / 'provisions.csv'}, {out / 'questions.csv'}, {out / 'report.md'}")


if __name__ == "__main__":
    main()
