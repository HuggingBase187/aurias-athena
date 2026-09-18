#!/usr/bin/env python
"""
Resolves a company's most recent filed accounts document via the Companies
House REST + Document APIs, instead of scraping the public filing-history
HTML page to find a "View PDF" link.

Why this exists: Companies House's structured company/PSC/officers API
doesn't expose the actual filed accounts' figures (Revenue, PBT, average
employees) -- those live only inside the filed document itself. Every prior
lookup for those figures either scraped the public find-and-update site's
HTML for a document link, or (worse) guessed at one -- fragile, and
inconsistent with the authenticated API this pipeline already uses for PSC
chasing (ch_psc_chase.py). This does the equivalent for accounts documents:
hit /company/{number}/filing-history for the latest accounts-category
filing, resolve its document_metadata to a content URL, and hand that URL
back for downloading -- structured lookup, not scraping.

Usage: ch_accounts_fetch.py COMPANY_NUMBER
Prints JSON: {"filing_date", "description", "content_url"} for the most
recent accounts filing, or {"error": "..."} if none is found.

Downloading the actual bytes from content_url still goes through a redirect
to a presigned S3 URL, same as the public site -- ch_accounts_fetch.sh
handles that with a plain `curl -sL`, which is the proven-working part of
this pipeline. This script's job is only to find the right URL reliably.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

API_KEY = os.environ["COMPANIES_HOUSE_API_KEY"]
BASE = "https://api.company-information.service.gov.uk"


def ch_get(url):
    req = urllib.request.Request(url)
    auth = base64.b64encode(f"{API_KEY}:".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {}
        return body, e.code


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: ch_accounts_fetch.py COMPANY_NUMBER"}))
        sys.exit(1)
    company_number = sys.argv[1]

    data, status = ch_get(
        f"{BASE}/company/{company_number}/filing-history?category=accounts&items_per_page=5"
    )
    if status != 200:
        print(json.dumps({"error": f"filing_history_api_error_{status}", "detail": data}))
        sys.exit(1)

    items = data.get("items", [])
    if not items:
        print(json.dumps({"error": "no_accounts_filings_found"}))
        sys.exit(1)

    # Filing history is newest-first; the first accounts-category item is
    # the most recent filed accounts.
    latest = items[0]
    doc_metadata_url = latest.get("links", {}).get("document_metadata")
    if not doc_metadata_url:
        print(json.dumps({"error": "no_document_metadata_link_on_latest_filing", "filing": latest}))
        sys.exit(1)

    meta, meta_status = ch_get(doc_metadata_url)
    if meta_status != 200:
        print(json.dumps({"error": f"document_metadata_api_error_{meta_status}", "detail": meta}))
        sys.exit(1)

    print(json.dumps({
        "filing_date": latest.get("date"),
        "description": latest.get("description"),
        "type": latest.get("type"),
        "content_url": f"{doc_metadata_url}/content",
        "available_formats": list(meta.get("resources", {}).keys()),
    }))


if __name__ == "__main__":
    main()
