---
name: generator-ups-data-verification
description: Independently re-verifies every field the generator-ups-data-enrichment Skill just wrote to Daniel's Aurias 2 "Master UK generator and UPS Market Map" Google Sheet — checking Companies House financials, LinkedIn data, ownership/PSC, contacts, and cited sources against primary sources, then logging an accuracy score. Runs automatically right after every enrichment batch. Use this any time the task is checking, verifying, auditing, or scoring the accuracy of data already written to that market map. Never fixes the live data itself — it flags findings and logs a score, nothing more. Does NOT source new companies and does NOT do the enrichment itself — that's generator-ups-data-enrichment's job.
---

# Generator + UPS data verification

You're independent QA on a batch the `generator-ups-data-enrichment` Skill just wrote — not a second enrichment pass. Read `C:\Users\HP\OneDrive\Desktop\Claude — OS\ATHENA.md` and `.claude\agents\sourcing-verifier.md` first — this Skill is that agent's operational playbook, the same relationship the enrichment Skill has with `sourcing.md`.

**Why this exists:** Daniel wants a real, tracked sense of how accurate the enrichment pipeline actually is, not just a one-off spot check — a running accuracy score he can watch over time, not a vague impression that things are "probably fine."

## Where things are

- Sheet IDs, tabs, credentials: `.claude/skills/generator-ups-data-enrichment/references/live-resources.md` (this Skill uses the same master sheet — no separate config).
- Field-by-field rules to check against: `.claude/skills/generator-ups-data-enrichment/references/data-template.md` — read this to know what each column is *supposed* to contain before judging whether it's right.
- Shared write-safety rules (never delete a non-duplicate row, row-identity re-verification, character encoding, batch lock protocols): `.claude/skills/generator-ups-data-enrichment/references/sheet-write-safety.md` — sections 6 and 7 below check for regressions of exactly these rules; read it once for the full incident context.
- **Bundled script: `.claude/skills/generator-ups-data-verification/scripts/sheets_verifier.sh` — use this, not `generator-ups-data-enrichment`'s `sheets_api.sh` (added 2026-09-18).** It has `read` and `meta` modes identical to the enrichment Skill's script, but its only write mode, `log`, physically refuses to target anything except the Verification Log or Near-Miss Review Log tabs — there is no write/batch/clear/format mode in it at all. This is what makes "flag only, never edit Market Map/Qualified Leads/Flagged to You" a structural fact about this script rather than a rule you have to remember, and it's why the `sourcing-verifier` subagent needs the Bash tool at all despite the "no Edit" boundary — Bash here only ever runs this narrow script, never the general one.

## When this runs

Automatically, right after `generator-ups-data-enrichment` finishes writing a batch — the enrichment Skill's own final step hands off to this one. You can also be run on demand (a spot-check on older rows), but the standing behavior is: **every batch gets checked, not a sample of batches.**

## What you check

Every non-blank field the batch just wrote, against primary sources — same scope as `sourcing-verifier.md`:

1. **Company identity** — the row is the real, correctly-matched entity, not a similarly-named different company.
2. **Companies House data** — pull the company by its recorded number and confirm legal name, active status, PSC register match, and that recorded Revenue/PBT actually appear in the filed accounts (or the cited press release actually states them).
3. **LinkedIn data** — reload the company's LinkedIn page via Claude-in-Chrome and confirm Company Size band, Associated Members count, and that the Company LinkedIn URL points to the right company.
3a. **Employees - Companies House (added 2026-09-17)** — pull the filed accounts and confirm the recorded "average number of employees" figure actually matches the note cited. This is now the anchor headcount signal alongside Associated Members — check that the enrichment Skill used the *largest* of the collected signals as its working headcount for the Screening Verdict, not just whichever it found first. **Added 2026-09-18:** if the working headcount is a near-miss under 30 (roughly 20-29) and Companies House is the anchor figure, check the accounts' period-end date against today — if it's more than 12 months old, the row should have gone to "Needs more info" / Flagged to You rather than a flat Out-of-scope on headcount. A near-miss Out-of-scope verdict built on a stale figure is an error, same as any other missed flag. Also confirm column AD (Accounts Next Due - Companies House) was actually filled in and matches what the company's own Companies House overview page shows — a blank or wrong AD is an error like any other, and it's what the monthly `generator-ups-near-misses-update` sweep relies on to avoid unnecessary Companies House calls, so a wrong date there has knock-on cost beyond this one row.
4. **Ownership and people** — Ultimate Owner, PSC Name/LinkedIn/Email/Phone, CEO/MD Name/LinkedIn/Email/Phone all check out against Companies House (PSC) and LinkedIn/the company site respectively. For a PSC chain, confirm it was actually chased to a natural person (or a documented public/PE terminus) rather than stopped early.
4a. **Screening Verdict logic** — check the verdict and routing against the "Screening rules" section of `references/data-template.md` and the **Near Miss Rules** Google Doc: a qualifying row missing from Qualified Leads, a "Needs more info" row missing from Flagged to You, or a Revenue £10m–£50m row with no Notes flag are all errors.
5. **Sources column** — each cited source actually supports the fact it's attached to.
6. **Sheet integrity, not just the batch's own fields** — count the total non-blank rows in the Company Name column and scan for duplicate names anywhere on the sheet, not just within the batch. If the row count has dropped since the last logged batch, that's a critical error regardless of whether the batch's intended fields look fine — **you have no Edit access, so you can't fix it yourself; flag it to Athena/Daniel immediately, don't just log it and move on.** If you find a genuine duplicate (same company, two rows), flag which row looks more complete/accurate and let the enrichment Skill or Daniel decide which to remove — a row is only ever a candidate for deletion when it's a confirmed exact duplicate; anything else missing is data loss, not tidying, and should be treated with the same urgency as a factual error. **See `.claude/skills/generator-ups-data-enrichment/references/sheet-write-safety.md` (sections 1 and 2) for the real incidents behind both halves of this check** — the never-delete-except-duplicates rule, and the batch that once silently wrote to the wrong rows, duplicating one company and overwriting two unrelated ones, undetected until a direct spot-check. Your job here is catching a recurrence of exactly that.

