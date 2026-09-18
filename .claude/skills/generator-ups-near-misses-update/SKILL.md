---
name: generator-ups-near-misses-update
description: "Also known as: \"Generator + UPS Data Verification - Near misses update\". Monthly re-check of companies on Daniel's Aurias 2 \"Master UK generator and UPS Market Map\" that sat just outside one of the three screening thresholds (headcount, Profit Before Tax, or Revenue) when they were last enriched. Reads each company's own \"Accounts Next Due - Companies House\" date straight off the sheet (column AE) to decide who's actually due a re-check, so most months this needs zero Companies House calls at all — only companies whose due date has passed get the expensive re-pull. Reclassifies to \"Needs more info\" / Flagged to You where a fresh figure (or, for headcount only, plain staleness) no longer supports the existing Out-of-scope verdict. Use this for the scheduled monthly sweep, or on demand if Daniel asks to re-check near-miss companies. Does NOT re-enrich a whole batch, re-verify PSC/ownership/contacts, or decide anything itself beyond re-running the three screening checks — that's `generator-ups-data-enrichment`'s job if a row needs a fuller pass.
---

# Generator + UPS near-misses update

Once a month, sweep the companies that were ruled Out-of-scope for sitting *just* outside one of the three screening thresholds — headcount, Profit Before Tax, or Revenue — and check whether that call still holds up. This started with Addicott Electrics (2026-09-18): its Companies House headcount (28) was accurate at the time, but a year from now that same filing will be well over 12 months old, and the real business may have grown past 30 in the meantime. Extended the same day to cover PBT and Revenue too (Daniel: "we have three types of criteria to measure whether something is a pass, the near miss should measure all three of those") — the same aging-data problem applies to all three, since they all come from the same annual filing.

**Why a separate Skill rather than folding this into enrichment or verification:** those two run *per batch*, right after new data is written. This runs on a *calendar cadence*, over rows that might not have been touched in months. Different trigger, different rhythm — worth keeping separate rather than overloading either existing Skill with a job it doesn't naturally do.

## Where things are

Same sheet, same script, same rules as the enrichment Skill — nothing here has its own copy:

- Master sheet, credentials, sharing notes: `.claude/skills/generator-ups-data-enrichment/references/live-resources.md`
- The screening thresholds themselves: `.claude/skills/generator-ups-data-enrichment/references/data-template.md` — read "The sizing heuristic," "Stale Companies House headcount near the 30-employee floor," and "Financial performance signals" before starting, don't work from memory.
- Shared write-safety rules (row-identity re-verification, never delete a non-duplicate row, character encoding, the batch lock protocols): `.claude/skills/generator-ups-data-enrichment/references/sheet-write-safety.md` — same rules this sweep is also bound by, canonical version lives there.
- Bundled Sheets API script: `.claude/skills/generator-ups-data-enrichment/scripts/sheets_api.sh`
- Log tab: **Near-Miss Review Log** on the master sheet — one row per monthly run, not per company (see "Logging" below).

## When this runs

Monthly, at month-end, via the scheduled task `generator-ups-near-misses-monthly`. Can also be run on demand if Daniel asks for a near-miss re-check outside the schedule — same steps either way.

## The workflow

### 0. Check whether the Near Miss Rules doc changed — this can trigger a full resweep, not just the routine one

**Added 2026-09-18 (Daniel: "when I change the numbers in the document it should apply retroactively and trigger a review of companies that may fall within the new bandings... especially relevant when lowering the bottom band").** Read `Automation Status!A3:C3` for the last-seen `modifiedTime` of the Near Miss Rules Google Doc (`1C6BGckrgU-5j7MPfMriWdw_3pPuqqAPg3Q8oYsc9_Wg`). Compare it against the doc's actual current `modifiedTime` (Drive file metadata).

