---
name: generator-ups-data-enrichment
description: Enriches company rows on Daniel's Aurias 2 "Master UK generator and UPS Market Map" Google Sheet — filling in Companies House financials, LinkedIn headcount, ownership/PSC chased to a named person, CEO/MD contacts, OEM partnerships, and screening verdict for companies that are already on the sheet but only have a name and maybe a website. Use this any time the task is enriching, filling in, completing, or verifying data on that market map — for the 7 in-scope categories (UPS, backup generators, transformers, battery energy storage/BESS, switchgear, load banks, critical power services). Does NOT find brand-new companies to add to the sheet (a separate skill handles that) and does NOT do independent QA verification of already-entered data (that's the sourcing-verifier agent's job) — this skill only fills in blanks on rows that already exist.
---

# Generator + UPS data enrichment

You're filling in the gaps on Daniel Cardenas-Clark's live Aurias 2 market map — a company is already a row on the sheet (at minimum a Name, usually a Website too), and your job is to research and populate the rest of the template fields for it, accurately, then hand off anything that qualifies.

Read `C:\Users\HP\OneDrive\Desktop\Claude — OS\ATHENA.md` first for house style and hard rules (autonomy limits, confidentiality, LinkedIn hard line) — they apply here too.

**The one thing that matters more than speed: accuracy.** Daniel's explicit brief for this skill was "no hallucinations." A blank cell costs nothing — someone can fill it in later. A wrong cell that looks confident is actively harmful: it gets trusted, gets acted on, and the error compounds. Every rule below exists in service of that one priority.

## Where things are

- **Master sheet** (the only place this skill writes real data), **template** (reference only), credentials, and the current sharing situation: `references/live-resources.md` — read this first, every time, since IDs and access can change.
- **Full field-by-field template**, the sizing heuristic, the PSC-chase procedure, and the contact rules: `references/data-template.md` — read this before starting a batch, don't work from memory of a previous run.
- **Bundled script** for all sheet reads/writes: `scripts/sheets_api.sh` — use this instead of hand-writing curl calls. Run it with no arguments to see the usage for each mode (`read`, `write`, `clear`, `batch`, `append`, `format`, `meta`).

## Scope

Only these 7 categories: UPS, critical power services, backup generators, transformers, battery energy storage systems (BESS), switchgears, load banks. If a company on the sheet turns out to be clearly outside all 7, that's a Screening Verdict of Out-of-scope with a reason — not something to silently skip past.

## LinkedIn work requires the Claude-in-Chrome tool — load it before you need it, not after

**Added 2026-09-18, after several batches quietly fell back to WebSearch/WebFetch for LinkedIn and got it wrong or left profiles blank.** LinkedIn mostly won't render to a logged-out session, and WebSearch only sees Google's sparse, stale index of it — that's how a real "James Richardson" working at Greenshields JCB gets missed while unrelated same-name profiles at other companies show up instead. The `sourcing` agent's own definition (`.claude/agents/sourcing.md`) already says to use Daniel's logged-in Chrome for anything on LinkedIn, and lists `claude-in-chrome` as an available MCP server — but that's not automatic. **At the start of any batch, load it explicitly** (`ToolSearch` for `mcp__claude-in-chrome__*`) and use LinkedIn's own logged-in search (`https://www.linkedin.com/search/results/people/?keywords=...`) for every PSC/CEO/MD LinkedIn lookup, rather than reaching for WebSearch/WebFetch first and only falling back to the browser if that fails. If the browser tool is genuinely unavailable in your context, say so explicitly in your batch report rather than silently leaving the field blank or accepting a low-confidence match — that's a tooling gap worth fixing, not a normal "couldn't find it."

## The workflow

### 1. Check the batch lock, then pick up where the sheet leaves off

**Added 2026-09-18, needed once batches started running unattended overnight:** before doing anything else, read `Automation Status!A2:C2` on the master sheet. If Status (column B) is `FREE`, you're clear — write `IN_PROGRESS since <ISO timestamp>, rows <range>` into it immediately, before you start researching, so a scheduled task or another dispatch can't start the same batch in parallel. If Status already shows `IN_PROGRESS`, **stop — don't start a batch.** Report back that a batch is already running rather than duplicating work or racing another agent on the same rows. Set it back to `FREE` as the very last thing you do, after the batch is written, verified, and handed off — not before. If you ever hit an unrecoverable error mid-batch, still set it back to `FREE` before stopping, so the lock doesn't jam the pipeline for whoever runs next.

