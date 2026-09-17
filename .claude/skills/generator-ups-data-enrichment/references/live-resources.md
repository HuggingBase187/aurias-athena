# Live resources — generator-ups-data-enrichment

Current IDs for the sheets this skill works against. Google Docs/Sheets get recreated occasionally (trashed and rebuilt, or converted between Excel and native Sheets) — when that happens, this is the only file that needs updating. Nothing else in the skill should hardcode an ID directly.

## Master sheet — the one this skill enriches

**Master UK generator and UPS Market Map** (native Google Sheet, converted from Excel 2026-09-17)
- Spreadsheet ID: `1wf1vhj4_jvufGxpAO_3QAszTL9nSG8w6q1iVjp65-c8`
- Parent Drive folder: `1H7NZ3fHzNKivddH89yvgn0xkDP12iXiy` ("UK Generator + UPS Market Map")
- Tabs: **Market Map** (the working data — 461 companies as of 2026-09-17, confirmed by reading the full Company Name column via the Sheets API rather than `read_file_content`/`download_file_content`, which have both previously undercounted this sheet silently — most rows still only have Company Name + Website populated), **Qualified Leads** (destination for anything that clears screening — a copy, the source row stays on Market Map too, never removed), **Legend & Sourcing Rules** (mirrors `references/data-template.md` — keep both in sync if either changes)
- Row 2 is a fictional worked example (`[EXAMPLE - FICTIONAL] Sample Power Solutions Ltd`) — delete it before/while enriching, per the template's own instruction. There's also a genuinely blank row partway down the list (around "Mecc Alte UK Ltd" / "Metaphor IT") worth checking when that section comes up in a batch.
- **Always get an authoritative row count via the Sheets API directly** (read the full Company Name column and count non-empty entries), not `read_file_content` or a Drive natural-language read — both have silently undercounted this exact sheet before (once when it was an Excel file, and the same risk applies to any large Google Sheet read through a summarizing tool rather than the values API).
- This sheet is the one and only place this skill writes real data. Never write to any other spreadsheet without Daniel confirming it's a deliberate change of target.

## Template — reference only, not a place this skill writes to

**Market Map Template** (native Google Sheet, converted from Excel 2026-09-17)
- Spreadsheet ID: `1C6dMxQ5TBg6rgnIMSt20ZFzh65BI8_8yW2Xt9H6OAcs`
- Parent Drive folder: `1Ie4KJKYw3Tb2sZZNpOFMwo9cR1HU0CRQ`
- Same tab structure as the master sheet, but with only the fictional worked example row — this is what a fresh copy of the template looks like, kept for reference and for spinning up any future market-map sheet with the same structure.

## Sheets API access

- Credentials: `C:\Users\HP\.claude\credentials\aurias-athena-sheets.json` (key), `...\aurias-athena-sheets.pem` (signing key), `...\sheets_auth.sh` (returns a fresh bearer token). Never print or output the contents of the `.json` or `.pem` files.
- Service account: `athena-sheets-writer@aurias-athena-sheets.iam.gserviceaccount.com`
- **Sharing is manual, not automatic.** The Drive connector's OAuth scope doesn't include permission-management, so attempts to share a file with the service account via the connector fail with a 403 even when Daniel has authorized it — confirmed 2026-09-17. Daniel has to add the service account as Editor himself, either per-file (Share button) or, more durably, at the folder level so anything created inside inherits access automatically.
- **As of 2026-09-17, Daniel is sharing the whole "Aurias 2" Drive folder** with the service account as Editor, specifically so future sheets/docs created inside it don't need a manual per-file share. If a future write fails with a 403 permission error, the first thing to check is whether the target file actually lives inside that shared folder tree — if it doesn't, ask Daniel to share it (or move it).

## Related docs (context, not written to by this skill)

- Services Vocabulary & Search Keywords doc: `1VcU78QCMR0Az9N-l-mVidFe5Qsu6ZvoD-xB6RzD9ScQ` — Section 2 has the real services vocabulary used to fill the Services Offered column.
- Power OEM database: `1yGu0zjSbpqmb1ysvjsSvL8CdbDtyMz7GfBQe2X4MTRA` — useful for recognizing OEM names when filling Key OEM Partnerships.
- 2023 Aurias 1 contact-enrichment precedent sheet: `1jScEMUN6XppcdBzwqyf4SbUUOQcQh4mujLvCCKHHOOs` — shows this exact discipline (PSC chase, blank-over-guess) working in practice.
