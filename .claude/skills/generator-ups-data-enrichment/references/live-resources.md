# Live resources — generator-ups-data-enrichment

Current IDs for the sheets this skill works against. Google Docs/Sheets get recreated occasionally (trashed and rebuilt, or converted between Excel and native Sheets) — when that happens, this is the only file that needs updating. Nothing else in the skill should hardcode an ID directly.

## Master sheet — the one this skill enriches

**Master UK generator and UPS Market Map** (native Google Sheet, converted from Excel 2026-09-17)
- Spreadsheet ID: `1wf1vhj4_jvufGxpAO_3QAszTL9nSG8w6q1iVjp65-c8`
- Parent Drive folder: `1H7NZ3fHzNKivddH89yvgn0xkDP12iXiy` ("UK Generator + UPS Market Map")
- Tabs: **Market Map** (the working data — count moves constantly as confirmed duplicates/bad rows are removed or moved to Suspected Hallucinations — check it fresh via the Sheets API rather than trusting any number written here, don't treat a lower count as data loss without checking the removal history first, confirmed by reading the full Company Name column via the Sheets API rather than `read_file_content`/`download_file_content`, which have both previously undercounted this sheet silently), **Qualified Leads** (destination for anything that clears screening via headcount or PBT — a copy, the source row stays on Market Map too, never removed), **Flagged to You** (added 2026-09-18 — destination for a "Needs more info" verdict, e.g. PBT qualifies but ownership is PE/large-group, or a near-miss reclassified by the monthly sweep; same copy-not-move pattern as Qualified Leads, Daniel reviews and reclassifies himself), **Suspected Hallucinations** (added 2026-09-18, at Daniel's explicit request — destination for rows carrying an "Out-of-scope - suspected hallucinated/fake entry" verdict, i.e. the hallucinated-entry checklist in `data-template.md` was fully exhausted: no Companies House match, no DNS resolution, no web presence. Unlike every other verdict category, these rows are actually **moved**, not copied — full row deleted from Market Map after being appended here first, verified via count reconciliation before/after. This is a standing, narrow exception to the never-delete-rows rule, same evidentiary bar as a confirmed exact duplicate; first run moved 10 rows: Brookpower, C.S.C Power, C&G Generators, C&N Carberry, Capel Power, Central Scotland Gen, Central UPS, Cogeneration UK, Cornwall Gen., Critical Power Group), **Batch Ledger** (added 2026-09-18 — multi-batch coordination, see `SKILL.md` section 1c), **Verification Log** (one row per enrichment batch, written by `generator-ups-data-verification`), **Near-Miss Review Log** (added 2026-09-18 — one row per monthly run of `generator-ups-near-misses-update`, not per company; different shape/purpose than Verification Log, don't conflate the two)
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

## Rules that live in Google Docs Daniel edits directly

Read these fresh on every run — they are the source of truth, not any copy in this repo.

- **Scope & Search Vocabulary** (`1VcU78QCMR0Az9N-l-mVidFe5Qsu6ZvoD-xB6RzD9ScQ`): Section 0 = the single list of in-scope hardware and services; Section 1 = search keywords; Section 2 = services vocabulary for the Services Offered column.
- **Near Miss Rules** (`1C6BGckrgU-5j7MPfMriWdw_3pPuqqAPg3Q8oYsc9_Wg`): near-miss bands and where each near miss goes.

## Related docs (context, not written to by this skill)

- Power OEM database: `1yGu0zjSbpqmb1ysvjsSvL8CdbDtyMz7GfBQe2X4MTRA` — useful for recognizing OEM names when filling Key OEM Partnerships.
- 2023 Aurias 1 contact-enrichment precedent sheet: `1jScEMUN6XppcdBzwqyf4SbUUOQcQh4mujLvCCKHHOOs` — shows this exact discipline (PSC chase, blank-over-guess) working in practice.