Read the Market Map tab's Company Name and Website columns (via `sheets_api.sh read`) to find rows that have a name but are still missing the rest of the template — that's your queue. Don't re-enrich a row that's already been filled in and given a Screening Verdict; that's the verifier's job to check, not yours to redo.

### 0. Never delete a row unless it's a confirmed exact duplicate

**Hard rule (Daniel, 2026-09-17): "I would not expect the skill to delete entries unless they are duplicates."** Not a judgment call — a company row only ever gets removed when it's a confirmed duplicate of another row for the same company (and even then, log which row you kept and why in your batch report). Every other row stays, no matter how it looks — out-of-scope, badly enriched, whatever. This is the same principle as "map the whole market, mark out-of-scope rather than drop" already in this Skill, just stated as an explicit boundary after a real incident where rows were lost by accident rather than by any deliberate decision to remove them.

### 1a. Count before you touch anything

Before writing, count the total non-blank rows in the Company Name column and note it. After writing the batch, count again. **The count should only ever stay the same or grow — never shrink.** A shrinking count means rows were lost somewhere, even if the batch you meant to write looks fine on a read-back. This is the cheapest possible check against the exact failure described in step 5 below, so don't skip it because it feels redundant with the read-back verification.

### 1b. Never trust a row number you determined earlier in the run — re-verify identity right before you write

**Added 2026-09-18, after a real incident:** a single-row enrichment cached its target as "row 459" at the start of a long research pass. While it was still working, Daniel manually deleted an unrelated duplicate elsewhere on the sheet, which shifted every row below it up by one — the real row moved to 458. The agent's later write still used the stale "459," landing on what was now an empty row and creating a full duplicate instead of updating the real one. This can happen from *any* concurrent structural change to the sheet, not just Daniel's edits — another dispatched agent, a manual fix, anything that inserts or deletes a row while you're mid-task.

The fix: **immediately before any write, re-read that row's Company Name cell (a single cheap read) and confirm it still matches the company you're about to write.** If it doesn't match — blank, different company, shifted — don't write blindly. Re-locate the row by searching Company Name for the expected company first, then write to wherever it actually is now. This matters most for anything that takes more than a couple of minutes (a single deep-dive row, a batch that hits a slow API), since that's exactly the window where a concurrent edit can land. A cheap read before every write is worth it — a silent duplicate or a write to the wrong row is much more expensive to untangle after the fact.

### 2. Work in batches of 5

Take five companies at a time, fully research and verify all of them, write that batch to the sheet, then move to the next five. This isn't a formality — Daniel asked for it specifically because long, unbroken research runs are exactly where an agent's accuracy tends to drift (this was raised directly when we researched why a Claude agent might "hallucinate after a small number of accurate results" — the fix isn't a different tool, it's disciplined batching and verification, which is what this whole workflow is built around). Five is small enough to genuinely fact-check each one, not so small that progress crawls.

You can run through as many batches as needed in one sitting — there's no need to stop and wait for approval between batches, since this is filling in blanks, not overwriting existing data. Do post a short one-line note after each batch (companies covered, anything flagged) so progress stays visible.

### 3. Research each company

Default sources, in the order they're normally most reliable for this market: **Companies House** (identity, financials, PSC/ownership), **LinkedIn** via Daniel's own logged-in Chrome (headcount, people, company page), **Google Search**, **Google Maps** (address, phone, sometimes the fastest way to confirm a company is still trading). Daniel's given you discretion to use any other source you judge genuinely useful for accuracy or efficiency — use it, but the same rule applies regardless of source: **verify before you write, and leave it blank if you can't.**

Fill in every field per `references/data-template.md`. Three fields have specific formatting rules worth restating here because they're easy to default into a lazier shorthand:

- **Employees - Companies House (K)** — added 2026-09-17: pull the "average number of employees" note from the filed accounts for every company, not just when LinkedIn is ambiguous. It's the anchor headcount signal alongside Associated Members (J) — use whichever of the two (plus the LinkedIn band) is largest, per `references/data-template.md`'s sizing heuristic.
- **Accounts Next Due - Companies House (AD)** — added 2026-09-18 (column moved from AE to AD on 2026-09-18 when Daniel moved Sources to the end): while you're already on the Companies House overview page for K/M/N, also copy its own published "Accounts next due" date. Costs nothing extra, and it's what lets `generator-ups-near-misses-update` check locally whether a company needs a re-check instead of calling Companies House every month for nothing.
- **Equipment Category (H)** — every category the company genuinely offers, not just the headline one.
- **Key OEM Partnerships (X)** — paired to the category it belongs to, e.g. `Generator - Cummins, Perkins; Load bank - Crestchic`.
- **Type-Spec / Resale-Rental-Service (Y)** — each applicable one spelled out individually, never "all" or "both".

And the two rules that protect against the most damaging kind of wrong answer:
- **PSC must resolve to a named human being**, chased up the ownership chain as far as it takes (`references/data-template.md` has the full procedure and worked examples).
- **Never a generic email address** (info@, sales@, hello@, etc.) in PSC Email or CEO/MD Email — a real person's direct address, verified where possible, or blank.

### 4. Spawn helper agents when it speeds things up without costing accuracy

You have discretion to use the Agent tool to parallelize research within a batch — for example, one helper agent per company doing the raw Companies House/LinkedIn/web lookups simultaneously, rather than one agent working through all 5 in sequence. Close each helper once it's reported back.

Keep the verification and the actual sheet write centralized in you, the orchestrating agent, rather than letting helpers write directly — that way five parallel lookups can't race each other on the same batch write, and you get one last chance to sanity-check everything before it hits the live sheet. Treat a fact a helper agent returns the same way you'd treat one you found yourself: if it isn't independently checkable against a primary source, it doesn't go in as a stated fact.

### 5. Write the batch

Use `sheets_api.sh batch` to write all 5 rows in one atomic call rather than 5 separate writes — this is exactly what the script's `batch` mode wraps. Always read the affected range back afterward to confirm the write landed as expected before moving to the next batch.

**Before writing, record the exact row number for each company you're about to update** (not just its name) — read the Company Name in that row and confirm it matches before you write anything into it. **A real incident (2026-09-17):** a re-run of an already-enriched batch ended up writing its results to a *different* set of rows than the ones it read from, which both duplicated one company and silently deleted two entirely unrelated ones further down the sheet (their rows got overwritten). This went undetected until Daniel spot-checked cells directly, well after the batch was reported as complete and verified. Reading a cell back after writing only proves the write landed *somewhere* correct — it doesn't prove nothing else shifted or got clobbered. If you insert, delete, or otherwise restructure rows for any reason during a batch, re-run the row-count and duplicate-name checks below before considering the batch finished, not just a read-back of the cells you meant to touch.

### 6. Triage with the headcount heuristic — and check the financial performance path too

Apply the 30–100 headcount sizing band from `references/data-template.md` to help decide the Screening Verdict. This is a triage aid, not the only input — check Ultimate Owner too, since a large group figure can mask a right-sized subsidiary.

**Headcount is a proxy for the real target, PBT/Revenue — not a co-equal signal (Daniel, 2026-09-18): "number of employees is a proxy for revenue and PBT."** Where PBT/Revenue are actually disclosed, that's the governing figure; headcount is what you fall back on when the financials aren't disclosed (common for the smallest private companies). If both are available and genuinely conflict, go with the financial figure. See "What we're actually screening for" in `references/data-template.md` for the full reasoning.

**Before disqualifying a near-miss on headcount (roughly 20-29), check how old the Companies House figure actually is** (added 2026-09-18, see "Stale Companies House headcount near the 30-employee floor" in `references/data-template.md`) — use the accounts' period-end date, not the filing date. If it's more than 12 months old, don't disqualify on it: set Screening Verdict to "Needs more info" and copy the row to Flagged to You instead, same as the PBT/ownership flag below.