- **If unchanged**, proceed with the routine sweep below exactly as normal (near-miss set built from the current bands, gated behind AE as usual).
- **If the doc has changed**, this is a **full backlog resweep**, not the routine monthly one: re-check **every currently Out-of-scope row on the Market Map** against the *new* bands read fresh from the doc — not just rows that were already near-misses under the old bands. A row that wasn't close enough to matter under the old numbers can become a genuine near-miss under a lowered floor (Daniel's own example: lowering the PBT floor pulls in rows that were previously well clear of it). This resweep doesn't wait for AE due dates the way the routine sweep does for *new* data — you're not waiting for anything new to exist, you're re-applying updated rules to figures you already have, so check every row's already-recorded K/M/N figures against the new bands immediately. Only fall through to an actual Companies House re-pull (steps 2-3 below) for rows where the *routine* staleness/newly-disclosed logic would separately apply.
- After the resweep completes (routine or full), **update `Automation Status!B3` to the doc's current `modifiedTime`** so the next run doesn't redo a full resweep unnecessarily.
- Log a full resweep distinctly in the Near-Miss Review Log's Details column (e.g. "Full resweep triggered by Near Miss Rules doc change — bands now X/Y/Z") so it's clearly distinguishable from a routine month-end run.

### 1. Find the near-miss set

**Read this carefully — headcount and the financial figures (PBT/Revenue) now work differently (updated 2026-09-18).** Since that date, the enrichment Skill itself catches a PBT near-miss (£700k-£1m) immediately, unconditionally, at write time — it never waits for this monthly sweep (Daniel: "no harm in approaching companies that are near misses... we do not lose anything"). So this Skill's PBT/Revenue role going forward is narrower than headcount's:

- **Headcount near-miss (the sweep's main ongoing job)**: read the Market Map's Screening Verdict (AB — moved here from AC on 2026-09-18 when Sources moved to the end) and Employees - Companies House (K) columns. A row belongs in the near-miss set if it's **Out-of-scope specifically on headcount** and working headcount (larger of Associated Members and Companies House employees) landed in roughly **20-29** — just under the 30 floor. This band is a working default, not a precision-tested number — open to adjustment if Daniel wants it wider or narrower.
- **PBT/Revenue backlog check (a one-time-per-row concern, not ongoing)**: any row enriched *before* 2026-09-18 could have been disqualified on a PBT near-miss (£700k-£1m) or a missed Revenue flag (£10-50m) under the old logic, since that rule didn't exist yet. Check for this once per row the first time this sweep touches it — if found, fix it the same way enrichment would now (Needs more info + Flagged to You), no need to wait for a new filing since you already have the figure that shows it. (A full backlog sweep was done manually on 2026-09-18 covering everything enriched up to that point — this is here so a future rebuild of this Skill doesn't have to rediscover the need for it.)
- **PBT/Revenue newly-disclosed check (the actual ongoing role for financials)**: a row where PBT/Revenue was recorded as "not disclosed" (Section 444 exemption, micro-entity accounts, etc.) is worth re-checking once a newer filing might exist — that filing could newly disclose a PBT/Revenue figure that didn't exist to check before. This is gated by AE exactly like headcount (see step 2) — there's no figure to re-derive from staleness alone here, only a genuinely new filing can help.

A row can need more than one of these checks at once — go through all three for every Out-of-scope row, don't stop at the first match.

### 2. Gate the expensive re-check behind column AD — this is the "don't run unnecessary calls" step

Both remaining ongoing checks (headcount staleness, and newly-disclosed PBT/Revenue) depend on whether a new Companies House filing has actually landed. There's no point re-pulling and re-parsing that filing every month if nothing could plausibly have changed since the last check — and as of 2026-09-18, there's no need to even ask Companies House whether it's changed, because the answer is already sitting on the sheet.

1. For each row in the near-miss set, **read column AD (Accounts Next Due - Companies House) directly off the sheet — moved here from AE on 2026-09-18** — no Companies House call needed for this step at all (Daniel, 2026-09-18: "you don't even need to bother checking Companies House if we already have that information... we only have to do it the once"). AE was captured the last time this company was enriched or re-checked, and records the exact date the next filing is due.
2. **If today is still before the date in AE, skip this company entirely this run** — no LinkedIn re-check, no Companies House call. The current filing is still the only one that will ever exist for this row until that date. Note it in the log as "checked, not yet due (AE: [date])" rather than silently omitting it.
3. **If today is on/after the date in AE, go to step 3 below** — this is the only case that costs an actual Companies House call.

