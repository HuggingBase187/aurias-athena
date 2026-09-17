---
name: generator-ups-data-verification
description: Independently re-verifies every field the generator-ups-data-enrichment Skill just wrote to Daniel's Aurias 2 "Master UK generator and UPS Market Map" Google Sheet — checking Companies House financials, LinkedIn data, ownership/PSC, contacts, and cited sources against primary sources, then logging an accuracy score. Runs automatically right after every enrichment batch. Use this any time the task is checking, verifying, auditing, or scoring the accuracy of data already written to that market map. Never fixes the live data itself — it flags findings and logs a score, nothing more. Does NOT source new companies and does NOT do the enrichment itself — that's generator-ups-data-enrichment's job.
---

# Generator + UPS data verification

You're independent QA on a batch the `generator-ups-data-enrichment` Skill just wrote — not a second enrichment pass. Read `C:\Users\HP\OneDrive\Desktop\Claude — OS\ATHENA.md` and `.claude\agents\sourcing-verifier.md` first — this Skill is that agent's operational playbook, the same relationship the enrichment Skill has with `sourcing.md`.

**Why this exists:** Daniel wants a real, tracked sense of how accurate the enrichment pipeline actually is, not just a one-off spot check — a running accuracy score he can watch over time, not a vague impression that things are "probably fine."

## Where things are

- Sheet IDs, tabs, credentials: `.claude/skills/generator-ups-data-enrichment/references/live-resources.md` (this Skill uses the same master sheet, same script — no separate config).
- Field-by-field rules to check against: `.claude/skills/generator-ups-data-enrichment/references/data-template.md` — read this to know what each column is *supposed* to contain before judging whether it's right.
- Bundled script for all sheet reads/writes: `.claude/skills/generator-ups-data-enrichment/scripts/sheets_api.sh` (same script, reused — no need for a second copy).

## When this runs

Automatically, right after `generator-ups-data-enrichment` finishes writing a batch — the enrichment Skill's own final step hands off to this one. You can also be run on demand (a spot-check on older rows), but the standing behavior is: **every batch gets checked, not a sample of batches.**

## What you check

Every non-blank field the batch just wrote, against primary sources — same scope as `sourcing-verifier.md`:

1. **Company identity** — the row is the real, correctly-matched entity, not a similarly-named different company.
2. **Companies House data** — pull the company by its recorded number and confirm legal name, active status, PSC register match, and that recorded Revenue/PBT actually appear in the filed accounts (or the cited press release actually states them).
3. **LinkedIn data** — reload the company's LinkedIn page via Claude-in-Chrome and confirm Company Size band, Associated Members count, and that the Company LinkedIn URL points to the right company.
3a. **Employees - Companies House (added 2026-09-17)** — pull the filed accounts and confirm the recorded "average number of employees" figure actually matches the note cited. This is now the anchor headcount signal alongside Associated Members — check that the enrichment Skill used the *largest* of the collected signals as its working headcount for the Screening Verdict, not just whichever it found first.
4. **Ownership and people** — Ultimate Owner, PSC Name/LinkedIn/Email/Phone, CEO/MD Name/LinkedIn/Email/Phone all check out against Companies House (PSC) and LinkedIn/the company site respectively. For a PSC chain, confirm it was actually chased to a natural person (or a documented public/PE terminus) rather than stopped early.
5. **Sources column** — each cited source actually supports the fact it's attached to.
6. **Sheet integrity, not just the batch's own fields (added 2026-09-17 after a real incident)** — count the total non-blank rows in the Company Name column and scan for duplicate names anywhere on the sheet, not just within the batch. A real batch once wrote its results to the wrong rows, duplicating one company and silently deleting two unrelated ones elsewhere — the batch's own cells read back as correct, so this only surfaced when Daniel spot-checked the sheet directly. If the row count has dropped since the last logged batch, or a duplicate name shows up, that's a critical error regardless of whether the batch's intended fields look fine.

**A blank field is not automatically correct or automatically wrong — check whether it *should* be blank.** If Revenue is blank because the company filed abridged/micro-entity accounts, that's a correct blank. If Revenue is blank but the filed accounts actually do disclose it, that's a real miss, not a stylistic gap — record it as one (see scoring below).

## What you never do

**Never edit the live Market Map or Qualified Leads data.** You have no Edit access to those by design — this keeps one set of hands off the live data and avoids two Skills overwriting each other. If you find an error, it goes into the Verification Log and gets flagged back to Athena/Daniel to fix via the enrichment Skill, exactly like `sourcing-verifier.md` already describes.

## Scoring and logging

For each batch, compute:

- **Non-blank fields checked** — count every field the enrichment Skill actually wrote a value into for this batch (across all rows in the batch).
- **Fields with errors** — of those, how many are factually wrong (wrong PSC, mismatched LinkedIn page, a figure that doesn't appear in the cited filing, etc.).
- **Accuracy %** — `(non-blank fields checked − fields with errors) ÷ non-blank fields checked × 100`. This measures whether what was written is *correct*, deliberately separate from completeness.
- **Blanks confirmed correct** — blank fields you checked and confirmed genuinely can't be found or don't exist (e.g. no P&L in abridged accounts).
- **Blanks flagged as missed** — blank fields where you found the answer *was* available and the enrichment Skill should have caught it. These don't count against Accuracy % (which is about correctness of what's there, not coverage) but are worth tracking separately, since a Skill that's accurate-but-incomplete has a different problem than one that's inaccurate.

Write one row per batch to the **Verification Log** tab on the master sheet (`1wf1vhj4_jvufGxpAO_3QAszTL9nSG8w6q1iVjp65-c8`) via the bundled script, using `append` mode against `Verification Log!A:J`. Columns, in order: Date, Batch (companies checked), Row Range, Non-blank Fields Checked, Fields With Errors, Accuracy %, Error Details (a short semicolon-separated list — company, field, what's wrong), Blanks Confirmed Correct, Blanks Flagged as Missed, Verified By (write "generator-ups-data-verification" here).

## Weekly reporting

A separate automated step (not this Skill's job to trigger itself) reads the Verification Log every Monday and produces a chart + summary in the Athena Reports Drive folder, tracking Accuracy % over time. This Skill's only responsibility is making sure every batch produces one clean, correctly-scored log row — the weekly rollup depends entirely on that log being complete and consistent.

## Not your job

Finding new companies. Enriching blank fields yourself (flag them as missed, don't fill them in — that blurs which Skill did what). Deciding sub-sector scope or reviewing Screening Verdict judgment calls. Editing the live map. Drafting outreach. Valuation.
