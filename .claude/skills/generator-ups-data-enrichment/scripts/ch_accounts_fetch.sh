#!/usr/bin/env bash
# Downloads a company's most recent filed accounts document via the
# Companies House API instead of scraping the public filing-history page.
#
# Why this exists (2026-09-18): every prior lookup for a company's Revenue/
# PBT/average-employees figures either scraped find-and-update.company-
# information.service.gov.uk's HTML for a "View PDF" link, or (a few times
# tonight) hit a presigned-S3-redirect fetch failure and gave up, leaving
# the figures wrongly marked unextractable. Companies House's own API
# (same key already used by ch_psc_chase.sh) can resolve the correct
# document reliably instead -- see ch_accounts_fetch.py for why the
# structured API is used for finding the document, while the final byte
# download still goes through the same curl-follows-redirect approach
# that's already proven to work against the resulting presigned URL.
#
# Usage: ch_accounts_fetch.sh COMPANY_NUMBER [OUTPUT_PDF_PATH]
#   OUTPUT_PDF_PATH defaults to ./accounts_<COMPANY_NUMBER>.pdf
set -euo pipefail

ENV_FILE="${CH_ENV_FILE:-/c/Users/HP/OneDrive/Desktop/Claude — OS/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env not found at $ENV_FILE (set CH_ENV_FILE to override)" >&2
  exit 1
fi

COMPANY_NUMBER="${1:?Usage: $0 COMPANY_NUMBER [OUTPUT_PDF_PATH]}"
OUTPUT_PATH="${2:-./accounts_${COMPANY_NUMBER}.pdf}"

COMPANIES_HOUSE_API_KEY=$(grep '^COMPANIES_HOUSE_API_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2-)
if [ -z "${COMPANIES_HOUSE_API_KEY:-}" ]; then
  echo "Error: COMPANIES_HOUSE_API_KEY not found in $ENV_FILE" >&2
  exit 1
fi
export COMPANIES_HOUSE_API_KEY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVED=$(python "$SCRIPT_DIR/ch_accounts_fetch.py" "$COMPANY_NUMBER")

CONTENT_URL=$(echo "$RESOLVED" | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('content_url',''))")
if [ -z "$CONTENT_URL" ]; then
  echo "Error resolving accounts document:" >&2
  echo "$RESOLVED" >&2
  exit 1
fi

echo "$RESOLVED" >&2
curl -sL -u "${COMPANIES_HOUSE_API_KEY}:" -o "$OUTPUT_PATH" "$CONTENT_URL"
echo "Downloaded to: $OUTPUT_PATH"
file "$OUTPUT_PATH" 2>/dev/null || true
