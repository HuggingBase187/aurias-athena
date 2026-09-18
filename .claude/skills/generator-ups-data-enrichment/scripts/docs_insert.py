"""Build a Docs API batchUpdate body that inserts styled paragraphs before an anchor paragraph.

Used by `docs_api.sh insert_before`. `replace` can only swap plain text, so any
new section with headings or bullets used to mean recreating the whole doc.
This locates the anchor by its text at run time (never a hand-computed index),
inserts everything in one go, then styles the inserted range.

Usage: python docs_insert.py DOC_JSON_FILE 'ANCHOR TEXT' BLOCKS_JSON_FILE
  ANCHOR TEXT: the full text of an existing paragraph (must match exactly one),
               or the literal __REWRITE__ to replace the whole body (same doc ID,
               same link -- used when a doc should be rewritten cleanly rather
               than patched).
  BLOCKS_JSON: [{"style": "HEADING_2" | "NORMAL_TEXT" | "BULLET", "text": "..."}]
    **double asterisks** in text mark bold spans; *single* marks italic.
Prints the batchUpdate request body to stdout.
"""
import json
import re
import sys


def para_text(p):
    return "".join(pe.get("textRun", {}).get("content", "") for pe in p.get("elements", [])).rstrip("\n")


def parse_spans(text):
    """Strip **bold** / *italic* markers; return (plain_text, [(start, end, kind)])."""
    out, spans, pos = [], [], 0
    for m in re.finditer(r"\*\*(.+?)\*\*|\*(.+?)\*|([^*]+|\*)", text):
        if m.group(1) is not None:
            spans.append((pos, pos + len(m.group(1)), "bold"))
            seg = m.group(1)
        elif m.group(2) is not None:
            spans.append((pos, pos + len(m.group(2)), "italic"))
            seg = m.group(2)
        else:
            seg = m.group(3)
        out.append(seg)
        pos += len(seg)
    return "".join(out), spans


def main():
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
    anchor = sys.argv[2]
    blocks = json.load(open(sys.argv[3], encoding="utf-8"))

    pre = []
    if anchor == "__REWRITE__":
        body_end = doc["body"]["content"][-1]["endIndex"]
        if body_end - 1 > 1:
            pre.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": body_end - 1}}})
        index = 1
    else:
        matches = [el for el in doc["body"]["content"]
                   if "paragraph" in el and para_text(el["paragraph"]) == anchor]
        if len(matches) != 1:
            sys.exit(f"Error: anchor matched {len(matches)} paragraphs (need exactly 1): {anchor!r}")
        index = matches[0]["startIndex"]

    text, styles, cursor = "", [], index
    for b in blocks:
        plain, spans = parse_spans(b["text"])
        length = len(plain) + 1  # + newline
        styles.append((cursor, cursor + length, b["style"], [(cursor + s, cursor + e, k) for s, e, k in spans]))
        text += plain + "\n"
        cursor += length
    end = index + len(text)

    if pre:
        # Clear leftover bullets/heading style from the old first paragraph.
        pre.append({"deleteParagraphBullets": {"range": {"startIndex": 1, "endIndex": 2}}})
    reqs = pre + [
        {"insertText": {"location": {"index": index}, "text": text}},
        {"updateTextStyle": {"range": {"startIndex": index, "endIndex": end},
                             "textStyle": {"bold": False, "italic": False}, "fields": "bold,italic"}},
    ]
    for start, stop, style, spans in styles:
        named = "NORMAL_TEXT" if style == "BULLET" else style
        reqs.append({"updateParagraphStyle": {"range": {"startIndex": start, "endIndex": stop},
                                              "paragraphStyle": {"namedStyleType": named},
                                              "fields": "namedStyleType"}})
        for s, e, kind in spans:
            reqs.append({"updateTextStyle": {"range": {"startIndex": s, "endIndex": e},
                                             "textStyle": {kind: True}, "fields": kind}})
    # Bullets last: createParagraphBullets doesn't change indices here since
    # the inserted text carries no leading tabs.
    for start, stop, style, _ in styles:
        if style == "BULLET":
            reqs.append({"createParagraphBullets": {"range": {"startIndex": start, "endIndex": stop},
                                                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
    print(json.dumps({"requests": reqs}))


if __name__ == "__main__":
    main()