This is the entire point of AE existing: most months, most rows get skipped after a free local read, with zero external calls. The only Companies House traffic this Skill generates is for rows whose own recorded due date has actually passed — and by construction, a row only reaches that state once its period-end is already close to the 12-month staleness mark (UK filing deadlines are ~9 months after period-end), so skipping on AE never risks missing a genuinely stale headcount case.

### 3. When AE says a company is due — check what Companies House actually shows

1. Fetch the company's Companies House overview page. Two possible outcomes:
   - **A newer filing has actually landed** (the normal case): pull it and extract **all three figures at once** — average employees, PBT, and Revenue, since they're all in the same document, no reason to fetch it three times. Re-pull current LinkedIn Associated Members too (a live number) and recompute working headcount per the sizing heuristic. Re-run the checks: headcount now 30+, PBT now qualifying or a near-miss (£700k-£10m — near-miss and qualifying both flag now, per step 1), or Revenue now £10m-£50m (subject to the existing PE/large-group flag logic in `data-template.md` for PBT — check that too). **Update column AE to the new "accounts next due" date regardless of what else changes** — this is what keeps next month's free local read in step 2 accurate.
   - **The company is late filing** — AE has passed but no newer filing exists yet. Nothing to extract for PBT/Revenue (there's no new document, so a newly-disclosed figure literally can't exist yet — leave that check for next time). Headcount still gets checked though: if the *already-recorded* Companies House employee figure's period-end is now more than 12 months old, that's reason enough not to trust an Out-of-scope-on-headcount verdict, per the existing stale-headcount rule. Leave AE as-is in this case; note in the log that the company is overdue and was flagged (or not) on staleness alone.
2. **If any check now points away from Out-of-scope**, don't decide the full verdict yourself — that needs the fuller checks (ownership, disqualifiers) that only a proper enrichment pass does. Set Screening Verdict to **"Needs more info"**, note which figure changed and how (old value → new value, with source), and copy the row to **Flagged to You**. **Re-read the row's Company Name right before you write to it, don't trust a row number from earlier in the sweep** — see `generator-ups-data-enrichment/references/sheet-write-safety.md` (section 2) for the full rule and the incidents behind it; the same risk applies here any time this sweep runs long enough for a concurrent edit (Daniel, another agent, anything that inserts/deletes a row) to shift rows underneath it — a monthly sweep touching many rows over a longer run is exactly the kind of window where that matters.
3. **If, even with fresh figures, nothing clears**, leave the row as Out-of-scope — but update the recorded K/M/N figures (and AE) to the fresh values regardless, so the next sweep starts from current data, not last year's. Log the recheck as "confirmed still Out-of-scope."

### 4. Logging — one row per run, not per company

Append one row to the **Near-Miss Review Log** tab (via `sheets_api.sh append` against `Near-Miss Review Log!A:F`) summarizing the whole sweep: Date, Companies Checked (count — this means everything in the near-miss set, including ones skipped as "not yet due"), Companies Reclassified (count + names), Companies Confirmed Still Out-of-Scope (count), Details (one line per company that got a fresh check — old figure(s) vs new, which axis triggered it if reclassified, or "not yet due" if skipped), Run By ("generator-ups-near-misses-update"). This is a different shape of record than the per-batch Verification Log (which scores enrichment accuracy) — don't write into that tab, this is a periodic sweep, not a QA pass on freshly-written data.

If the near-miss set is empty, still log a row saying so — an empty run is itself a useful data point.

### 5. Tell Daniel what happened

A short note: how many companies were in the near-miss set, how many were actually due for a re-check vs. skipped as premature, how many got reclassified and on which axis, and a pointer to Flagged to You if anything landed there. Don't over-explain what didn't change.

## What this Skill never does

Re-verify PSC, ownership, or contacts — only headcount, PBT, and Revenue. Re-pull a full accounts filing for a company that isn't yet due new accounts. Auto-qualify anything into Qualified Leads directly — a reclassification always goes through "Needs more info" / Flagged to You first, same as any other borderline call. Edit a row that wasn't part of the near-miss set. Run more often than the schedule calls for without being asked.
