#!/usr/bin/env bash
# Test suite for sheets_api.sh — run this after ANY edit to that script,
# before trusting it against real data again.
#
# Why this exists: both real bugs found on 2026-09-18 (silent UTF-8
# corruption in write/append/batch, and the Claude-in-Chrome tool-access
# mismatch) shared one root cause — nothing actually tested the tooling's
# real behavior, so a broken assumption sat undetected across many live
# writes until it surfaced painfully in production. This suite exists so
# the next change to sheets_api.sh gets caught here instead of on a live
# batch.
#
# Safety model: every test that writes uses ONLY cells in the Batch Ledger
# tab, column J or later, row 199 or later. The real ledger (written by
# Athena/enrichment batches) only ever uses columns A-H, rows 2+, so this
# scratch zone can never collide with a real batch claim, even if one is
# being written concurrently while this suite runs. A trap clears every
# scratch cell this script touches, on success OR failure, so a crashed
# run never leaves stray data behind.
#
# Usage: bash test_sheets_api.sh   (no args)
# Exit code: 0 if all tests passed, 1 if any failed.

set -uo pipefail   # NOT -e: we want to keep running tests after a failure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHEETS_API="${SCRIPT_DIR}/sheets_api.sh"
SHEET_ID="1wf1vhj4_jvufGxpAO_3QAszTL9nSG8w6q1iVjp65-c8"
TAB="Batch Ledger"

# Scratch cells — all column J or later, row 199 or later, per the safety rule.
CELL_ENCODING="${TAB}!J199"
CELL_BATCH_1="${TAB}!J200"
CELL_BATCH_2="${TAB}!K200"
CELL_NEXTBATCH_NAME="${TAB}!J201"
CELL_NEXTBATCH_STATUS="${TAB}!K201"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# Clean up every scratch cell this suite might have touched. Registered via
# trap so it fires on normal exit AND on any early failure/interrupt.
cleanup() {
  bash "$SHEETS_API" clear "$SHEET_ID" "${TAB}!J199:K201" >/dev/null 2>&1
}
trap cleanup EXIT

echo "=== sheets_api.sh test suite ==="
echo "Scratch zone: '${TAB}' columns J-K, rows 199-201 (never collides with real ledger data in A-H, rows 2+)"
echo

# ---------------------------------------------------------------------------
# Test 1: round-trip encoding — write a string with em-dash, arrow, £, a
# double quote, and an apostrophe; read it back; assert exact match.
# This is the test that would have caught the 2026-09-18 corruption bug on
# day one: that bug silently mangled exactly these characters when they were
# passed as inline curl -d string arguments instead of via --data-binary @file.
# ---------------------------------------------------------------------------
test_encoding_roundtrip() {
  local test_str='em-dash — arrow → pound £123 quote " apostrophe '"'"'s'
  local write_json
  write_json=$(python -c "import json,sys; print(json.dumps([[sys.argv[1]]]))" "$test_str")

  local write_out
  write_out=$(bash "$SHEETS_API" write "$SHEET_ID" "$CELL_ENCODING" "$write_json" 2>&1)
  if ! echo "$write_out" | grep -q '"updatedCells": 1'; then
    fail "encoding round-trip — write call did not report success: $write_out"
    return
  fi

  local read_out
  read_out=$(bash "$SHEETS_API" read "$SHEET_ID" "$CELL_ENCODING" 2>&1)
  local read_back
  read_back=$(echo "$read_out" | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d['values'][0][0], end='')
except Exception:
    print('__READ_PARSE_FAILED__', end='')
")

  if [ "$read_back" = "$test_str" ]; then
    pass "encoding round-trip (em-dash / arrow / £ / quote / apostrophe survived intact)"
  else
    fail "encoding round-trip — wrote [$test_str] but read back [$read_back]"
  fi
}

