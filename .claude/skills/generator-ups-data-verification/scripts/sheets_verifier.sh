#!/usr/bin/env bash
# Read/log helper for generator-ups-data-verification and generator-ups-near-misses-update.
#
# Why this exists: the verifier subagent needs to read the full market-map
# sheet to check facts against it, and needs to write its own accuracy score
# and near-miss sweep results somewhere — but must never be able to touch
# Market Map, Qualified Leads, or Flagged to You (see the "What you never do"
# section of generator-ups-data-verification/SKILL.md, and the 2026-09-18
# incident that motivated it). Rather than trust a written rule to hold that
# line, this script makes it structural: `read`/`meta` work against any tab,
# but `log` (the only write mode) refuses anything that isn't the
# Verification Log or Near-Miss Review Log tab. There is no write/batch/clear/
# format mode in this script at all, so there's nothing to misuse.
#
# Usage:
#   sheets_verifier.sh read SHEET_ID "Tab!Range"
#   sheets_verifier.sh meta SHEET_ID
#   sheets_verifier.sh log  SHEET_ID "Tab!Range" 'JSON 2D array, e.g. [["a","b"]]'
#
# `log` behaves like sheets_api.sh's `append` (adds a row after the last row
# with data), but only against "Verification Log" or "Near-Miss Review Log" —
# anything else is refused before any request is sent.

set -euo pipefail

AUTH_SCRIPT="${SHEETS_AUTH_SCRIPT:-/c/Users/HP/.claude/credentials/sheets_auth.sh}"

if [ ! -f "$AUTH_SCRIPT" ]; then
  echo "Error: auth script not found at $AUTH_SCRIPT (set SHEETS_AUTH_SCRIPT to override)" >&2
  exit 1
fi

MODE="${1:-}"
if [ -z "$MODE" ]; then
  echo "Usage: $0 {read|meta|log} ..." >&2
  exit 1
fi

TOKEN=$(bash "$AUTH_SCRIPT")

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

  log)
    SHEET_ID="${2:?Usage: $0 log SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    RANGE="${3:?Usage: $0 log SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    VALUES_JSON="${4:?Usage: $0 log SHEET_ID 'Tab!Range' 'JSON_VALUES'}"
    case "$RANGE" in
      "Verification Log"*|"Near-Miss Review Log"*) ;;
      *)
        echo "Error: log mode only writes to 'Verification Log' or 'Near-Miss Review Log' — refused range: $RANGE" >&2
        exit 1
        ;;
    esac
    ENC_RANGE=$(urlencode "$RANGE")
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      "https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${ENC_RANGE}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS" \
      -d "{\"values\": ${VALUES_JSON}}"
    ;;

  *)
    echo "Unknown mode: $MODE (use read, meta, or log)" >&2
    exit 1
    ;;
esac
echo