**As of 2026-09-18, headcount isn't the only route to qualifying — and it's not even the primary one.** Also check Profit Before Tax (column N) against the "Financial performance signals" section of `references/data-template.md` — a PBT of £1m-£10m qualifies a company independently of headcount, unless it's PE/large-group owned, in which case that goes to Daniel as a flag rather than an automatic call. **A PBT near-miss (roughly £700k-£1m) never gets a flat Out-of-scope-on-PBT verdict either — it goes to "Needs more info" + Flagged to You, regardless of whether the accounts are fresh or stale** (Daniel, 2026-09-18: "no harm in approaching companies that are near misses... we do not lose anything"). Revenue between £10m-£50m gets its own Notes flag for Daniel regardless of what else the row shows. None of these financial checks is optional just because headcount already gave you a clean verdict — run all of them on every company, every time, and if headcount and a disclosed financial figure ever disagree, the financial figure governs (headcount is only ever a proxy for it).

### 7. Qualified leads get copied, not moved — and so does anything flagged for Daniel

If a company's Screening Verdict comes out In-scope via **either** the headcount path or the PBT path (see step 6 and `references/data-template.md`), use `sheets_api.sh append` to add the same row to the **Qualified Leads** tab. The row on Market Map stays exactly as it is — this is a copy for visibility, not a move. Everyone stays mapped, per the existing "map the whole market" rule; Qualified Leads is just the shortlist view on top of it.

**Added 2026-09-18:** the same copy-not-move pattern applies to a Screening Verdict of "Needs more info" — the case where a company qualifies on one path (usually PBT) but sits inside a PE/large-group ownership structure, so the call is Daniel's rather than automatic (see the "Financial performance signals" section of `references/data-template.md`). Copy that row to the **Flagged to You** tab the same way. Daniel reviews rows there and will move or reclassify them himself once he's decided — this skill's job stops at flagging, not deciding.

If the Qualified Leads or Flagged to You tab doesn't yet have a header row matching the Market Map columns, add one first (same 30 columns, same order) so all tabs stay directly comparable.

### 8. Keep the sheet readable

Daniel wants this sheet "neatly formatted, well presented and easy to read" — not just correct. Use `sheets_api.sh format` (wraps the general `spreadsheets.batchUpdate` endpoint) to apply standard presentation once per sheet if it isn't already there: bold + frozen header row, sensible column widths, and consider light row banding for readability on a sheet this long. Formatting is a one-time/idempotent housekeeping step, not something to redo every batch — check with `sheets_api.sh meta` first if you're unsure whether it's already applied.

### 9. Hand off to verification, every time — as a genuinely separate agent

Once a batch is written and verified-readable, hand off to verification by spawning the **`sourcing-verifier` subagent** (via the Agent tool, `subagent_type: "sourcing-verifier"`) and telling it to run the `generator-ups-data-verification` Skill against this batch. This isn't optional or occasional — Daniel wants every batch checked, not a sample, so the accuracy tracking it produces (see that Skill's scoring section) reflects the whole pipeline, not a cherry-picked slice.

**Use the subagent, don't just load the verification Skill inline in your own context (corrected 2026-09-18).** The verification Skill's "no Edit access by design" boundary only means something if it's actually enforced — and `sourcing-verifier`'s own tool grant genuinely has no Edit or Bash tool, so a verifier running as that subagent physically cannot write to the sheet, whereas you (the enrichment agent) can. The first real batch through this pipeline (2026-09-17/18) showed why this matters: verification found two Notes-column misses and corrected them itself rather than just flagging them, because it was running inline in an agent context that still had full Edit/Bash access — the written rule didn't stop it, since nothing was actually enforcing it. Route through the subagent so the boundary is structural, not just a line in a file.

## Not this skill's job

Finding brand-new companies to add to the sheet (a separate skill, built to cover that side of the pipeline). Independent verification/QA of data already on the sheet — that's `sourcing-verifier`. Deciding sub-sector scope changes. Drafting outreach. Valuation. Anything touching legal or financial commitments. If you hit one of these, hand it back to Athena rather than doing it yourself.
