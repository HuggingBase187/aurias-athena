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
- **Full field-by-field template**, the screening rules, the PSC-chase procedure, and the contact rules: `references/data-template.md` — read this before starting a batch, don't work from memory of a previous run.
- **Shared safety rules** (never delete a non-duplicate row, re-verify row identity before every write, character-encoding safety, the Automation Status/Batch Ledger lock protocols) — canonical version, with the real incidents behind each rule, lives in `references/sheet-write-safety.md`. The same rules apply to `generator-ups-data-verification` and `generator-ups-near-misses-update`; this is the one place they're written out in full.
- **Bundled script** for all sheet reads/writes: `scripts/sheets_api.sh` — use this instead of hand-writing curl calls. Run it with no arguments to see the usage for each mode (`read`, `write`, `clear`, `batch`, `append`, `format`, `meta`). **Test suite: `scripts/test_sheets_api.sh`** — run this after any edit to `sheets_api.sh` before trusting it again; it's safe to run any time (zero side effects on real data).
- **PSC chase, scripted (added 2026-09-18):** `scripts/ch_psc_chase.sh COMPANY_NUMBER` walks a Companies House PSC chain to the underlying natural person(s) in one call instead of doing it hop-by-hop by hand — see the "Chasing the PSC to a real person" section of `.claude/agents/sourcing.md` for why. Read-only, hits the Companies House API (key in the project's `.env`), no sheet access.
- **Accounts document fetch, scripted (added 2026-09-18):** `scripts/ch_accounts_fetch.sh COMPANY_NUMBER [OUTPUT_PDF]` resolves and downloads a company's most recent filed accounts document via the Companies House API (same key, same auth pattern as `ch_psc_chase.sh`) instead of scraping the public filing-history page for a "View PDF" link. Use this any time you need Revenue/PBT/average-employees figures that only exist inside the filed document itself, not in the structured company/PSC data — those three figures are never available from the plain company-profile API call alone. Read the returned PDF with the `Read` tool's `pages` parameter rather than pulling the whole thing at once if it's long (e.g. `pages: "20-25"` to jump toward the Notes section once you've seen the Contents page). **Always pass an explicit `OUTPUT_PDF` path pointing at your scratchpad directory** — the default (`./accounts_<number>.pdf`, relative to wherever you happen to run the command) has already landed downloaded PDFs directly inside this skill's own `scripts/` folder once, which doesn't belong in a git-tracked directory.
- **Duplicate-candidate scan, scripted (added 2026-09-18):** `scripts/duplicate_scan.sh SHEET_ID` scans the whole Market Map for likely duplicate rows (exact Companies House number/LinkedIn match, exact name after stripping Ltd/plc, fuzzy name similarity) instead of relying on stumbling onto them during enrichment. Read-only, prints candidates only — it never deletes or decides; see `.claude/agents/sourcing-verifier.md`'s "Duplicate/conflicting rows" check.
- **Batch health check, scripted (added 2026-09-18):** `scripts/batch_health_check.sh SHEET_ID` cross-checks the Batch Ledger against the Market Map to catch silently-dead or stalled batch agents — see "Silent agent death" under multi-batch mode below for when this is mandatory, not optional. Read-only.
- **Google Docs edits, scripted (added 2026-09-18):** `scripts/docs_api.sh` reads/writes the Scope & Search Vocabulary doc and Near Miss Rules doc directly via the Docs API (same service account, wider token scope) — `get`/`text` to read, `append` to add at the end, `replace` for exact-text find/replace (also the safe way to do a targeted insert against a stable marker line). Replaces the old trash-and-recreate browser-automation approach entirely — see [[feedback_avoid_live_gdoc_editing]].

## Scope

Only these 7 categories: UPS, critical power services, backup generators, transformers, battery energy storage systems (BESS), switchgears, load banks. If a company on the sheet turns out to be clearly outside all 7, that's a Screening Verdict of Out-of-scope with a reason — not something to silently skip past.

## LinkedIn work is Athena's job, not a dispatched batch agent's — don't try to load the browser tool yourself

**Corrected 2026-09-18.** An earlier version of this section told batch agents to `ToolSearch` for `mcp__claude-in-chrome__*` before LinkedIn lookups. That instruction was wrong and has been retired: `sourcing.md` lists `claude-in-chrome` as an available MCP server in its frontmatter, but the agent's actual `tools` grant doesn't include `ToolSearch`, so a dispatched batch agent has no way to load or call it — confirmed directly by a batch agent's own report ("I don't have a ToolSearch function to load one"). Trying anyway just wastes a turn.

