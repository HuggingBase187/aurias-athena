#!/usr/bin/env bash
# Read/write helper for Google Docs, using the same Aurias Athena service
# account as sheets_api.sh (same auth script, wider scope as of 2026-09-18).
#
# Why this exists: editing a live Google Doc (Services Vocabulary & Search
# Keywords, Near Miss Rules) used to mean "trash + recreate" via browser
# automation -- slow, and one more thing that can go visibly wrong on a
# doc Daniel might have open. This replaces that with the same direct-API
# pattern the Sheets integration already uses, once Daniel enabled the
# Docs API on the same GCP project (2026-09-18).
#
# Usage:
#   docs_api.sh get     DOC_ID              -- full document JSON (structure)
#   docs_api.sh text     DOC_ID              -- just the plain text content
#   docs_api.sh append   DOC_ID 'TEXT'       -- appends TEXT at the very end
#   docs_api.sh replace  DOC_ID 'OLD' 'NEW'  -- exact-text find/replace, whole doc
#
# `replace` is also the safe way to do a targeted insert: doc authors should
# keep a stable marker line (e.g. "-- add new entries above this line --")
# in any section meant to grow, then `replace` the marker with
# "new entry\n-- add new entries above this line --". Docs API edits are
# index-based and indices shift after every edit, the same class of fragility
# as Sheets row numbers -- replaceAllText matches by text instead, so it
# never needs to know indices at all. Don't try to compute an insert index
# by hand; restructure the ask into a replace against a stable anchor instead.
set -euo pipefail

AUTH_SCRIPT="${SHEETS_AUTH_SCRIPT:-/c/Users/HP/.claude/credentials/sheets_auth.sh}"

if [ ! -f "$AUTH_SCRIPT" ]; then
  echo "Error: auth script not found at $AUTH_SCRIPT (set SHEETS_AUTH_SCRIPT to override)" >&2
  exit 1
fi

MODE="${1:-}"
if [ -z "$MODE" ]; then
  echo "Usage: $0 {get|text|append|replace} ..." >&2
  exit 1
fi

TOKEN=$(bash "$AUTH_SCRIPT")

case "$MODE" in
  get)
    DOC_ID="${2:?Usage: $0 get DOC_ID}"
    curl -s -H "Authorization: Bearer $TOKEN" \
      "https://docs.googleapis.com/v1/documents/${DOC_ID}"
    ;;

  text)
    DOC_ID="${2:?Usage: $0 text DOC_ID}"
    curl -s -H "Authorization: Bearer $TOKEN" \
      "https://docs.googleapis.com/v1/documents/${DOC_ID}" | python -c "
import json, sys
d = json.load(sys.stdin)
def walk(elements):
    out = []
    for el in elements:
        if 'paragraph' in el:
            for pe in el['paragraph'].get('elements', []):
                tr = pe.get('textRun')
                if tr:
                    out.append(tr.get('content', ''))
        elif 'table' in el:
            for row in el['table'].get('tableRows', []):
                for cell in row.get('tableCells', []):
                    out.append(walk(cell.get('content', [])))
    return ''.join(out)
print(walk(d.get('body', {}).get('content', [])))
"
    ;;

  append)
    DOC_ID="${2:?Usage: $0 append DOC_ID 'TEXT'}"
    TEXT="${3:?Usage: $0 append DOC_ID 'TEXT'}"
    END_INDEX=$(curl -s -H "Authorization: Bearer $TOKEN" \
      "https://docs.googleapis.com/v1/documents/${DOC_ID}?fields=body.content(endIndex)" | \
      python -c "
import json, sys
d = json.load(sys.stdin)
content = d.get('body', {}).get('content', [])
print(content[-1]['endIndex'] - 1 if content else 1)
")
    BODY_FILE=$(mktemp)
    trap 'rm -f "$BODY_FILE"' EXIT
    python -c "
import json, sys
index, text = int(sys.argv[1]), sys.argv[2]
print(json.dumps({'requests':[{'insertText':{'location':{'index':index},'text':text}}]}))
" "$END_INDEX" "$TEXT" > "$BODY_FILE"
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      --data-binary "@${BODY_FILE}" \
      "https://docs.googleapis.com/v1/documents/${DOC_ID}:batchUpdate"
    ;;

  replace)
    if [ "$#" -lt 4 ]; then
      echo "Usage: $0 replace DOC_ID 'OLD' 'NEW' (NEW may be empty, to delete OLD)" >&2
      exit 1
    fi
    DOC_ID="$2"
    OLD_TEXT="$3"
    NEW_TEXT="$4"
    BODY_FILE=$(mktemp)
    trap 'rm -f "$BODY_FILE"' EXIT
    python -c "
import json, sys
old_text, new_text = sys.argv[1], sys.argv[2]
print(json.dumps({'requests':[{'replaceAllText':{
    'containsText': {'text': old_text, 'matchCase': True},
    'replaceText': new_text
}}]}))
" "$OLD_TEXT" "$NEW_TEXT" > "$BODY_FILE"
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      --data-binary "@${BODY_FILE}" \
      "https://docs.googleapis.com/v1/documents/${DOC_ID}:batchUpdate"
    ;;

  *)
    echo "Unknown mode: $MODE (use get, text, append, or replace)" >&2
    exit 1
    ;;
esac
echo
