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

## The workflow

### 1. Pick up where the sheet leaves off

Read the Market Map tab's Company Name and Website columns (via `sheets_api.sh read`) to find rows that have a name but are still missing the rest of the template — that's your queue. Don't re-enrich a row that's already been filled in and given a Screening Verdict; that's the verifier's job to check, not yours to redo.

### 0. Never delete a row unless it's a confirmed exact duplicate

**Hard rule (Daniel, 2026-09-17): "I would not expect the skill to delete entries unless they are duplicates."** Not a judgment call — a company row only ever gets removed when it's a confirmed duplicate of another row for the same company (and even then, log which row you kept and why in your batch report). Every other row stays, no matter how it looks — out-of-scope, badly enriched, whatever. This is the same principle as "map the whole market, mark out-of-scope rather than drop" already in this Skill, just stated as an explicit boundary after a real incident where rows were lost by accident rather than by any deliberate decision to remove them.

### 1a. Count before you touch anything

Before writing, count the total non-blank rows in the Company Name column and note it. After writing the batch, count again. **The count should only ever stay the same or grow — never shrink.** A shrinking count means rows were lost somewhere, even if the batch you meant to write looks fine on a read-back. This is the cheapest possible check against the exact failure described in step 5 below, so don't skip it because it feels redundant with the read-back verification.

### 2. Work in batches of 5

Take five companies at a time, fully research and verify all of them, write that batch to the sheet, then move to the next five. This isn't a formality — Daniel asked for it specifically because long, unbroken research runs are exactly where an agent's accuracy tends to drift (this was raised directly when we researched why a Claude agent might "hallucinate after a small number of accurate results" — the fix isn't a different tool, it's disciplined batching and verification, which is what this whole workflow is built around). Five is small enough to genuinely fact-check each one, not so small that progress crawls.

You can run through as many batches as needed in one sitting — there's no need to stop and wait for approval between batches, since this is filling in blanks, not overwriting existing data. Do post a short one-line note after each batch (companies covered, anything flagged) so progress stays visible.

### 3. Research each company

Default sources, in the order they're normally most reliable for this market: **Companies House** (identity, financials, PSC/ownership), **LinkedIn** via Daniel's own logged-in Chrome (headcount, people, company page), **Google Search**, **Google Maps** (address, phone, sometimes the fastest way to confirm a company is still trading). Daniel's given you discretion to use any other source you judge genuinely useful for accuracy or efficiency — use it, but the same rule applies regardless of source: **verify before you write, and leave it blank if you can't.**

Fill in every field per `references/data-template.md`. Three fields have specific formatting rules worth restating here because they're easy to default into a lazier shorthand:

- **Employees - Companies House (K)** — added 2026-09-17: pull the "average number of employees" note from the filed accounts for every company, not just when LinkedIn is ambiguous. It's the anchor headcount signal alongside Associated Members (J) — use whichever of the two (plus the LinkedIn band) is largest, per `references/data-template.md`'s sizing heuristic.
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

**As of 2026-09-18, headcount isn't the only route to qualifying.** Also check Profit Before Tax (column N) against the "Financial performance signals" section of `references/data-template.md` — a PBT of £1m-£10m qualifies a company independently of headcount, unless it's PE/large-group owned, in which case that goes to Daniel as a flag rather than an automatic call. Revenue between £10m-£50m gets its own Notes flag for Daniel regardless of what else the row shows. Neither of these financial checks is optional just because headcount already gave you a clean verdict — run both checks on every company, every time.

### 7. Qualified leads get copied, not moved

If a company's Screening Verdict comes out In-scope via **either** the headcount path or the PBT path (see step 6 and `references/data-template.md`), use `sheets_api.sh append` to add the same row to the **Qualified Leads** tab. The row on Market Map stays exactly as it is — this is a copy for visibility, not a move. Everyone stays mapped, per the existing "map the whole market" rule; Qualified Leads is just the shortlist view on top of it.

If the Qualified Leads tab doesn't yet have a header row matching the Market Map columns, add one first (same 29 columns, same order) so the two tabs stay directly comparable.

### 8. Keep the sheet readable

Daniel wants this sheet "neatly formatted, well presented and easy to read" — not just correct. Use `sheets_api.sh format` (wraps the general `spreadsheets.batchUpdate` endpoint) to apply standard presentation once per sheet if it isn't already there: bold + frozen header row, sensible column widths, and consider light row banding for readability on a sheet this long. Formatting is a one-time/idempotent housekeeping step, not something to redo every batch — check with `sheets_api.sh meta` first if you're unsure whether it's already applied.

### 9. Hand off to verification, every time

Once a batch is written and verified-readable, invoke the `generator-ups-data-verification` Skill on that same batch before moving on. This isn't optional or occasional — Daniel wants every batch checked, not a sample, so the accuracy tracking it produces (see that Skill's scoring section) reflects the whole pipeline, not a cherry-picked slice.

## Not this skill's job

Finding brand-new companies to add to the sheet (a separate skill, built to cover that side of the pipeline). Independent verification/QA of data already on the sheet — that's `sourcing-verifier`. Deciding sub-sector scope changes. Drafting outreach. Valuation. Anything touching legal or financial commitments. If you hit one of these, hand it back to Athena rather than doing it yourself.
