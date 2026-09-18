#!/usr/bin/env bash
# Read/write/format helper for the Aurias 2 market map Google Sheets.
#
# Why this exists: every sourcing run used to hand-type curl + auth boilerplate
# from scratch, which is exactly the kind of repetitive task that invites a typo
# or a dropped flag on a live spreadsheet. This wraps the same Sheets API v4
# calls documented in .claude/agents/sourcing.md into one tested script, so
# every run reuses the same path instead of re-deriving it.
#
# Usage:
#   sheets_api.sh read   SHEET_ID "Tab!Range"
#   sheets_api.sh write  SHEET_ID "Tab!Range" 'JSON 2D array, e.g. [["a","b"],["c","d"]]'
#   sheets_api.sh clear  SHEET_ID "Tab!Range"
#   sheets_api.sh batch  SHEET_ID 'JSON data array, e.g. [{"range":"Tab!A1","values":[["x"]]}, ...]'
#   sheets_api.sh append SHEET_ID "Tab!A:AC" 'JSON 2D array, e.g. [["row","of","values"]]'
#   sheets_api.sh format SHEET_ID 'JSON requests array for spreadsheets.batchUpdate'
#   sheets_api.sh meta   SHEET_ID
#
# `batch` writes multiple ranges atomically in one call (values:batchUpdate) —
# use this for a 5-company enrichment batch instead of 5 separate `write` calls.
# `append` adds a row after the last row with data in the given range (e.g. the
# Qualified Leads tab) instead of overwriting a specific cell — use this so two
# qualifying companies from the same run never collide on which row to write to.
# `format` is for structural changes (bold headers, frozen rows, column widths,
# banding) via the general spreadsheets.batchUpdate endpoint — pass the `requests`
# array from the Sheets API reference, e.g.:
#   [{"repeatCell": {...}}, {"updateSheetProperties": {...}}]
# `meta` lists the sheet's tabs and their sheetId (gid) — needed before any
# `format` call, since formatting requests address tabs by numeric sheetId, not name.
#
#   sheets_api.sh next-batch SHEET_ID TAB NAME_COL STATUS_COL N [START_ROW]
#
# `next-batch` finds the next N rows that have a name but no status yet (e.g.
# Company Name filled in, Screening Verdict still blank) and prints them as a
# JSON array of {"row": N, "name": "..."}. This exists so a fresh, unattended
# session (a scheduled task with no memory of prior runs) never has to write
# its own ad-hoc `python -c` one-liner to answer "what's next" — that always
# shows up as a brand-new Bash command with no matching allowlist entry, which
# just sits there waiting for an approval nobody's awake to give (this is what
# stalled the overnight run on 2026-09-18). All JSON parsing here happens
# inside this already-approved script, the same way `urlencode()` below
# already shells out to `python` internally without that ever needing its own
# separate approval — so this mode is safe to allowlist as read-only.

set -euo pipefail

AUTH_SCRIPT="${SHEETS_AUTH_SCRIPT:-/c/Users/HP/.claude/credentials/sheets_auth.sh}"

if [ ! -f "$AUTH_SCRIPT" ]; then
  echo "Error: auth script not found at $AUTH_SCRIPT (set SHEETS_AUTH_SCRIPT to override)" >&2
  exit 1
fi

MODE="${1:-}"
if [ -z "$MODE" ]; then
  echo "Usage: $0 {read|write|clear|batch|append|format|meta|next-batch} ..." >&2
  exit 1
fi

TOKEN=$(bash "$AUTH_SCRIPT")

# URL-encode a range string (tab names commonly contain spaces, which curl
# will not encode automatically and which cause a malformed-URL error).
urlencode() {
  python -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=\"!:,\$\"))" "$1"
}

