---
name: generator-ups-near-misses-update
description: "Also known as: \"Generator + UPS Data Verification - Near misses update\". Monthly re-check of companies on Daniel's Aurias 2 \"Master UK generator and UPS Market Map\" that sat just outside one of the three screening thresholds (headcount, Profit Before Tax, or Revenue) when they were last enriched. All three figures come from filed Companies House accounts, which only change once a year — so this Skill checks each company's own \"next accounts due\" date first and only does the expensive re-pull once new accounts are actually due, instead of re-querying every near-miss company every month regardless. Reclassifies to \"Needs more info\" / Flagged to You where a fresh figure (or, for headcount only, plain staleness) no longer supports the existing Out-of-scope verdict. Use this for the scheduled monthly sweep, or on demand if Daniel asks to re-check near-miss companies. Does NOT re-enrich a whole batch, re-verify PSC/ownership/contacts, or decide anything itself beyond re-running the three screening checks — that's `generator-ups-data-enrichment`'s job if a row needs a fuller pass.
---

# Generator + UPS near-misses update

Once a month, sweep the companies that were ruled Out-of-scope for sitting *just* outside one of the three screening thresholds — headcount, Profit Before Tax, or Revenue — and check whether that call still holds up. This started with Addicott Electrics (2026-09-18): its Companies House headcount (28) was accurate at the time, but a year from now that same filing will be well over 12 months old, and the real business may have grown past 30 in the meantime. Extended the same day to cover PBT and Revenue too (Daniel: "we have three types of criteria to measure whether something is a pass, the near miss should measure all three of those") — the same aging-data problem applies to all three, since they all come from the same annual filing.

**Why a separate Skill rather than folding this into enrichment or verification:** those two run *per batch*, right after new data is written. This runs on a *calendar cadence*, over rows that might not have been touched in months. Different trigger, different rhythm — worth keeping separate rather than overloading either existing Skill with a job it doesn't naturally do.

## Where things are

Same sheet, same script, same rules as the enrichment Skill — nothing here has its own copy:

- Master sheet, credentials, sharing notes: `.claude/skills/generator-ups-data-enrichment/references/live-resources.md`
- The screening thresholds themselves: `.claude/skills/generator-ups-data-enrichment/references/data-template.md` — read "The sizing heuristic," "Stale Companies House headcount near the 30-employee floor," and "Financial performance signals" before starting, don't work from memory.
- Bundled Sheets API script: `.claude/skills/generator-ups-data-enrichment/scripts/sheets_api.sh`
- Log tab: **Near-Miss Review Log** on the master sheet — one row per monthly run, not per company (see "Logging" below).

## When this runs

Monthly, at month-end, via the scheduled task `generator-ups-near-misses-monthly`. Can also be run on demand if Daniel asks for a near-miss re-check outside the schedule — same steps either way.

## The workflow

### 1. Find the near-miss set — all three criteria, not just headcount

Read the Market Map's Screening Verdict (AC), Notes (AD), Employees - Companies House (K), Revenue (M), and Profit Before Tax (N) columns. A row belongs in the near-miss set if it's currently **Out-of-scope** and any of the following is true of the figure that drove that verdict:

