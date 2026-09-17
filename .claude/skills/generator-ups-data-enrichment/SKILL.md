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

### 2. Work in batches of 5

Take five companies at a time, fully research and verify all of them, write that batch to the sheet, then move to the next five. This isn't a formality — Daniel asked for it specifically because long, unbroken research runs are exactly where an agent's accuracy tends to drift (this was raised directly when we researched why a Claude agent might "hallucinate after a small number of accurate results" — the fix isn't a different tool, it's disciplined batching and verification, which is what this whole workflow is built around). Five is small enough to genuinely fact-check each one, not so small that progress crawls.

You can run through as many batches as needed in one sitting — there's no need to stop and wait for approval between batches, since this is filling in blanks, not overwriting existing data. Do post a short one-line note after each batch (companies covered, anything flagged) so progress stays visible.

### 3. Research each company

Default sources, in the order they're normally most reliable for this market: **Companies House** (identity, financials, PSC/ownership), **LinkedIn** via Daniel's own logged-in Chrome (headcount, people, company page), **Google Search**, **Google Maps** (address, phone, sometimes the fastest way to confirm a company is still trading). Daniel's given you discretion to use any other source you judge genuinely useful for accuracy or efficiency — use it, but the same rule applies regardless of source: **verify before you write, and leave it blank if you can't.**

Fill in every field per `references/data-template.md`. Three fields have specific formatting rules worth restating here because they're easy to default into a lazier shorthand:

- **Equipment Category (H)** — every category the company genuinely offers, not just the headline one.
- **Key OEM Partnerships (W)** — paired to the category it belongs to, e.g. `Generator - Cummins, Perkins; Load bank - Crestchic`.
- **Type-Spec / Resale-Rental-Service (X)** — each applicable one spelled out individually, never "all" or "both".

And the two rules that protect against the most damaging kind of wrong answer:
- **PSC must resolve to a named human being**, chased up the ownership chain as far as it takes (`references/data-template.md` has the full procedure and worked examples).
- **Never a generic email address** (info@, sales@, hello@, etc.) in PSC Email or CEO/MD Email — a real person's direct address, verified where possible, or blank.

### 4. Spawn helper agents when it speeds things up without costing accuracy

You have discretion to use the Agent tool to parallelize research within a batch — for example, one helper agent per company doing the raw Companies House/LinkedIn/web lookups simultaneously, rather than one agent working through all 5 in sequence. Close each helper once it's reported back.

Keep the verification and the actual sheet write centralized in you, the orchestrating agent, rather than letting helpers write directly — that way five parallel lookups can't race each other on the same batch write, and you get one last chance to sanity-check everything before it hits the live sheet. Treat a fact a helper agent returns the same way you'd treat one you found yourself: if it isn't independently checkable against a primary source, it doesn't go in as a stated fact.

### 5. Write the batch

Use `sheets_api.sh batch` to write all 5 rows in one atomic call rather than 5 separate writes — this is exactly what the script's `batch` mode wraps. Always read the affected range back afterward to confirm the write landed as expected before moving to the next batch.

### 6. Triage with the headcount heuristic

Apply the 30–100 headcount sizing band from `references/data-template.md` to help decide the Screening Verdict. This is a triage aid, not the only input — check Ultimate Owner too, since a large group figure can mask a right-sized subsidiary.

### 7. Qualified leads get copied, not moved

If a company's Screening Verdict comes out In-scope (or otherwise looks like a genuine qualified lead), use `sheets_api.sh append` to add the same row to the **Qualified Leads** tab. The row on Market Map stays exactly as it is — this is a copy for visibility, not a move. Everyone stays mapped, per the existing "map the whole market" rule; Qualified Leads is just the shortlist view on top of it.

If the Qualified Leads tab doesn't yet have a header row matching the Market Map columns, add one first (same 29 columns, same order) so the two tabs stay directly comparable.

### 8. Keep the sheet readable

Daniel wants this sheet "neatly formatted, well presented and easy to read" — not just correct. Use `sheets_api.sh format` (wraps the general `spreadsheets.batchUpdate` endpoint) to apply standard presentation once per sheet if it isn't already there: bold + frozen header row, sensible column widths, and consider light row banding for readability on a sheet this long. Formatting is a one-time/idempotent housekeeping step, not something to redo every batch — check with `sheets_api.sh meta` first if you're unsure whether it's already applied.

## Not this skill's job

Finding brand-new companies to add to the sheet (a separate skill, built to cover that side of the pipeline). Independent verification/QA of data already on the sheet — that's `sourcing-verifier`. Deciding sub-sector scope changes. Drafting outreach. Valuation. Anything touching legal or financial commitments. If you hit one of these, hand it back to Athena rather than doing it yourself.
