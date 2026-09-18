#!/usr/bin/env bash
# Scans the Market Map tab for likely duplicate company rows and prints
# candidates for review -- see duplicate_scan.py for why this exists and
# how matches are found. Never deletes anything itself -- read-only, always.
#
# Usage: duplicate_scan.sh SHEET_ID [TAB]   (TAB defaults to "Market Map")
#
# Cross-session lock check (added 2026-09-18, after a real incident): this
# scan itself is harmless and safe to run any time, since it never writes.
# But ANY session (this one or a separate window) about to ACT on its
# recommendations -- i.e. actually delete a row -- must check
# Automation Status!A2:C2 is FREE and that Batch Ledger has no IN_PROGRESS
# rows first, the same way a dispatched enrichment batch does. This script
# prints that check up front as a loud reminder, not as a hard gate (a pure
# read like this one doesn't need to block on the lock), specifically so a
# human or agent skimming the output doesn't skip straight to "which row
# do I delete" without checking whether it's actually safe to touch the
# sheet's structure right now. See references/sheet-write-safety.md
# section 1 for the full append-verify-delete-reconcile protocol that
# governs the actual deletion step -- this script is only ever the first
# half of that, never the second.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHEET_ID="${1:?Usage: $0 SHEET_ID [TAB]}"
TAB="${2:-Market Map}"

echo "=== Pre-flight: is it safe to ACT on this scan's recommendations? ===" >&2
LOCK_STATE=$(bash "$SCRIPT_DIR/sheets_api.sh" read "$SHEET_ID" "Automation Status!A2:C2" 2>/dev/null || echo '{}')
echo "$LOCK_STATE" | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
    vals = d.get('values', [[]])
    status = vals[0][1] if vals and len(vals[0]) > 1 else 'UNKNOWN'
except Exception:
    status = 'UNKNOWN'
if status.startswith('IN_PROGRESS'):
    print(f'LOCK: {status}', file=sys.stderr)
    print('>>> A single-batch run is IN PROGRESS. Do NOT delete any row until it completes.', file=sys.stderr)
elif status == 'FREE':
    print('LOCK: FREE (single-batch lock clear)', file=sys.stderr)
else:
    print(f'LOCK: {status!r} (unrecognized -- treat as unsafe, do not act until confirmed FREE)', file=sys.stderr)
"
LEDGER_STATE=$(bash "$SCRIPT_DIR/sheets_api.sh" read "$SHEET_ID" "'Batch Ledger'!A2:D50" 2>/dev/null || echo '{}')
echo "$LEDGER_STATE" | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rows = d.get('values', [])
except Exception:
    rows = []
active = [r[0] for r in rows if len(r) > 3 and r[3] == 'IN_PROGRESS']
if active:
    print(f'LEDGER: {len(active)} batch(es) still IN_PROGRESS: {active}', file=sys.stderr)
    print('>>> Multi-batch mode is ACTIVE. Do NOT delete any row until every batch above is DONE.', file=sys.stderr)
else:
    print('LEDGER: no IN_PROGRESS batches', file=sys.stderr)
"
echo "=== If either lock above is not clear, review-only: note the recommendation, don't delete anything yet. ===" >&2
echo "" >&2

bash "$SCRIPT_DIR/sheets_api.sh" read "$SHEET_ID" "${TAB}!A2:AF5000" | python "$SCRIPT_DIR/duplicate_scan.py"