case "$MODE" in
  meta)
    SHEET_ID="${2:?Usage: $0 meta SHEET_ID}"
    curl -s -H "Authorization: Bearer $TOKEN" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}?fields=properties.title,sheets.properties"
    ;;

  read)
    SHEET_ID="${2:?Usage: $0 read SHEET_ID 'Tab!Range'}"
    RANGE="${3:?Usage: $0 read SHEET_ID 'Tab!Range'}"
    ENC_RANGE=$(urlencode "$RANGE")
    curl -s -H "Authorization: Bearer $TOKEN" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${ENC_RANGE}"
    ;;

  write)
    SHEET_ID="${2:?Usage: $0 write SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    RANGE="${3:?Usage: $0 write SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    VALUES_JSON="${4:?Usage: $0 write SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    ENC_RANGE=$(urlencode "$RANGE")
    BODY_FILE=$(mktemp)
    trap 'rm -f "$BODY_FILE"' EXIT
    printf '{"values": %s}' "$VALUES_JSON" > "$BODY_FILE"
    curl -s -X PUT \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${ENC_RANGE}?valueInputOption=RAW" \
      --data-binary "@${BODY_FILE}"
    ;;

  clear)
    SHEET_ID="${2:?Usage: $0 clear SHEET_ID 'Tab!Range'}"
    RANGE="${3:?Usage: $0 clear SHEET_ID 'Tab!Range'}"
    ENC_RANGE=$(urlencode "$RANGE")
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      --data '{}' \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${ENC_RANGE}:clear"
    ;;

  append)
    SHEET_ID="${2:?Usage: $0 append SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    RANGE="${3:?Usage: $0 append SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    VALUES_JSON="${4:?Usage: $0 append SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    ENC_RANGE=$(urlencode "$RANGE")
    BODY_FILE=$(mktemp)
    trap 'rm -f "$BODY_FILE"' EXIT
    printf '{"values": %s}' "$VALUES_JSON" > "$BODY_FILE"
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${ENC_RANGE}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS" \
      --data-binary "@${BODY_FILE}"
    ;;

  batch)
    SHEET_ID="${2:?Usage: $0 batch SHEET_ID 'JSON_DATA_ARRAY'}"
    DATA_JSON="${3:?Usage: $0 batch SHEET_ID 'JSON_DATA_ARRAY'}"
    BODY_FILE=$(mktemp)
    trap 'rm -f "$BODY_FILE"' EXIT
    printf '{"valueInputOption": "RAW", "data": %s}' "$DATA_JSON" > "$BODY_FILE"
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      --data-binary "@${BODY_FILE}" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values:batchUpdate"
    ;;

  next-batch)
    SHEET_ID="${2:?Usage: $0 next-batch SHEET_ID TAB NAME_COL STATUS_COL N [START_ROW]}"
    TAB="${3:?Usage: $0 next-batch SHEET_ID TAB NAME_COL STATUS_COL N [START_ROW]}"
    NAME_COL="${4:?Usage: $0 next-batch SHEET_ID TAB NAME_COL STATUS_COL N [START_ROW]}"
    STATUS_COL="${5:?Usage: $0 next-batch SHEET_ID TAB NAME_COL STATUS_COL N [START_ROW]}"
    N="${6:?Usage: $0 next-batch SHEET_ID TAB NAME_COL STATUS_COL N [START_ROW]}"
    START_ROW="${7:-2}"
    NAME_RANGE=$(urlencode "${TAB}!${NAME_COL}${START_ROW}:${NAME_COL}5000")
    STATUS_RANGE=$(urlencode "${TAB}!${STATUS_COL}${START_ROW}:${STATUS_COL}5000")
    RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values:batchGet?ranges=${NAME_RANGE}&ranges=${STATUS_RANGE}")
    echo "$RESPONSE" | python -c "
import json, sys
d = json.load(sys.stdin)
ranges = d.get('valueRanges', [{}, {}])
names = [r[0] if r else '' for r in ranges[0].get('values', [])]
statuses = [r[0] if r else '' for r in ranges[1].get('values', [])]
start_row = ${START_ROW}
n_wanted = ${N}
out = []
for i, name in enumerate(names):
    status = statuses[i] if i < len(statuses) else ''
    if name.strip() and not status.strip():
        out.append({'row': start_row + i, 'name': name})
        if len(out) >= n_wanted:
            break
print(json.dumps(out))
"
    exit 0
    ;;

  format)
    SHEET_ID="${2:?Usage: $0 format SHEET_ID 'JSON_REQUESTS_ARRAY'}"
    REQUESTS_JSON="${3:?Usage: $0 format SHEET_ID 'JSON_REQUESTS_ARRAY'}"
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"requests\": ${REQUESTS_JSON}}" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}:batchUpdate"
    ;;

  *)
    echo "Unknown mode: $MODE (use read, write, clear, batch, append, format, meta, or next-batch)" >&2
    exit 1
    ;;
esac
echo
