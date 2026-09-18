"""Capture new market vocabulary from company websites, and act on it once it recurs.

Rule (Daniel, 2026-09-19): agents log every product, service or phrase they
meet on a company website that isn't in the Scope & Search Vocabulary doc yet.
Once a phrase has been seen at 3 different companies:
  - description (Section 2, services-offered wording) -> added to the doc directly;
  - product (Section 1 Product List), service (Section 1 Services List) and
    scope (a new category for Section 0) -> proposed to Daniel on the Tally tab.
When Daniel sets a proposal's Status to "Approved", `process` adds product and
service items to their table (search terms then regenerate) and reports scope
items for Athena to add to Section 0 by hand. "Rejected" phrases are never
proposed again.

Log: "Vocabulary Log — Aurias 2" sheet. Tabs: Sightings (one row per phrase per
company), Tally (every phrase that reached the threshold, with its status).

Usage:
  python vocab_capture.py log SIGHTINGS.json   # [{"phrase","kind","company","ch_number","source_url","logged_by"}]
  python vocab_capture.py process [--dry-run]
"""
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

# Env overrides exist only so tests can run against copies.
LOG_ID = os.environ.get("VOCAB_LOG_ID", "1y1iOwjN1BHrNM0GKWZS68WuXZRIPAiHvy-jm-iZcq5A")
DOC_ID = os.environ.get("VOCAB_DOC_ID", "1VcU78QCMR0Az9N-l-mVidFe5Qsu6ZvoD-xB6RzD9ScQ")
AUTH = "/c/Users/HP/.claude/credentials/sheets_auth.sh"
THRESHOLD = 3
KINDS = {"product", "service", "description", "scope"}
TABLE_LABEL = {"product": "Product List:", "service": "Services List:"}
SECTION2_LINE = "Added from company websites (seen at 3+ companies):"
TODAY = datetime.date.today().isoformat()


def token():
    return subprocess.run(["bash", AUTH], capture_output=True, text=True, check=True).stdout.strip()


TOK = None


def call(url, body=None, method=None):
    global TOK
    TOK = TOK or token()
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None,
                                 method=method or ("POST" if body is not None else "GET"))
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def sheet_read(rng):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{LOG_ID}/values/{urllib.parse.quote(rng, safe='!:')}"
    return call(url).get("values", [])


def sheet_append(rng, rows):
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{LOG_ID}/values/{urllib.parse.quote(rng, safe='!:')}"
           ":append?valueInputOption=RAW&insertDataOption=INSERT_ROWS")
    call(url, {"values": rows})


def sheet_write(rng, rows):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{LOG_ID}/values/{urllib.parse.quote(rng, safe='!:')}?valueInputOption=RAW"
    call(url, {"values": rows}, method="PUT")


def norm(s):
    return re.sub(r"\s+", " ", s.strip().strip(".,;:").lower())


def para_text(el):
    return "".join(e.get("textRun", {}).get("content", "") for e in el["paragraph"]["elements"]).rstrip("\n")


def get_doc():
    return call(f"https://docs.googleapis.com/v1/documents/{DOC_ID}")


def find_table(doc, label):
    seen = False
    for el in doc["body"]["content"]:
        if "paragraph" in el and para_text(el).strip() == label:
            seen = True
        elif seen and "table" in el:
            return el
    raise SystemExit(f"Error: no table after {label!r}")


def cell_text(cell):
    return "".join(e.get("textRun", {}).get("content", "")
                   for c in cell["content"] if "paragraph" in c for e in c["paragraph"]["elements"]).strip()


def known_phrases(doc):
    """Normalised text already in the doc, per kind."""
    known = {k: set() for k in KINDS}
    for kind, label in TABLE_LABEL.items():
        known[kind] = {norm(cell_text(r["tableCells"][0])) for r in find_table(doc, label)["table"]["tableRows"]}
    full = "\n".join(para_text(el) for el in doc["body"]["content"] if "paragraph" in el).lower()
    s2 = full[full.find("section 2"):]
    known["description"] = s2
    known["scope"] = full[full.find("section 0"):full.find("section 1")]
    return known


def already_known(known, kind, p):
    # Sets for the two tables (exact item), text for Section 0/2 (substring).
    return p in known[kind]


