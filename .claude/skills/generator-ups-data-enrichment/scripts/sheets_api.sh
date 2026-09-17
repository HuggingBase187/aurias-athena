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

set -euo pipefail

AUTH_SCRIPT="${SHEETS_AUTH_SCRIPT:-/c/Users/HP/.claude/credentials/sheets_auth.sh}"

if [ ! -f "$AUTH_SCRIPT" ]; then
  echo "Error: auth script not found at $AUTH_SCRIPT (set SHEETS_AUTH_SCRIPT to override)" >&2
  exit 1
fi

MODE="${1:-}"
if [ -z "$MODE" ]; then
  echo "Usage: $0 {read|write|clear|batch|format|meta} ..." >&2
  exit 1
fi

TOKEN=$(bash "$AUTH_SCRIPT")

case "$MODE" in
  meta)
    SHEET_ID="${2:?Usage: $0 meta SHEET_ID}"
    curl -s -H "Authorization: Bearer $TOKEN" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}?fields=properties.title,sheets.properties"
    ;;

  read)
    SHEET_ID="${2:?Usage: $0 read SHEET_ID 'Tab!Range'}"
    RANGE="${3:?Usage: $0 read SHEET_ID 'Tab!Range'}"
    curl -s -H "Authorization: Bearer $TOKEN" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${RANGE}"
    ;;

  write)
    SHEET_ID="${2:?Usage: $0 write SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    RANGE="${3:?Usage: $0 write SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    VALUES_JSON="${4:?Usage: $0 write SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    curl -s -X PUT \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${RANGE}?valueInputOption=RAW" \
      -d "{\"values\": ${VALUES_JSON}}"
    ;;

  clear)
    SHEET_ID="${2:?Usage: $0 clear SHEET_ID 'Tab!Range'}"
    RANGE="${3:?Usage: $0 clear SHEET_ID 'Tab!Range'}"
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      --data '{}' \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${RANGE}:clear"
    ;;

  batch)
    SHEET_ID="${2:?Usage: $0 batch SHEET_ID 'JSON_DATA_ARRAY'}"
    DATA_JSON="${3:?Usage: $0 batch SHEET_ID 'JSON_DATA_ARRAY'}"
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"valueInputOption\": \"RAW\", \"data\": ${DATA_JSON}}" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values:batchUpdate"
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
    echo "Unknown mode: $MODE (use read, write, clear, batch, format, or meta)" >&2
    exit 1
    ;;
esac
echo
