# Sheet write safety — canonical rules

This is the single source of truth for the safety rules shared across the three skills that read or write Daniel's Aurias 2 "Master UK generator and UPS Market Map" Google Sheet: `generator-ups-data-enrichment`, `generator-ups-data-verification`, and `generator-ups-near-misses-update`. Each of those rules used to be restated in each skill's own prose, independently — which meant a fix or clarification to the rule in one place didn't reach the others, and the incident stories that make each rule stick got copied, trimmed, and drifted differently in each copy. This file exists so there's one canonical version of each, in full, with the real incident behind it — the three SKILL.md files point here instead of re-explaining from scratch.

If a skill has its own specific nuance on top of one of these rules (e.g. how it applies during a multi-agent batch, or during a monthly sweep instead of a live write), that nuance stays in the skill's own file — only the generic, shared core lives here.

---

## 1. Never delete a row unless it's a confirmed exact duplicate

**Hard rule (Daniel, 2026-09-17): "I would not expect the skill to delete entries unless they are duplicates."** Not a judgment call — a company row only ever gets removed when it's a confirmed duplicate of another row for the same company, and even then, log which row you kept and why. Every other row stays, no matter how it looks — out-of-scope, badly enriched, missing every field, whatever. This is the same principle as "map the whole market, mark out-of-scope rather than drop" that runs through the whole pipeline, just stated as an explicit, hard boundary after a real incident where rows were lost by accident rather than by any deliberate decision to remove them.

**Why this is a hard line, not a guideline:** a wrongly-deleted row isn't a data quality issue you can fix by re-researching — it's gone, along with whatever partial work had already gone into it, and nobody finds out until someone happens to notice a company missing that they remember being there. The market map's whole value is that it stays complete over time; an agent quietly "cleaning up" rows it judges low-value undermines that completeness in a way that's invisible until it's already caused damage.

**What counts as a confirmed exact duplicate:** the same company appearing as two (or more) separate rows — not two similar-sounding companies, not a parent and subsidiary, not a rebrand where the old and new names both still have some claim to a row. The YorPower case is the canonical example: "YorPower" (owner "Gardner Family," 65 employees), "YorPower Ltd" (owner "YorPower Holdings Limited," 82 employees), and "Yorpower" (owner "Tony Brimble," 105 employees) all appeared as separate rows for what's presumably the same underlying company — conflicting ownership and headcount data across all three. That's a genuine duplicate-reconciliation case, not a judgment call about which row is "better." When you do confirm an exact duplicate, keep the more complete/accurate row, remove the other(s), and log which row you kept and why — the deletion needs to be traceable after the fact, not silent.

**If you're not sure it's an exact duplicate, it isn't one for this rule's purposes** — leave both rows, flag the ambiguity, and let Daniel or the enrichment skill's own judgment call decide later. A false negative (a real duplicate left in place a bit longer) costs nothing but a slightly untidy sheet. A false positive (a wrongly-deleted non-duplicate) costs real, unrecoverable data.

**Second authorized exception, added 2026-09-18 at Daniel's explicit request:** a row carrying the "Out-of-scope - suspected hallucinated/fake entry" verdict — meaning the full hallucinated-entry checklist in `data-template.md` was exhausted (no Companies House match, no DNS resolution, no web presence) — may be **moved** (not deleted outright) from Market Map to the **Suspected Hallucinations** tab. Same evidentiary bar as a confirmed duplicate: this only applies to rows that already earned that exact standardized verdict text through the normal enrichment process, not a fresh judgment call made while doing the move. The move is a genuine structural deletion from Market Map, so it carries the same procedural discipline as any other row deletion: append the full row to the destination tab first, verify it landed, re-verify row identity immediately before deleting (per section 2), delete rows in **descending row-number order** in a single batchUpdate if moving more than one (ascending order invalidates every subsequent row index as soon as the first deletion shifts everything below it), then reconcile the before/after count exactly (a move of N rows should drop Market Map's count by exactly N, no more, no less). First run moved 10 rows this way, reconciled 455 → 445 with zero discrepancy.

---

## 2. Re-verify row identity immediately before every write — never trust a row number from earlier in the run

**The fix, stated once:** immediately before any write, re-read that row's Company Name cell (a single cheap read) and confirm it still matches the company you're about to write. If it doesn't match — blank, a different company, shifted — don't write blindly. Re-locate the row by searching Company Name for the expected company first, then write to wherever it actually is now. This matters most for anything that takes more than a couple of minutes (a single deep-dive row, a batch that hits a slow API), since that's exactly the window where a concurrent edit can land. A cheap read before every write is worth it — a silent duplicate or a write to the wrong row is much more expensive to untangle after the fact.

**Two real incidents are why this rule exists, and both are worth keeping in full because they're different failure modes with the same fix:**

**Incident A — a shifting row number (2026-09-18).** A single-row enrichment cached its target as "row 459" at the start of a long research pass. While it was still working, Daniel manually deleted an unrelated duplicate elsewhere on the sheet, which shifted every row below it up by one — the real row moved to 458. The agent's later write still used the stale "459," landing on what was now an empty row and creating a full duplicate instead of updating the real one. This can happen from *any* concurrent structural change to the sheet, not just Daniel's edits — another dispatched agent, a manual fix, anything that inserts or deletes a row while you're mid-task.