# ---------------------------------------------------------------------------
# Test 2: next-batch mode correctness — run it against a known-safe,
# read-only range on the real Market Map, having independently read the
# same range first to compute the expected answer by hand (in Python, not
# by re-using the script's own logic), then assert the two agree.
# ---------------------------------------------------------------------------
test_next_batch_correctness() {
  local start_row=2
  local n=5
  # Read window must be wide enough to actually contain N unscreened rows —
  # next-batch itself scans up to row 5000, so a too-narrow comparison
  # window here would make this test compare apples to oranges (fewer
  # candidate rows than the thing under test actually sees).
  local read_end=$((start_row + 499))
  local raw_names raw_statuses
  raw_names=$(bash "$SHEETS_API" read "$SHEET_ID" "Market Map!B${start_row}:B${read_end}" 2>&1)
  raw_statuses=$(bash "$SHEETS_API" read "$SHEET_ID" "Market Map!AB${start_row}:AB${read_end}" 2>&1)

  # Independently compute the expected answer straight from the raw reads —
  # deliberately re-implemented here rather than re-using next-batch's own
  # logic, so this test can't just be checking the script against itself.
  # Data is piped in via stdin (not a temp-file path) because `python` here
  # may be native Windows Python, which can't resolve Git Bash's /tmp mount.
  local expected
  expected=$(printf '%s\n-----SPLIT-----\n%s\n' "$raw_names" "$raw_statuses" | python -c "
import sys, json
data = sys.stdin.read()
names_raw, statuses_raw = data.split('-----SPLIT-----', 1)
names_d = json.loads(names_raw)
statuses_d = json.loads(statuses_raw)
names = [r[0] if r else '' for r in names_d.get('values', [])]
statuses = [r[0] if r else '' for r in statuses_d.get('values', [])]
start_row = $start_row
n_wanted = $n
out = []
for i, name in enumerate(names):
    status = statuses[i] if i < len(statuses) else ''
    if name.strip() and not status.strip():
        out.append({'row': start_row + i, 'name': name})
        if len(out) >= n_wanted:
            break
print(json.dumps(out, sort_keys=True))
" 2>&1)

  local actual
  actual=$(bash "$SHEETS_API" next-batch "$SHEET_ID" "Market Map" "B" "AB" "$n" "$start_row" 2>&1)
  local actual_sorted
  actual_sorted=$(echo "$actual" | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(json.dumps(d, sort_keys=True))
except Exception:
    print('__PARSE_FAILED__')
" 2>&1)

  if [ "$expected" = "$actual_sorted" ]; then
    pass "next-batch mode returns the same rows as an independent read+compute (start_row=$start_row, n=$n)"
  else
    fail "next-batch mismatch — expected [$expected] but got [$actual_sorted]"
  fi
}

# ---------------------------------------------------------------------------
# Test 3: batch mode multi-range write — write two different scratch cells
# in one `batch` call, confirm both landed correctly, with the right values
# in the right cells (not swapped, not dropped).
# ---------------------------------------------------------------------------
test_batch_multi_range() {
  local val_a="batch-test-alpha-1"
  local val_b="batch-test-beta-2"
  local data_json
  data_json=$(python -c "
import json
print(json.dumps([
    {'range': '$CELL_BATCH_1', 'values': [['$val_a']]},
    {'range': '$CELL_BATCH_2', 'values': [['$val_b']]},
]))
")

  local batch_out
  batch_out=$(bash "$SHEETS_API" batch "$SHEET_ID" "$data_json" 2>&1)
  if ! echo "$batch_out" | grep -q '"totalUpdatedCells": 2'; then
    fail "batch multi-range write — batch call did not report 2 updated cells: $batch_out"
    return
  fi

  local read_a read_b
  read_a=$(bash "$SHEETS_API" read "$SHEET_ID" "$CELL_BATCH_1" 2>&1 | python -c "
import json,sys
try:
    print(json.load(sys.stdin)['values'][0][0], end='')
except Exception:
    print('__MISSING__', end='')
")
  read_b=$(bash "$SHEETS_API" read "$SHEET_ID" "$CELL_BATCH_2" 2>&1 | python -c "
import json,sys
try:
    print(json.load(sys.stdin)['values'][0][0], end='')
except Exception:
    print('__MISSING__', end='')
")

  if [ "$read_a" = "$val_a" ] && [ "$read_b" = "$val_b" ]; then
    pass "batch mode multi-range write — both cells landed correctly, not swapped or dropped"
  else
    fail "batch mode multi-range write — expected ($val_a, $val_b) but got ($read_a, $read_b)"
  fi
}

# ---------------------------------------------------------------------------
# Test 4: argument-validation sanity — confirm the script fails cleanly
# (non-zero exit, clear stderr message) when required args are missing,
# rather than doing something silently wrong (e.g. hitting the API with an
# empty/malformed range).
# ---------------------------------------------------------------------------
test_argument_validation() {
  local ok=1

  # No mode at all.
  if bash "$SHEETS_API" >/dev/null 2>/tmp/sheets_api_test_stderr_1; then
    ok=0
    echo "  -> no-args invocation exited 0, expected non-zero"
  fi
  if ! grep -qi "usage" /tmp/sheets_api_test_stderr_1 2>/dev/null; then
    ok=0
    echo "  -> no-args invocation did not print a usage message"
  fi

  # write mode missing the VALUES_JSON arg.
  if bash "$SHEETS_API" write "$SHEET_ID" "${TAB}!J199" >/dev/null 2>/tmp/sheets_api_test_stderr_2; then
    ok=0
    echo "  -> 'write' with missing VALUES_JSON exited 0, expected non-zero"
  fi
  if ! grep -qi "usage" /tmp/sheets_api_test_stderr_2 2>/dev/null; then
    ok=0
    echo "  -> 'write' with missing VALUES_JSON did not print a usage message"
  fi

  # unknown mode.
  if bash "$SHEETS_API" not-a-real-mode "$SHEET_ID" >/dev/null 2>/tmp/sheets_api_test_stderr_3; then
    ok=0
    echo "  -> unknown mode exited 0, expected non-zero"
  fi
  if ! grep -qi "unknown mode" /tmp/sheets_api_test_stderr_3 2>/dev/null; then
    ok=0
    echo "  -> unknown mode did not print a clear 'unknown mode' error"
  fi

  rm -f /tmp/sheets_api_test_stderr_1 /tmp/sheets_api_test_stderr_2 /tmp/sheets_api_test_stderr_3

  if [ "$ok" = "1" ]; then
    pass "argument validation — missing args and unknown modes fail cleanly with a clear message"
  else
    fail "argument validation — see details above"
  fi
}

# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
test_encoding_roundtrip
test_next_batch_correctness
test_batch_multi_range
test_argument_validation

echo
echo "=== Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed ==="

if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
exit 0
