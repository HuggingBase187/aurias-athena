"""Regenerate the "Search terms" list in the Scope & Search Vocabulary doc.

Rule (Daniel, 2026-09-16/19): every search term = one Product List item + one
Services List item. The two tables are the source of truth; the flat list is
generated from them, never hand-typed. Add a row to either table, run this,
and every combination appears.

Reads the doc, reads the tables under "Product List:" and "Services List:",
and replaces everything between "Search terms:" and the paragraph that starts
"Transformers:" (or "SECTION 2") with the full cross-product, one product
group per block. No change is written if the list is already current.

Usage:
  python regen_search_terms.py [--dry-run]
Needs the Athena service-account auth script (same as docs_api.sh).
"""
import json
import os
import subprocess
import sys
import urllib.request

DOC_ID = "1VcU78QCMR0Az9N-l-mVidFe5Qsu6ZvoD-xB6RzD9ScQ"
AUTH = os.environ.get("SHEETS_AUTH_SCRIPT", "/c/Users/HP/.claude/credentials/sheets_auth.sh")
API = f"https://docs.googleapis.com/v1/documents/{DOC_ID}"


def token():
    return subprocess.run(["bash", AUTH], capture_output=True, text=True, check=True).stdout.strip()


def call(tok, url, body=None):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body else None, method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def paragraphs(doc):
    out = []
    for el in doc["body"]["content"]:
        p = el.get("paragraph")
        if p is not None:
            text = "".join(e.get("textRun", {}).get("content", "") for e in p["elements"]).rstrip("\n")
            out.append((text, el["startIndex"], el["endIndex"]))
    return out


def table_items(doc, label):
    """Text of each row's first cell in the first table after the paragraph `label`."""
    seen = False
    for el in doc["body"]["content"]:
        p = el.get("paragraph")
        if p is not None and "".join(e.get("textRun", {}).get("content", "") for e in p["elements"]).strip() == label:
            seen = True
        elif seen and "table" in el:
            items = []
            for row in el["table"]["tableRows"]:
                cell = row["tableCells"][0]
                txt = "".join(e.get("textRun", {}).get("content", "")
                              for c in cell["content"] if "paragraph" in c for e in c["paragraph"]["elements"]).strip()
                if txt:
                    items.append(txt)
            return items
    return []


def main():
    dry = "--dry-run" in sys.argv
    tok = token()
    doc = call(tok, API)
    paras = paragraphs(doc)
    products = table_items(doc, "Product List:")
    services = table_items(doc, "Services List:")
    if not products or not services:
        sys.exit("Error: Product List or Services List is empty -- refusing to regenerate.")

    texts = [t for t, _, _ in paras]
    s = next(i for i, t in enumerate(texts) if t.strip() == "Search terms:")
    e = next(i for i, t in enumerate(texts) if i > s and (t.startswith("Transformers:") or t.startswith("SECTION 2")))
    current = [t.strip() for t in texts[s + 1:e] if t.strip()]
    wanted = [f"{p} {v}" for p in products for v in services]
    print(f"{len(products)} products x {len(services)} services = {len(wanted)} search terms")
    if current == wanted:
        print("Search terms already current -- nothing to do.")
        return
    added = sorted(set(wanted) - set(current))
    removed = sorted(set(current) - set(wanted))
    print(f"Adding {len(added)}, removing {len(removed)}")
    for t in added[:20]:
        print("  +", t)
    for t in removed[:20]:
        print("  -", t)
    if dry:
        return

    start = paras[s][2]          # just after the "Search terms:" paragraph
    end = paras[e][1]            # start of the "Transformers:" / SECTION 2 paragraph
    blocks = ["\n".join(f"{p} {v}" for v in services) for p in products]
    new_text = "\n\n".join(blocks) + "\n\n"
    reqs = [{"deleteContentRange": {"range": {"startIndex": start, "endIndex": end}}},
            {"insertText": {"location": {"index": start}, "text": new_text}}]
    call(tok, API + ":batchUpdate", {"requests": reqs})
    check = paragraphs(call(tok, API))
    ct = [t for t, _, _ in check]
    s2 = next(i for i, t in enumerate(ct) if t.strip() == "Search terms:")
    e2 = next(i for i, t in enumerate(ct) if i > s2 and (t.startswith("Transformers:") or t.startswith("SECTION 2")))
    got = [t.strip() for t in ct[s2 + 1:e2] if t.strip()]
    if got != wanted:
        sys.exit("Error: read-back does not match the generated list -- check the doc.")
    print("Written and verified.")


if __name__ == "__main__":
    main()
