#!/usr/bin/env bash
# Detects silently-dead or stalled multi-batch enrichment runs by cross-
# checking the Batch Ledger against what has actually landed on the Market
# Map -- instead of trusting the ledger's own IN_PROGRESS status, which a
# dead agent never updates.
#
# Why this exists (2026-09-18): dispatched `sourcing` batch agents run in
# the background. Athena gets a PUSH notification when one completes, but
# NOTHING when one dies mid-run (process killed, session restart, unexplained
# stall) -- the Batch Ledger row just sits at IN_PROGRESS forever. This
# happened three times in one night (Batch 16; Batches 17-19 via a session
# restart; Batches 21-22, cause unknown) and each time Daniel noticed before
# Athena did. Detecting death requires a PULL, not a wait -- this script is
# that pull, made cheap enough to run on every resume instead of relying on
# someone remembering to.
#
# Usage: batch_health_check.sh SHEET_ID [STALE_MINUTES]
#   STALE_MINUTES defaults to 25 -- comfortably above the ~15-20 min a real
#   batch of 5 has taken in practice, so this doesn't cry wolf on a batch
#   that's simply still working.
#
# Read-only. Never writes to the sheet, never touches the ledger. Prints one
# verdict line per IN_PROGRESS batch; see the verdicts themselves for what
# each one means and what to do about it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHEET_ID="${1:?Usage: $0 SHEET_ID [STALE_MINUTES]}"
STALE_MINUTES="${2:-25}"
NOW_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

export LEDGER_JSON=$(bash "$SCRIPT_DIR/sheets_api.sh" read "$SHEET_ID" "'Batch Ledger'!A2:H50" 2>/dev/null || echo '{}')
export MAP_CH_JSON=$(bash "$SCRIPT_DIR/sheets_api.sh" read "$SHEET_ID" "'Market Map'!C2:C5000" 2>/dev/null || echo '{}')

python - "$STALE_MINUTES" "$NOW_ISO" <<'PYEOF'
import json, sys, os, re
from datetime import datetime, timezone

stale_minutes, now_iso = float(sys.argv[1]), sys.argv[2]
now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))

ledger = json.loads(os.environ["LEDGER_JSON"])
ch_col = json.loads(os.environ["MAP_CH_JSON"])

rows = ledger.get("values", [])
ch_rows = [r[0].strip() if r else "" for r in ch_col.get("values", [])]
# ch_rows[0] corresponds to Market Map row 2, so Market Map row N -> ch_rows[N-2]

def parse_started(s):
    # Ledger timestamps are written as "IN_PROGRESS since <ISO>" or a bare ISO string.
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", s or "")
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def parse_row_range(s):
    m = re.search(r"(\d+)\s*-\s*(\d+)", s or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))

in_progress = []
done_count = failed_count = 0

for r in rows:
    r = r + [""] * (8 - len(r))
    batch_id, rows_assigned, companies, status, started, completed, agent_task_id, notes = r[:8]
    status = status.strip()
    if status == "DONE":
        done_count += 1
        continue
    if status == "FAILED":
        failed_count += 1
        continue
    if status != "IN_PROGRESS":
        continue

    started_dt = parse_started(started)
    elapsed_min = (now - started_dt).total_seconds() / 60 if started_dt else None
    row_range = parse_row_range(rows_assigned)

    populated = total = None
    if row_range:
        start_row, end_row = row_range
        total = end_row - start_row + 1
        populated = 0
        for rn in range(start_row, end_row + 1):
            idx = rn - 2
            if 0 <= idx < len(ch_rows) and ch_rows[idx]:
                populated += 1

    if elapsed_min is None:
        verdict = "UNKNOWN -- can't parse Started timestamp, check manually"
    elif elapsed_min < stale_minutes:
        verdict = f"RUNNING (normal) -- {elapsed_min:.0f} min elapsed, under the {stale_minutes:.0f} min threshold"
    elif populated is None:
        verdict = f"STALE ({elapsed_min:.0f} min elapsed) -- can't parse Rows Assigned to spot-check, check ListAgents now"
    elif populated == 0:
        verdict = (f"STALE -- LIKELY DEAD ({elapsed_min:.0f} min elapsed, 0/{total} rows show a "
                   f"Companies House Number). Check ListAgents now; if the agent is gone, mark FAILED "
                   f"and redispatch or write from any research already reported via task notification.")
    elif populated < total:
        verdict = (f"STALE -- PARTIAL ({elapsed_min:.0f} min elapsed, {populated}/{total} rows show data). "
                   f"Died mid-batch or is just slow -- check ListAgents. If gone, the missing rows are "
                   f"what still needs writing, not the whole batch.")
    else:
        verdict = (f"STALE -- LOOKS DONE ({elapsed_min:.0f} min elapsed, {populated}/{total} rows show data) "
                   f"but ledger Status is still IN_PROGRESS. Agent likely finished writing then died before "
                   f"updating its own ledger row -- spot-check a row or two, then mark DONE yourself.")

    in_progress.append((batch_id, rows_assigned, companies, verdict))

print(f"Batch Ledger as of {now_iso}: {done_count} DONE, {failed_count} FAILED, "
      f"{len(in_progress)} IN_PROGRESS\n")

if not in_progress:
    print("No IN_PROGRESS batches -- nothing to check.")
else:
    for batch_id, rows_assigned, companies, verdict in in_progress:
        print(f"[{batch_id}] rows {rows_assigned} ({companies})")
        print(f"  -> {verdict}\n")
PYEOF
