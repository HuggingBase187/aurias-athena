#!/usr/bin/env python
"""
Reads the Market Map's full row range (A:AF, piped in as Sheets API JSON on
stdin) and flags likely duplicate rows. Never deletes, never decides -- per
the hard-line rule in ATHENA.md, only a confirmed exact duplicate may ever
be removed, and that call stays a human/agent judgment, not this script's.
Every row printed here is a candidate to go check, nothing more.

Why this exists: duplicates (YorPower as three separate rows; Power
Control Ltd, Alpha Power, Bespoke Power, already found and removed) were
only ever found by accident during enrichment. At 450+ rows that's not a
plan -- see sourcing-verifier.md's "Duplicate/conflicting rows" check.

v2 (2026-09-18): every match now carries a `recommended_keep` /
`recommended_delete` based on which row has more populated cells --
added after a real incident where the *enriched* row got deleted and the
near-empty stub got kept, the opposite of the point, a couple of times in
one day. This script only recommends; whoever acts on it still has to
re-verify before deleting (per sheet-write-safety.md section 2), but the
recommendation is now explicit and computed, not left to a glance.
"""
import json
import re
import sys
from difflib import SequenceMatcher

SUFFIX_RE = re.compile(r"\b(ltd|limited|plc|llp|uk|group|holdings?|the)\b", re.I)
PUNCT_RE = re.compile(r"[^a-z0-9 ]")
NAME_SIMILARITY_THRESHOLD = 0.87


def normalize(name):
    name = name.lower()
    name = SUFFIX_RE.sub(" ", name)
    name = PUNCT_RE.sub(" ", name)
    return " ".join(name.split())


def completeness(row):
    """Count of non-blank cells across the whole row -- the proxy for
    "how enriched is this row", used to recommend which side of a
    duplicate pair to keep."""
    return sum(1 for cell in row if cell and cell.strip())


def keep_delete_verdict(group):
    """group: list of entry dicts, each with 'row', 'name', 'non_empty_cells'.
    Returns (recommended_keep_row, recommended_delete_rows, reason)."""
    scores = sorted(group, key=lambda g: -g["non_empty_cells"])
    best, second = scores[0], scores[1]
    if best["non_empty_cells"] == second["non_empty_cells"]:
        return None, None, "tie_on_populated_cell_count -- needs a human look, don't guess which to keep"
    return (
        best["row"],
        [g["row"] for g in scores[1:]],
        f"kept row {best['row']} ({best['non_empty_cells']} populated cells) over "
        + ", ".join(f"row {g['row']} ({g['non_empty_cells']} cells)" for g in scores[1:])
        + " -- never delete the more-enriched row",
    )


def main():
    data = json.load(sys.stdin)
    rows = data.get("values", [])

    entries = []
    for i, row in enumerate(rows):
        row_num = i + 2  # data starts at sheet row 2 (row 1 is the header)
        name = row[1] if len(row) > 1 else ""
        if not name.strip():
            continue
        ch_number = (row[2] if len(row) > 2 else "").strip()
        linkedin = (row[4] if len(row) > 4 else "").strip().rstrip("/").lower()
        entries.append({
            "row": row_num,
            "name": name,
            "ch_number": ch_number,
            "linkedin": linkedin,
            "norm_name": normalize(name),
            "non_empty_cells": completeness(row),
        })

    def annotate(group):
        keep, delete, reason = keep_delete_verdict(group)
        return {
            "rows": [{"row": g["row"], "name": g["name"], "populated_cells": g["non_empty_cells"]} for g in group],
            "recommended_keep": keep,
            "recommended_delete": delete,
            "reason": reason,
        }

    high_confidence = []

    by_ch = {}
    for e in entries:
        if e["ch_number"]:
            by_ch.setdefault(e["ch_number"], []).append(e)
    for ch_number, group in by_ch.items():
        if len(group) > 1:
            entry = annotate(group)
            entry["matched_on"] = "companies_house_number"
            entry["value"] = ch_number
            high_confidence.append(entry)

    by_linkedin = {}
    for e in entries:
        if e["linkedin"]:
            by_linkedin.setdefault(e["linkedin"], []).append(e)
    for url, group in by_linkedin.items():
        if len(group) > 1:
            entry = annotate(group)
            entry["matched_on"] = "linkedin_url"
            entry["value"] = url
            high_confidence.append(entry)

    # Same name once Ltd/plc/etc and punctuation are stripped -- much
    # stronger signal than a merely-similar name, but still short of
    # "high confidence" since two genuinely different companies can share
    # a generic trading name. Kept as its own tier rather than mixed into
    # the fuzzy list below.
    exact_norm_matches = []
    by_norm = {}
    for e in entries:
        by_norm.setdefault(e["norm_name"], []).append(e)
    for norm_name, group in by_norm.items():
        if norm_name and len(group) > 1:
            entry = annotate(group)
            entry["matched_on"] = "name_after_removing_ltd_plc_etc"
            exact_norm_matches.append(entry)

    exact_norm_rows = {g["row"] for m in exact_norm_matches for g in m["rows"]}

    # Merely-similar names -- noisier, especially for short 2-word names
    # ("JP Power" vs "JS Power" is one character apart but almost
    # certainly two different companies). Worth a quick human glance,
    # not a strong signal on its own -- don't treat this list the way
    # you'd treat the two tiers above.
    name_candidates = []
    seen_pairs = set()
    for i, a in enumerate(entries):
        for b in entries[i + 1:]:
            if not a["norm_name"] or not b["norm_name"] or a["norm_name"] == b["norm_name"]:
                continue
            if a["row"] in exact_norm_rows and b["row"] in exact_norm_rows:
                continue
            ratio = SequenceMatcher(None, a["norm_name"], b["norm_name"]).ratio()
            if ratio >= NAME_SIMILARITY_THRESHOLD:
                pair_key = (a["row"], b["row"])
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                entry = annotate([a, b])
                entry["similarity"] = round(ratio, 3)
                name_candidates.append(entry)

    name_candidates.sort(key=lambda x: -x["similarity"])

    print(json.dumps({
        "total_rows_scanned": len(entries),
        "guardrail": "recommended_keep is always the row with MORE populated cells -- never delete the more-enriched row, even if it isn't the one that matched first. If recommended_keep is null, the two rows tied on populated-cell count -- stop and ask a human, don't guess.",
        "high_confidence_duplicates": high_confidence,
        "exact_name_after_normalizing": exact_norm_matches,
        "fuzzy_name_similarity_candidates_low_confidence": name_candidates,
    }, indent=2))


if __name__ == "__main__":
    main()