def cmd_log(path):
    items = json.load(open(path, encoding="utf-8"))
    known = known_phrases(get_doc())
    rows, skipped = [], 0
    for it in items:
        kind = it["kind"].strip().lower()
        if kind not in KINDS:
            raise SystemExit(f"Error: kind must be one of {sorted(KINDS)}, got {kind!r}")
        if already_known(known, kind, norm(it["phrase"])):
            skipped += 1
            continue
        rows.append([TODAY, it["phrase"].strip(), kind, it["company"].strip(), it.get("ch_number", "").strip(),
                     it.get("source_url", "").strip(), it.get("logged_by", "").strip()])
    if rows:
        sheet_append("Sightings!A:G", rows)
    print(f"Logged {len(rows)} sighting(s); skipped {skipped} already in the doc.")


def add_table_row(label, text):
    doc = get_doc()
    t = find_table(doc, label)
    last = len(t["table"]["tableRows"]) - 1
    call(f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate", {"requests": [{"insertTableRow": {
        "tableCellLocation": {"tableStartLocation": {"index": t["startIndex"]}, "rowIndex": last, "columnIndex": 0},
        "insertBelow": True}}]})
    t = find_table(get_doc(), label)
    idx = t["table"]["tableRows"][-1]["tableCells"][0]["content"][0]["startIndex"]
    call(f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
         {"requests": [{"insertText": {"location": {"index": idx}, "text": text}}]})


def add_description(phrase):
    doc = get_doc()
    line = next((el for el in doc["body"]["content"] if "paragraph" in el
                 and para_text(el).startswith(SECTION2_LINE)), None)
    if line:
        end = line["endIndex"] - 1
        req = {"insertText": {"location": {"index": end}, "text": f"; {phrase}"}}
    else:
        notes = [el for el in doc["body"]["content"] if "paragraph" in el and para_text(el).strip() == "NOTES"]
        if len(notes) != 1:
            raise SystemExit("Error: can't find the NOTES heading in Section 2")
        req = {"insertText": {"location": {"index": notes[0]["startIndex"]}, "text": f"{SECTION2_LINE} {phrase}\n"}}
    call(f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate", {"requests": [req]})


def cmd_process(dry):
    sightings = sheet_read("Sightings!A2:G")
    tally = sheet_read("Tally!A2:G")
    tally_keys = {(norm(r[0]), r[1]) for r in tally if len(r) > 1}
    known = known_phrases(get_doc())

    groups = {}
    for r in sightings:
        r = r + [""] * (7 - len(r))
        key = (norm(r[1]), r[2])
        g = groups.setdefault(key, {"phrase": r[1], "companies": set(), "first": r[0]})
        g["companies"].add(norm(r[4]) or norm(r[3]))
        g["first"] = min(g["first"], r[0])

    new_rows, report = [], []
    for (p, kind), g in sorted(groups.items()):
        n = len(g["companies"])
        if n < THRESHOLD or (p, kind) in tally_keys or already_known(known, kind, p):
            continue
        if kind == "description":
            status = "Added automatically"
            if not dry:
                add_description(g["phrase"])
            report.append(f"Added to Section 2: {g['phrase']} ({n} companies)")
        else:
            status = "Pending"
            report.append(f"Proposed to Daniel ({kind}): {g['phrase']} ({n} companies)")
        new_rows.append([g["phrase"], kind, n, g["first"], status, TODAY if status != "Pending" else "", ""])

    # Apply Daniel's approvals.
    for i, r in enumerate(tally, start=2):
        r = r + [""] * (7 - len(r))
        if r[4].strip().lower() != "approved":
            continue
        if r[1] in TABLE_LABEL:
            if not dry and norm(r[0]) not in known[r[1]]:
                add_table_row(TABLE_LABEL[r[1]], r[0])
            report.append(f"Approved and added to {TABLE_LABEL[r[1]][:-1]}: {r[0]}")
            if not dry:
                sheet_write(f"Tally!E{i}:F{i}", [["Added to doc", TODAY]])
        elif r[1] == "scope":
            report.append(f"Approved scope item for Athena to add to Section 0 by hand: {r[0]}")
            if not dry:
                sheet_write(f"Tally!E{i}:F{i}", [["Approved - Athena to add", TODAY]])

    if new_rows and not dry:
        sheet_append("Tally!A:G", new_rows)
    print("\n".join(report) if report else "Nothing new reached the threshold; no approvals to apply.")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "log":
        cmd_log(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == "process":
        cmd_process("--dry-run" in sys.argv)
    else:
        sys.exit(__doc__)
