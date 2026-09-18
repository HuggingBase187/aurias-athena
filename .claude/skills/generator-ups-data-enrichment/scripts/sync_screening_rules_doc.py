"""Regenerate the "Screening Rules — Aurias 2" Google Doc from the rulebook.

The rulebook is references/data-template.md ("Screening rules" and "Reading
headcount" sections). The Google Doc is a read-only, human-readable copy for
Daniel. Hand-keeping both let them drift within an hour (2026-09-18), so the
doc is now generated: never edit it directly -- change the rulebook and run
this (a PostToolUse hook runs it automatically after any edit to
data-template.md).

Usage: python sync_screening_rules_doc.py [--dry-run] [--if-changed]
  --if-changed: only rewrite the doc if the rulebook sections changed since the
                last sync (hash kept in scripts/.screening_rules.hash).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
RULEBOOK = os.path.join(HERE, "..", "references", "data-template.md")
DOC_ID = "1l4YEw1gTwx3fTau6T-7Im9JZJDG8k1iOoxSl_woBwIo"
SECTIONS = ["## Screening rules", "## Reading headcount"]


def section(md, header):
    a = md.index(header)
    b = md.find("\n## ", a + 1)
    return md[a:b if b != -1 else len(md)]


def to_blocks(md_section):
    blocks = []
    for raw in md_section.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        line = line.replace("`", "")
        if line.startswith("## "):
            title = re.sub(r"\s*\(.*?\)\s*$", "", line[3:])
            blocks.append({"style": "HEADING_2", "text": title})
        elif re.match(r"^\s*(-|\d+\.)\s+", line):
            blocks.append({"style": "BULLET", "text": re.sub(r"^\s*(-|\d+\.)\s+", "", line)})
        else:
            blocks.append({"style": "NORMAL_TEXT", "text": line})
    return blocks


def main():
    md = open(RULEBOOK, encoding="utf-8").read()
    blocks = [
        {"style": "HEADING_1", "text": "Screening Rules — Aurias 2"},
        {"style": "NORMAL_TEXT", "text": "*Generated automatically from the rulebook the Skills use (data-template.md). "
         "Don't edit this doc — ask Athena to change the rulebook and it regenerates. Scope: Section 0 of the "
         "\"Scope & Search Vocabulary\" doc. Near-miss routing: the \"Near Miss Rules\" doc.*"},
    ]
    body = "".join(section(md, h) for h in SECTIONS)
    for h in SECTIONS:
        blocks += to_blocks(section(md, h))
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    hash_file = os.path.join(HERE, ".screening_rules.hash")
    if "--if-changed" in sys.argv and os.path.exists(hash_file) and open(hash_file).read().strip() == digest:
        return
    if "--dry-run" in sys.argv:
        print(json.dumps(blocks, ensure_ascii=False, indent=1))
        return
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False)
        path = f.name
    try:
        out = subprocess.run(["bash", os.path.join(HERE, "docs_api.sh"), "rewrite", DOC_ID, path],
                             capture_output=True, text=True)
        if out.returncode != 0 or '"replies"' not in out.stdout:
            sys.exit(f"Error: doc rewrite failed:\n{out.stdout[:500]}\n{out.stderr[:500]}")
        open(hash_file, "w").write(digest)
        print(f"Screening Rules doc regenerated ({len(blocks)} blocks).")
    finally:
        os.unlink(path)


if __name__ == "__main__":
    main()