- **Headcount near-miss**: working headcount (larger of Associated Members and Companies House employees) landed in roughly **20-29** — just under the 30 floor.
- **PBT near-miss**: recorded PBT landed in roughly **£700k-£1m** — just under the £1m qualifying floor for the financial-performance path. (This Skill only tracks the *lower* PBT boundary, not the £10m "too large" ceiling — a company that's too big on PBT getting bigger isn't a new find, so there's nothing to gain re-checking that direction. If Daniel wants that tracked too, it's a one-line addition to this section.)
- **Revenue near-miss**: recorded Revenue landed in roughly **£8m-£10m** — just under the floor of the £10m-£50m Notes-flag band. (Same asymmetry as PBT: crossing into the band only adds a Notes flag, but a company already inside or above the band getting bigger isn't something this Skill needs to chase.)

These bands (20-29, £700k-£1m, £8m-£10m) are working defaults, not precision-tested numbers — reasonable buffers below each real threshold, open to adjustment if Daniel wants them wider or narrower. A company that's clearly outside all three bands (e.g. 5 employees, £50k PBT) isn't a near-miss on any axis and doesn't belong in this sweep.

A row can be a near-miss on more than one axis at once — check all three for every candidate row, don't stop at the first match.

### 2. Gate the expensive re-check behind the accounts due date — this is the "don't run unnecessary calls" step

All three figures come from the same filed Companies House accounts, which only update once a year. There's no point re-pulling and re-parsing that filing every month if nothing could plausibly have changed since the last check.

1. For each near-miss row, do one **cheap** check first: fetch the company's Companies House overview page and read its own published **"Accounts next due"** / **"Next statement date"** field, and the **"last accounts made up to"** date. (Background: private companies must file within 9 months of their accounting reference date — Companies House does this arithmetic for you and publishes the answer directly, so use its own date rather than recomputing it.)
2. **Only proceed to the full re-pull (step 3) if either:** (a) the "last accounts made up to" date shown is *newer* than the period-end already recorded on the sheet for this company (a new filing has genuinely landed), or (b) today is on/after the "accounts next due" date shown (accounts are now overdue, which sometimes happens, but still means nothing new is available yet — see the headcount-only staleness fallback in step 4 for this case).
3. If neither is true — the recorded filing is still current and nothing new is due yet — **skip this company entirely this run.** Don't re-pull LinkedIn for it either. Note it in the log as "checked, not yet due" rather than silently omitting it.

This step is what keeps the sweep cheap: most months, most near-miss companies will still be within their filing cycle and get skipped after one lightweight overview-page check, not a full accounts re-pull.

### 3. Full re-pull — when a newer filing exists

When step 2 confirms a newer filing is available:

1. Pull the new accounts and extract **all three figures at once** — average employees, PBT, and Revenue — since they're in the same document; there's no reason to fetch it three times.
2. Re-pull current LinkedIn Associated Members too (a live number, no staleness concept applies — just get the current count), and recompute working headcount per the sizing heuristic.
3. Re-run all three screening checks against the fresh figures:
   - Headcount now 30+ → no longer Out-of-scope on headcount.
   - PBT now £1m-£10m → qualifies via the financial-performance path (subject to the existing PE/large-group flag logic in `data-template.md` — check that too, don't skip it just because this is a re-check).
   - Revenue now £10m-£50m → gets the Notes flag.
4. If **any** of the three now clears its threshold, or genuinely can't be resolved either way, don't decide the full verdict yourself — that needs the fuller checks (ownership, disqualifiers) that only a proper enrichment pass does. Set Screening Verdict to **"Needs more info"**, note which figure changed and how (old value → new value, with source), and copy the row to **Flagged to You**.
5. If, even with fresh figures, none of the three thresholds are cleared, leave the row as Out-of-scope — but update the recorded K/M/N figures and their Sources/Notes to the fresh values regardless (so the next sweep starts from current data, not last year's), and log the recheck as "confirmed still Out-of-scope."

### 4. Headcount-only staleness fallback — when no new filing exists but the figure is old anyway

If step 2 found no newer filing (still within the normal filing cycle, nothing overdue), the PBT and Revenue figures literally cannot have changed in our data — skip them, there's nothing to re-check. But headcount gets one more check even without new data: if the recorded Companies House employee figure's period-end is now **more than 12 months old**, that's still reason enough not to trust an Out-of-scope-on-headcount verdict, per the existing stale-headcount rule — set "Needs more info" and copy to Flagged to You, noting the figure is stale with no fresher filing yet available to resolve it. This fallback only applies to headcount, not PBT/Revenue, because LinkedIn gives an independent (if imperfect) live corroborating signal for headcount that has no equivalent for financial figures — there's no "LinkedIn revenue."

### 5. Logging — one row per run, not per company

Append one row to the **Near-Miss Review Log** tab (via `sheets_api.sh append` against `Near-Miss Review Log!A:F`) summarizing the whole sweep: Date, Companies Checked (count — this means everything in the near-miss set, including ones skipped as "not yet due"), Companies Reclassified (count + names), Companies Confirmed Still Out-of-Scope (count), Details (one line per company that got a fresh check — old figure(s) vs new, which axis triggered it if reclassified, or "not yet due" if skipped), Run By ("generator-ups-near-misses-update"). This is a different shape of record than the per-batch Verification Log (which scores enrichment accuracy) — don't write into that tab, this is a periodic sweep, not a QA pass on freshly-written data.

If the near-miss set is empty, still log a row saying so — an empty run is itself a useful data point.

### 6. Tell Daniel what happened

A short note: how many companies were in the near-miss set, how many were actually due for a re-check vs. skipped as premature, how many got reclassified and on which axis, and a pointer to Flagged to You if anything landed there. Don't over-explain what didn't change.

## What this Skill never does

Re-verify PSC, ownership, or contacts — only headcount, PBT, and Revenue. Re-pull a full accounts filing for a company that isn't yet due new accounts. Auto-qualify anything into Qualified Leads directly — a reclassification always goes through "Needs more info" / Flagged to You first, same as any other borderline call. Edit a row that wasn't part of the near-miss set. Run more often than the schedule calls for without being asked.