There's also a reason not to fix this by simply granting the tool: Claude-in-Chrome drives Daniel's one real, logged-in Chrome session — not an isolated browser per agent. Multiple concurrent batch agents (or even one, running unsupervised) hitting that shared session risks both wrong-tab/wrong-result mix-ups and, more seriously, LinkedIn's own bot-detection flagging unusual automated activity on Daniel's actual account.

**So: leave LinkedIn-sourced fields (Associated Members on LinkedIn, PSC/CEO/MD LinkedIn URLs where you can't confirm identity via WebSearch alone) blank rather than guessing, and say so plainly in your batch report** — e.g. "LinkedIn fields left blank, needs Athena's direct lookup." Athena does these lookups herself, directly, using her own logged-in browser access, working through the batch's companies once the rest of the research lands. This is a deliberate handoff, not a missed step — don't try to work around it by using WebSearch/WebFetch as a LinkedIn substitute, since that's what produced wrong-person matches before this rule existed.

## The workflow

### 1. Check the batch lock, then pick up where the sheet leaves off

Before doing anything else, read `Automation Status!A2:C2` on the master sheet. If Status (column B) is `FREE`, you're clear — write `IN_PROGRESS since <ISO timestamp>, rows <range>` into it immediately, before you start researching, so a scheduled task or another dispatch can't start the same batch in parallel. If Status already shows `IN_PROGRESS`, **stop — don't start a batch.** Report back that a batch is already running rather than duplicating work or racing another agent on the same rows. Set it back to `FREE` as the very last thing you do, after the batch is written, verified, and handed off — not before. If you ever hit an unrecoverable error mid-batch, still set it back to `FREE` before stopping, so the lock doesn't jam the pipeline for whoever runs next.

**This single lock only covers one batch at a time — it does not apply when Athena has dispatched you as part of multi-batch mode.** If your dispatch prompt says you were assigned a fixed row list from the **Batch Ledger** tab, skip the `Automation Status!A2:C2` check entirely and follow "1c. Multi-batch mode" below instead. See `references/sheet-write-safety.md` (section 4) for why both protocols exist and how they relate — read it before assuming which one applies to a given dispatch.

Read the Market Map tab's Company Name and Website columns (via `sheets_api.sh read`) to find rows that have a name but are still missing the rest of the template — that's your queue. Don't re-enrich a row that's already been filled in and given a Screening Verdict; that's the verifier's job to check, not yours to redo.

### 1c. Multi-batch mode — when several batches run at once

Athena (the orchestrating session, not a dispatched batch agent) is the sole coordinator here — she splits the unenriched-row queue into disjoint row lists (no overlap, ever), claims one row per batch in the **Batch Ledger** tab, and only then dispatches batch agents each with their exact row list baked into their prompt. **See `references/sheet-write-safety.md` (section 4) for the full protocol, its columns, and why it's structured this way** — this section only covers what a batch agent running inside it needs to do.

If you're a batch agent running in this mode:
- Work only the rows you were explicitly given. Don't call `next-batch` or otherwise pick additional rows — another concurrent agent may already be working adjacent ones.
- **The row-identity-verification rule in step 1b matters even more here than in single-batch mode** — with several agents live at once, a concurrent structural edit (an insert/delete from Daniel or another agent) can shift rows for everyone simultaneously, not just for the one agent that happened to be running. Re-read the Company Name immediately before every write, every time, no exceptions.
- When you finish (or hit an unrecoverable error), update your own row in the Batch Ledger tab — Status to `DONE` or `FAILED`, Completed timestamp, and a one-line Notes summary — instead of touching `Automation Status!A2:C2`. Only ever write your own ledger row; never touch another batch's row.
- Still hand off to the `sourcing-verifier` subagent per step 9 below, same as single-batch mode.

Daniel has agreed to pause his own manual row/column edits on the Market Map while multi-batch mode is actively running, specifically to keep the risk surface down — this doesn't remove the need for the identity-verification rule (another concurrent agent is still a source of structural change), but it does remove the most common trigger seen so far (a manual edit landing mid-batch).

**Default round shape (confirmed 2026-09-18): 3 concurrent batches of 5 = 15 companies per round.** This is a working default, not a hard limit — Athena adjusts if a specific situation calls for it, but this is where to start without being asked.

**Trial concluded (2026-09-18): 3 concurrent batches of 8 tested against Daniel's 95% accuracy floor, and reverted.** Daniel asked whether running more than 3 batches concurrently would speed things up; the answer was no — the actual bottleneck is the serial work between rounds (the LinkedIn sweep, which only runs through one logged-in browser session; verification review; hallucination-tab sweeps), which scales with total companies enriched, not with how many batches ran them. Bigger batches (8 instead of 5, still 3 concurrent) were the proposed alternative, tested with the explicit rule that any trial batch scoring below 95% reverts on its own, no averaging. **Result: Batch 36 (rows 118-125) scored 92.1%.** Reverted immediately per the standing rule — **back to 3 concurrent batches of 5 = 15 per round as the default.** The original reason 5 was chosen ("long, unbroken research runs are exactly where an agent's accuracy tends to drift," see step 2 below) held up: Batch 36's errors weren't randomly distributed noise, they clustered specifically around one research technique (Wayback Machine evidence-checking, see the Wayback API gotcha noted under the hallucination checklist) — plausibly a size-independent tooling issue rather than proof that 8 itself causes drift, but the floor rule doesn't require litigating *why* a batch missed 95%, only that it did. Don't retry 8-per-batch without a specific reason to revisit it.

#### A round isn't "complete" until the LinkedIn sweep is done, not just the Companies House research

**Confirmed 2026-09-18, after a real gap:** across several rounds, batch agents correctly left LinkedIn-sourced fields blank per the rule above and handed them to Athena — but Athena reported those rounds as done without actually doing the LinkedIn sweep, creating a backlog that Daniel had to notice and flag three separate times before it got addressed. The fix isn't a reminder, it's a sequencing rule: **Athena does the LinkedIn sweep for every company in a round immediately after the batches finish, as a blocking step, before telling Daniel the round is done.** A round that's "done except LinkedIn" is not done — say so explicitly if a genuine interruption forces a report before the sweep is finished, rather than letting it read as complete.

#### Silent agent death — detect it on every resume, don't wait for a notification

**Confirmed 2026-09-18, after three separate incidents in one night (Batch 16; Batches 17-19 via a session restart; Batches 21-22, cause unknown) — Daniel noticed all three before Athena did.** The structural problem: Athena gets a PUSH notification when a dispatched batch agent *completes*, but nothing at all when one *dies* mid-run. A dead agent's Batch Ledger row just sits at `IN_PROGRESS` forever, looking identical to a slow-but-healthy batch. Waiting for a notification that will never arrive isn't a monitoring strategy — it's passive hoping, and it puts the burden of noticing on Daniel instead of on the person coordinating the work.

**The fix is a PULL, run on a schedule Athena controls, not a PUSH someone else has to remember to send.** `scripts/batch_health_check.sh SHEET_ID` cross-checks the Batch Ledger against what has actually landed on the Market Map (does each assigned row show a Companies House Number yet?) and flags anything `IN_PROGRESS` for longer than ~25 minutes as stale, with a verdict that tells you what happened: no data landed at all (likely dead), partial data (died mid-batch), or full data with a stale ledger row (finished but never updated its own status). Read-only, safe to run any time.

**When to run it — this is the part that actually closes the gap:**
- Immediately after dispatching a round, before doing anything else, confirm via `ListAgents` that the number of running agents matches the number of batches just dispatched.
- **Every single time Athena is invoked for any reason — a new message from Daniel, a task notification, anything — while any Batch Ledger row shows `IN_PROGRESS`, run `batch_health_check.sh` as the first action, before responding to whatever prompted the resume.** This is the actual fix: since nothing can wake this session on a timer on its own, the only reliable checkpoint is "every time I'm already awake for some other reason." Making the check mandatory on every resume — not conditional on remembering, or on feeling like something's wrong — is what turns detection from best-effort into structural.
- A `STALE -- LIKELY DEAD` or `STALE -- PARTIAL` verdict is confirmed, not just suspected, once `ListAgents` also shows the batch's agent is no longer running. At that point mark the ledger row `FAILED` immediately yourself — don't wait for Daniel to ask, and don't leave it at `IN_PROGRESS` a moment longer than it takes to confirm.

**This doesn't replace the write-pattern fix below** (writing incrementally so less is lost when a batch does die) — the two are complementary: one shrinks how much a death costs, the other shrinks how long a death goes unnoticed.

#### Borderline/override verdict calls get batched into one review per round, not flagged one at a time

**Confirmed 2026-09-18.** A "Needs more info" verdict that needs Daniel's judgment (PBT qualifies but ownership is PE/large-group, a stale near-miss, etc.) doesn't need to interrupt him the moment one batch agent reports it. Athena collects every such call from a round together and brings them to Daniel as one batch of decisions once the round (including its LinkedIn sweep) is finished — not as a drip of separate interruptions mid-round. This is about pacing the *conversation*, not the underlying "Needs more info" → Flagged to You mechanism, which is unchanged.

### 0. Never delete a row unless it's a confirmed exact duplicate

**Hard rule (Daniel, 2026-09-17): "I would not expect the skill to delete entries unless they are duplicates."** Not a judgment call — a row only ever gets removed when it's a confirmed duplicate of another row for the same company, and even then, log which row you kept and why in your batch report. Every other row stays, no matter how it looks. **See `references/sheet-write-safety.md` (section 1) for the full rule, the YorPower precedent that defines what "confirmed exact duplicate" actually means, and why this is a hard line rather than a judgment call** — read it before removing any row you're tempted to treat as a duplicate.

### 1a. Count before you touch anything

Before writing, count the total non-blank rows in the Company Name column and note it. After writing the batch, count again. **The count should only ever stay the same or grow — never shrink.** A shrinking count means rows were lost somewhere, even if the batch you meant to write looks fine on a read-back. This is the cheapest possible check against the exact failure described in step 5 below, so don't skip it because it feels redundant with the read-back verification.

### 1b. Never trust a row number you determined earlier in the run — re-verify identity right before you write

**The fix: immediately before any write, re-read that row's Company Name cell (a single cheap read) and confirm it still matches the company you're about to write.** If it doesn't match — blank, different company, shifted — don't write blindly; re-locate the row by searching Company Name for the expected company first, then write to wherever it actually is now. This matters most for anything that takes more than a couple of minutes (a single deep-dive row, a batch that hits a slow API), since that's exactly the window where a concurrent edit can land.

**See `references/sheet-write-safety.md` (section 2) for the real incident behind this rule** — a cached "row 459" that had silently shifted to row 458 mid-run after an unrelated manual delete elsewhere on the sheet — and why a read-back after writing isn't enough on its own to catch this.

### 2. Work in batches of 5

Take five companies at a time, fully research and verify all of them, write that batch to the sheet, then move to the next five. This isn't a formality — Daniel asked for it specifically because long, unbroken research runs are exactly where an agent's accuracy tends to drift (this was raised directly when we researched why a Claude agent might "hallucinate after a small number of accurate results" — the fix isn't a different tool, it's disciplined batching and verification, which is what this whole workflow is built around). Five is small enough to genuinely fact-check each one, not so small that progress crawls.

You can run through as many batches as needed in one sitting — there's no need to stop and wait for approval between batches, since this is filling in blanks, not overwriting existing data. Do post a short one-line note after each batch (companies covered, anything flagged) so progress stays visible.

### 3. Research each company — cheapest checks first

Follow the order of checks in the "Screening rules" section of `references/data-template.md`, and stop as soon as a pass produces a verdict. LinkedIn is the bottleneck, so it only runs for companies still in play at the end.

**Pass 0 — quality gate (script, no research).** Run `scripts/quality_gate.py` on the batch's rows (read-only; needs `COMPANIES_HOUSE_API_KEY` from the repo `.env`). Then:
- `FAIL_NO_COMPANY` → run the hallucination checklist ("Untraceable companies" in `data-template.md`) and, if confirmed, step 6a.
- `FAIL_DISSOLVED` / `FAIL_TOO_SMALL` → confirm the matched Companies House entity is this company (address or website agree), then Out-of-scope with the reason. If it's a different company with the same name, treat the row as `REVIEW`.
- `PASS` / `REVIEW` → Pass 1.

**Pass 1 — one Companies House visit.** Pull PBT, Revenue, Employees (K), the PSC register and Accounts Next Due (AD) together. Also check the homepage matches Section 0 of the Scope & Search Vocabulary doc. Write the verdict now if these decide it.

**Pass 2 — everything else, only for companies still in play.** PSC chased to a named person, CEO/MD contacts, OEM partnerships, services, sectors, sources. LinkedIn (I/J) is Athena's job and happens last (see the LinkedIn section above). Verify before you write; blank beats a guess.

Fill in every field per `references/data-template.md`, whichever pass reaches it. Three fields have specific formatting rules worth restating here because they're easy to default into a lazier shorthand:

- **Employees - Companies House (K)** — pull it for every company; it's the first headcount source (see "Reading headcount" in `references/data-template.md`).
- **Accounts Next Due - Companies House (AD)** — the next accounts' period and due date, from the same overview page.
- **Equipment Category (H)** — every in-scope category (Section 0 of the Scope & Search Vocabulary doc) the company genuinely offers.
- **Key OEM Partnerships (X)** — paired to the category it belongs to, e.g. `Generator - Cummins, Perkins; Load bank - Crestchic`.
- **Type-Spec / Resale-Rental-Service (Y)** — each applicable one spelled out individually, never "all" or "both".

And the two rules that protect against the most damaging kind of wrong answer:
- **PSC must resolve to a named human being**, chased up the ownership chain as far as it takes (`references/data-template.md` has the full procedure and worked examples).
- **Never a generic email address** (info@, sales@, hello@, etc.) in PSC Email or CEO/MD Email — a real person's direct address, verified where possible, or blank.

### 4. Spawn helper agents when it speeds things up without costing accuracy

You have discretion to use the Agent tool to parallelize research within a batch — for example, one helper agent per company doing the raw Companies House/LinkedIn/web lookups simultaneously, rather than one agent working through all 5 in sequence. Close each helper once it's reported back.

Keep the verification and the actual sheet write centralized in you, the orchestrating agent, rather than letting helpers write directly — that way five parallel lookups can't race each other on the same batch write, and you get one last chance to sanity-check everything before it hits the live sheet. Treat a fact a helper agent returns the same way you'd treat one you found yourself: if it isn't independently checkable against a primary source, it doesn't go in as a stated fact.

### 5. Write each company as soon as it's ready — don't hold all 5 for one final write

**Changed 2026-09-18, after three batches in one night died mid-run and lost 100% of already-completed research because nothing had been written yet.** The previous instruction here was to research all 5 companies, then write them in a single `sheets_api.sh batch` call at the end. That's a bad trade: an atomic 5-row write buys you a slightly tidier API call, but it means a crash at minute 14 of a 15-minute batch — after all the hard research work is done — throws away the entire batch instead of the one row still in progress. Given how often batch agents have died right before this exact step, treat "haven't written yet" as "doesn't exist yet" and write accordingly.

**Write each company's row the moment it's fully researched and verified, one at a time, via `sheets_api.sh write`** (or `append`/`batch` for that single row — whichever mode fits, the point is committing per-company, not the specific call). Read the row back to confirm it landed before moving to the next company. This means a mid-batch death now costs at most the one row that was actively being written, not the whole batch — and whatever already landed is real, verifiable progress that the next agent (or Athena, writing from reported research) doesn't need to redo.

Re-verify row identity (step 1b) before every one of these writes, same as always — five separate writes to a batch that might be shifting under you is exactly the situation that rule exists for, not a reason to skip it.

**Before writing, record the exact row number for each company you're about to update** (not just its name) — read the Company Name in that row and confirm it matches before you write anything into it, per the row-identity rule in step 1b. If you insert, delete, or otherwise restructure rows for any reason during a batch, re-run the row-count and duplicate-name checks before considering the batch finished — a read-back only proves the cells you meant to touch landed correctly, it doesn't prove nothing else shifted or got clobbered elsewhere on the sheet. **See `references/sheet-write-safety.md` (section 2, "Incident B") for the real batch-mismatch incident this protects against** — a re-run that silently duplicated one company and overwrote two unrelated ones, undetected until a direct spot-check.

### 6. Decide the verdict

Apply the "Screening rules" section of `references/data-template.md` — financials first, headcount only when no PBT is filed, ownership next. For near misses (PBT £700k–£1m, headcount 20–29), read the **Near Miss Rules** Google Doc fresh every time and route exactly as it says. Run every financial check on every company, even when headcount already looks decisive.

### 6a. A confirmed hallucination gets moved to the Suspected Hallucinations tab immediately — every time, not as a periodic sweep

**Gap found and fixed 2026-09-18.** The Suspected Hallucinations tab and its move-protocol (`references/sheet-write-safety.md` section 1, second authorized exception) were built for a one-time whole-sheet sweep, and that's the only time the move actually happened — 10 rows, moved once. Every hallucination verdict written since, by batches 11 through 22, was correctly labelled "Out-of-scope - suspected hallucinated/fake entry" but never actually moved — nothing in the day-to-day workflow triggered it. By the time this was caught, 9 rows (D&E Power, Dash Power, Derby Power, Devon Power, Direct Gensets, Durham Power, Eagle Power Ltd, East Midlands Power, Eco Power) had accumulated on Market Map with the right verdict sitting in the wrong place. Daniel caught this by asking directly whether the move was a standing rule or a one-off — it was the latter, silently.

**The rule now: the moment you write a Screening Verdict of "Out-of-scope - suspected hallucinated/fake entry" for a row — whether you're an enrichment batch, a single-row fix, or anything else touching this sheet — move that row to the Suspected Hallucinations tab as part of finishing that row, not as a separate cleanup pass someone has to remember to run later.** Follow the append-verify-delete-reconcile protocol in `references/sheet-write-safety.md` section 1 exactly (append the full row there first, verify it landed, re-verify identity immediately before deleting from Market Map, reconcile the before/after count). If you're mid-batch and it's cheaper to collect every hallucination found in that batch and move them together in one pass at the end of the batch (descending row order, same protocol) rather than one-by-one interleaved with research, that's fine — the requirement is "before this batch is reported done," not "before the very next row." What isn't fine is leaving a hallucination-verdict row sitting on Market Map indefinitely on the assumption that someone will sweep for it later.

### 7. Copy, don't move: Qualified Leads and Flagged to You

- Verdict qualifies (per the Screening rules or the Near Miss Rules doc) → `sheets_api.sh append` the row to **Qualified Leads**.
- Verdict is "Needs more info" → append the row to **Flagged to You**. Daniel reviews and reclassifies; this Skill stops at flagging.
- The Market Map row stays where it is. Copy the row's full current width (read the header row first — never a hardcoded range).

### 8. Keep the sheet readable

Daniel wants this sheet "neatly formatted, well presented and easy to read" — not just correct. Use `sheets_api.sh format` (wraps the general `spreadsheets.batchUpdate` endpoint) to apply standard presentation once per sheet if it isn't already there: bold + frozen header row, sensible column widths, and consider light row banding for readability on a sheet this long. Formatting is a one-time/idempotent housekeeping step, not something to redo every batch — check with `sheets_api.sh meta` first if you're unsure whether it's already applied.

### 9. Hand off to verification, every time — as a genuinely separate agent

Once a batch is written and verified-readable, hand off to verification by spawning the **`sourcing-verifier` subagent** (via the Agent tool, `subagent_type: "sourcing-verifier"`) and telling it to run the `generator-ups-data-verification` Skill against this batch. This isn't optional or occasional — Daniel wants every batch checked, not a sample, so the accuracy tracking it produces (see that Skill's scoring section) reflects the whole pipeline, not a cherry-picked slice.

**Use the subagent, don't just load the verification Skill inline in your own context (corrected 2026-09-18).** The verification Skill's "no Edit access by design" boundary only means something if it's actually enforced — and `sourcing-verifier`'s own tool grant genuinely has no Edit or Bash tool, so a verifier running as that subagent physically cannot write to the sheet, whereas you (the enrichment agent) can. The first real batch through this pipeline (2026-09-17/18) showed why this matters: verification found two Notes-column misses and corrected them itself rather than just flagging them, because it was running inline in an agent context that still had full Edit/Bash access — the written rule didn't stop it, since nothing was actually enforcing it. Route through the subagent so the boundary is structural, not just a line in a file.

## Not this skill's job

Finding brand-new companies to add to the sheet (a separate skill, built to cover that side of the pipeline). Independent verification/QA of data already on the sheet — that's `sourcing-verifier`. Deciding sub-sector scope changes. Drafting outreach. Valuation. Anything touching legal or financial commitments. If you hit one of these, hand it back to Athena rather than doing it yourself.
