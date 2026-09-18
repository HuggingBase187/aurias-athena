#!/usr/bin/env bash
# Chases a Companies House PSC entry through corporate layers to the
# underlying natural person(s) -- see ch_psc_chase.py for why this exists.
#
# Usage: ch_psc_chase.sh COMPANY_NUMBER
set -euo pipefail

ENV_FILE="${CH_ENV_FILE:-/c/Users/HP/OneDrive/Desktop/Claude — OS/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env not found at $ENV_FILE (set CH_ENV_FILE to override)" >&2
  exit 1
fi

COMPANY_NUMBER="${1:?Usage: $0 COMPANY_NUMBER}"

COMPANIES_HOUSE_API_KEY=$(grep '^COMPANIES_HOUSE_API_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2-)
if [ -z "${COMPANIES_HOUSE_API_KEY:-}" ]; then
  echo "Error: COMPANIES_HOUSE_API_KEY not found in $ENV_FILE" >&2
  exit 1
fi
export COMPANIES_HOUSE_API_KEY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/ch_psc_chase.py" "$COMPANY_NUMBER"