**Incident B — a batch that silently landed on the wrong rows (2026-09-17).** A re-run of an already-enriched batch ended up writing its results to a *different* set of rows than the ones it had read from, which both duplicated one company and silently deleted (overwrote) two entirely unrelated companies further down the sheet. This went undetected until Daniel spot-checked cells directly, well after the batch had already been reported as complete and verified — because the read-back verification only checked that the cells the agent *meant* to write landed correctly. It didn't check whether anything else had been clobbered. The lesson from this incident is broader than incident A's: **reading a cell back after writing only proves the write landed somewhere correct — it doesn't prove nothing else shifted or got overwritten.** If you insert, delete, or otherwise restructure rows for any reason during a batch, re-run a row-count check and a duplicate-name scan across the whole sheet before considering the batch finished, not just a read-back of the specific cells you meant to touch.

**Combined, the working discipline is:** re-verify identity right before every single write (incident A's fix), and after any batch that touched row structure, verify the sheet as a whole — not just the cells you meant to change (incident B's fix). Neither check substitutes for the other.

---

## 3. Character-encoding safety

**Scan every field you read for garbled special characters:** a blank or double-space where an em-dash (—) should be, a "?" where an arrow (→) should be, a currency figure missing its £ sign entirely, a corrupted apostrophe or quote mark. This isn't cosmetic — it's the fingerprint of a specific, real bug, and treating a garbled character as an error is exactly as important as treating a wrong PSC name as one.

**The incident (root-caused and fixed 2026-09-18):** `sheets_api.sh`'s `write`, `append`, and `batch` modes were silently corrupting non-ASCII characters — em-dashes, arrows, £ signs — on their way to the sheet. The root cause was passing the JSON request body as an inline curl `-d` string argument: shell/argument-encoding handling mangled multi-byte UTF-8 characters before curl ever sent them. A prior fix for this had been applied ad hoc, by one subagent, for one specific call — it was never folded into the shared script, so the underlying bug persisted undetected across many other writes that used the same modes. The real fix was structural: write the JSON body to a temp file first, then use `curl --data-binary @file` to send it, which sidesteps shell argument-encoding entirely. That fix is now in the shared script itself (see git commits `8a0b9c5` and `d8432eb`), not a one-off patch — every call through `write`, `append`, or `batch` now goes through the same safe path.

**Why this still matters even though it's fixed:** any batch written *before* the fix landed could still carry the damage — a garbled character sitting in an already-written cell won't fix itself, and nothing about the fix retroactively repairs old data. A regression is also possible if the script is ever edited again without re-running its test suite (`scripts/test_sheets_api.sh`, which includes a round-trip encoding test specifically so this class of bug gets caught before it reaches a live batch again, not after). Treat a garbled character you find during verification as a real, silent data-quality miss — flag it back to Athena/Daniel the same way you would any other factual error, whether or not you know if the cell predates the fix.

---

## 4. The Automation Status single-batch lock, and the Batch Ledger multi-batch protocol

Two different coordination mechanisms exist to stop concurrent enrichment work from racing on the same rows, depending on how many batches are running at once. **They are mutually exclusive for a given dispatch — a batch agent uses one or the other, never both, and knows which one applies from how it was dispatched.**

### Single-batch lock — `Automation Status!A2:C2`

This exists because batches started running unattended overnight, where nothing but the sheet itself can prevent two runs (a scheduled task and a manual dispatch, say) from starting the same batch in parallel. Before doing anything else, read `Automation Status!A2:C2` on the master sheet:

- If Status (column B) is `FREE`, you're clear — write `IN_PROGRESS since <ISO timestamp>, rows <range>` into it **immediately, before starting any research**, so nothing else can claim the same batch while you're mid-task.
- If Status already shows `IN_PROGRESS`, **stop — don't start a batch.** Report back that one is already running rather than duplicating work or racing another agent on the same rows.
- Set it back to `FREE` as the very last thing you do, after the batch is written, verified, and handed off — not before.
- If you hit an unrecoverable error mid-batch, still set it back to `FREE` before stopping, so the lock doesn't jam the pipeline for whoever runs next.

This single lock only covers one batch at a time. **It does not apply when you've been dispatched as part of multi-batch mode** — skip the `Automation Status!A2:C2` check entirely in that case (it's reserved for the single-batch path) and use the Batch Ledger protocol below instead.

### Multi-batch protocol — the `Batch Ledger` tab

Added at Daniel's request, to speed up wall-clock throughput by running several batches at once instead of one at a time. **Athena (the orchestrating session, not a dispatched batch agent) is the sole coordinator:** she reads the unenriched-row queue once, splits it into N disjoint row lists (no overlap, ever), writes one claim row per batch to the **Batch Ledger** tab (columns: Batch ID, Rows Assigned, Companies, Status, Started, Completed, Agent Task ID, Notes), and only then dispatches N `sourcing` agents in parallel, each with its exact row list baked into its prompt.

A dispatched batch agent in this mode **never picks its own rows** — it works only the rows it was explicitly given, and never calls `next-batch` or otherwise self-selects additional rows, since another concurrent agent may already be working adjacent ones. That single discipline — rows assigned up front by one coordinator, never claimed peer-to-peer — is what keeps two concurrent agents from ever racing to claim the same row, without needing any actual distributed-locking scheme between them.

When a batch agent finishes (or hits an unrecoverable error), it updates **its own row only** in the Batch Ledger — Status to `DONE` or `FAILED`, a Completed timestamp, and a one-line Notes summary — instead of touching `Automation Status!A2:C2`. Never touch another batch's row.

**The row-identity-verification rule (Section 2 above) matters even more in multi-batch mode than single-batch mode** — with several agents live at once, a concurrent structural edit (an insert/delete from Daniel or from another agent) can shift rows for everyone simultaneously, not just for the one agent that happened to be running at the time. Re-read the Company Name immediately before every write, every time, no exceptions — the same fix, just a larger blast radius if skipped.