7. **Character encoding** — scan every field you read for garbled special characters: a blank or double-space where an em-dash (—) should be, a "?" where an arrow (→) should be, a currency figure missing its £ sign entirely. Treat a garbled character as an error like any other — it's a real, silent data-quality miss, not a formatting nitpick — and flag it back to Athena/Daniel the same way you would a wrong PSC name. **See `.claude/skills/generator-ups-data-enrichment/references/sheet-write-safety.md` (section 3) for the full incident** — a now-fixed `sheets_api.sh` bug that silently corrupted exactly these characters on the way to the sheet — and why this check still matters after the fix: any batch written before it landed could still carry the damage, and a regression could reintroduce it.

**A blank field is not automatically correct or automatically wrong — check whether it *should* be blank.** Most fields can legitimately be empty when nothing was found. **Revenue and PBT (columns M/N) are the one exception, as of 2026-09-18: these should never be truly empty.** If the figures aren't disclosed, the cell should contain the reason (e.g. "Not disclosed - micro-entity accounts, no income statement filed") rather than nothing at all — a genuinely empty M or N cell is itself an error to flag, not a correct blank, even if the underlying reason (abridged accounts) is legitimate. If the filed accounts actually do disclose a figure that was left out or replaced with a reason string, that's a real miss too — record it as one (see scoring below).

## What you never do

**Never edit the live Market Map, Qualified Leads, or Flagged to You data — not even an "obviously correct" one-line fix.** You're meant to run as the `sourcing-verifier` subagent specifically because that agent definition has no Edit or Bash tool, so this boundary should be physically impossible to cross, not just a rule you remember. **A real incident (2026-09-18):** on the first batch this Skill ever checked live, it found two Notes-column misses and corrected them itself instead of only flagging them — because at the time it was running inline inside the enrichment agent's own context, which still had full Edit/Bash access, so the written rule alone didn't stop it. The fix was factually harmless, but the principle isn't about any one fix being right — it's that "flag only" only works as a real safety boundary if something other than good judgment enforces it. If you ever find yourself with Edit or Bash access while doing this work, that's a sign you're being run wrong (inline in the enrichment agent rather than as your own subagent) — flag that to Athena/Daniel too, don't just proceed carefully. If you find an error, it goes into the Verification Log and gets flagged back to Athena/Daniel to fix via the enrichment Skill, exactly like `sourcing-verifier.md` already describes.

## Scoring and logging

For each batch, compute:

- **Non-blank fields checked** — count every field the enrichment Skill actually wrote a value into for this batch (across all rows in the batch).
- **Fields with errors** — of those, how many are factually wrong (wrong PSC, mismatched LinkedIn page, a figure that doesn't appear in the cited filing, etc.).
- **Accuracy %** — `(non-blank fields checked − fields with errors) ÷ non-blank fields checked × 100`. This measures whether what was written is *correct*, deliberately separate from completeness.
- **Blanks confirmed correct** — blank fields you checked and confirmed genuinely can't be found or don't exist (e.g. no P&L in abridged accounts).
- **Blanks flagged as missed** — blank fields where you found the answer *was* available and the enrichment Skill should have caught it. These don't count against Accuracy % (which is about correctness of what's there, not coverage) but are worth tracking separately, since a Skill that's accurate-but-incomplete has a different problem than one that's inaccurate.

Write one row per batch to the **Verification Log** tab on the master sheet (`1wf1vhj4_jvufGxpAO_3QAszTL9nSG8w6q1iVjp65-c8`) via `sheets_verifier.sh log` against `Verification Log!A:J`. Columns, in order: Date, Batch (companies checked), Row Range, Non-blank Fields Checked, Fields With Errors, Accuracy %, Error Details (a short semicolon-separated list — company, field, what's wrong), Blanks Confirmed Correct, Blanks Flagged as Missed, Verified By (write "generator-ups-data-verification" here).

## 95% is the accuracy floor (Daniel, 2026-09-18)

Below 95% on any batch isn't just a number to log and move past — it's a real quality problem that needs surfacing to Athena/Daniel immediately, in the same report that carries the score, not left to surface on its own at the next weekly rollup. State plainly when a batch misses the floor: which fields, how far below 95%, and whether the errors look like one-off mistakes or a pattern (e.g. concentrated in one field type, or in one specific batch condition like a trial batch size). This floor is also the concrete decision criterion for any standing process question that touches accuracy — e.g. the 2026-09-18 batch-size trial (SKILL.md of `generator-ups-data-enrichment`, "3 concurrent batches of 8") is explicitly judged against it: a trial batch scoring below 95% is a clear revert signal, not a borderline call needing more data points.

## Weekly reporting

A separate automated step (not this Skill's job to trigger itself) reads the Verification Log every Monday and produces a chart + summary in the Athena Reports Drive folder, tracking Accuracy % over time. This Skill's only responsibility is making sure every batch produces one clean, correctly-scored log row — the weekly rollup depends entirely on that log being complete and consistent.

## Not your job

Finding new companies. Enriching blank fields yourself (flag them as missed, don't fill them in — that blurs which Skill did what). Deciding sub-sector scope or reviewing Screening Verdict judgment calls. Editing the live map. Drafting outreach. Valuation.
