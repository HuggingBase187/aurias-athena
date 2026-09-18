"""Deterministic quality gate for market-map rows (no LLM anywhere in this file).

Why this exists: "junk in, junk out" (Daniel, 2026-09-18). The legacy Gemini list
carried fake and dead companies that each cost a full enrichment pass before
anyone noticed. This gate runs the cheap, factual checks first -- Companies
House match, company status, filed-accounts size class, website liveness,
duplicates -- so only real, live, plausibly-sized companies reach enrichment.
The same gate is meant to guard the Discovery Staging -> master promotion.

READ-ONLY: never writes to any sheet. Emits a JSON report.

Usage:
  python quality_gate.py ROWS_JSON OUT_JSON
    ROWS_JSON: Sheets API values JSON for a tab read from column A (header row
               included), e.g. `sheets_api.sh read SHEET "Market Map!A1:AF2000"`.
    Needs COMPANIES_HOUSE_API_KEY in the environment.

Verdicts:
  PASS            live Companies House company, name agrees, not micro/dormant.
  FAIL_DISSOLVED  the row's own recorded Companies House number is dissolved /
                  in liquidation / administration etc.
  FAIL_TOO_SMALL  the row's own recorded number files micro-entity or dormant
                  accounts (can't be near the PBT GBP 1m floor).
  (Both FAILs need a recorded CH number. A match found only by name search is
  always REVIEW -- a same-name company is too often a different business.)
  FAIL_NO_COMPANY no Companies House match AND website missing or dead
                  -> suspected hallucination.
  REVIEW          anything ambiguous (name mismatch, CH found only by name search,
                  no CH but a live website, duplicate CH number). A human or the
                  enrichment Skill decides; the gate never guesses.
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import base64

CH = "https://api.company-information.service.gov.uk"
KEY = os.environ.get("COMPANIES_HOUSE_API_KEY", "")
AUTH = "Basic " + base64.b64encode(f"{KEY}:".encode()).decode()
DEAD_STATUSES = {"dissolved", "liquidation", "receivership", "administration",
                 "converted-closed", "insolvency-proceedings", "voluntary-arrangement", "removed", "closed"}
SMALL_ACCOUNTS = {"micro-entity", "dormant"}
STOP = {"ltd", "limited", "plc", "llp", "uk", "the", "and", "co", "company", "group", "services", "service"}


def norm_tokens(name):
    return {t for t in re.findall(r"[a-z0-9]+", (name or "").lower().replace("&", " and ")) if t not in STOP}


def similarity(a, b):
    ta, tb = norm_tokens(a), norm_tokens(b)
    if not ta or not tb:
        return 0.0
    if "".join(sorted(ta)) == "".join(sorted(tb)) or "".join(ta) == "".join(tb):
        return 1.0
    # "All-Power" vs "ALLPOWER": compare with spaces removed, in original word order
    ja = "".join(re.findall(r"[a-z0-9]+", a.lower())); jb = "".join(re.findall(r"[a-z0-9]+", b.lower()))
    for sw in ("limited", "ltd", "plc", "llp"):
        ja, jb = ja.removesuffix(sw), jb.removesuffix(sw)
    if ja and ja == jb:
        return 1.0
    return len(ta & tb) / min(len(ta), len(tb))


def ch_get(path, retries=4):
    for attempt in range(retries):
        req = urllib.request.Request(CH + path, headers={"Authorization": AUTH})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            time.sleep(2)
    raise RuntimeError(f"Companies House unreachable for {path}")


def check_ch(name, number):
    """Return dict with ch_status, ch_name, ch_number, accounts_type, how."""
    number = re.sub(r"\s", "", number or "").upper()
    if number and re.fullmatch(r"[A-Z]{0,2}\d{4,8}", number):
        number = number.zfill(8) if number.isdigit() else number
        prof = ch_get(f"/company/{number}")
        time.sleep(0.25)
        if prof:
            return {"how": "number", "ch_number": number, "ch_name": prof.get("company_name"),
                    "ch_status": prof.get("company_status"),
                    "accounts_type": ((prof.get("accounts") or {}).get("last_accounts") or {}).get("type"),
                    "name_similarity": round(similarity(name, prof.get("company_name")), 2)}
        return {"how": "number_not_found", "ch_number": number}
    # No usable number: search by name, accept only a strong, unique-ish hit.
    res = ch_get("/search/companies?" + urllib.parse.urlencode({"q": name, "items_per_page": 5})) or {}
    time.sleep(0.25)
    best = None
    for it in res.get("items", []):
        s = similarity(name, it.get("title"))
        if s >= 0.99 and (best is None or s > best[0]):
            best = (s, it)
    if best:
        it = best[1]
        prof = ch_get(f"/company/{it['company_number']}") or {}
        time.sleep(0.25)
        return {"how": "name_search", "ch_number": it["company_number"], "ch_name": it.get("title"),
                "ch_status": prof.get("company_status", it.get("company_status")),
                "accounts_type": ((prof.get("accounts") or {}).get("last_accounts") or {}).get("type"),
                "name_similarity": round(best[0], 2)}
    return {"how": "no_match"}


def check_site(url):
    """live / live_blocked / unreachable (timeout, TLS) / dead (domain doesn't resolve) / none.

    Website cells sometimes carry notes around the address, so pull out the
    first domain-looking token. Only a failed DNS lookup on every variant
    counts as "dead" -- a timeout or TLS error means something is there.
    """
    m = re.search(r"(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(/[^\s,;)]*)?", url or "", re.I)
    if not m:
        return "none"
    host, path = m.group(1).lower(), m.group(2) or ""
    hosts = [host] + ([f"www.{host}"] if not host.startswith("www.") else [host[4:]])
    outcome = "dead"
    for h in hosts:
        for scheme in ("https", "http"):
            try:
                req = urllib.request.Request(f"{scheme}://{h}{path}", headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=12) as r:
                    if r.status < 400:
                        return "live"
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 405, 406, 429, 503):
                    return "live_blocked"
                outcome = f"http_{e.code}"
            except urllib.error.URLError as e:
                if "getaddrinfo" not in str(e.reason) and "Name or service" not in str(e.reason):
                    outcome = "unreachable" if outcome == "dead" else outcome
            except Exception:
                outcome = "unreachable" if outcome == "dead" else outcome
    return outcome


def verdict(ch, site, dup):
    status = ch.get("ch_status")
    if ch["how"] == "name_search":
        # A name match alone proves nothing: on the 2026-09-18 legacy run, 31 of
        # 77 name-only matches were a different company with the same name.
        # Report what the match shows, but never fail a row on it.
        return "REVIEW", (f"name-only match {ch.get('ch_name')} {ch.get('ch_number')} "
                          f"({status}; accounts {ch.get('accounts_type')}) — confirm by address or website")
    if ch["how"] == "number" and status in DEAD_STATUSES:
        return "FAIL_DISSOLVED", f"Companies House status: {status}"
    if ch["how"] in ("no_match", "number_not_found"):
        if site in ("none", "dead"):
            return "FAIL_NO_COMPANY", f"no Companies House match; website {site}"
        return "REVIEW", f"no Companies House match but website {site} (trading name / sole trader?)"
    if dup:
        return "REVIEW", f"Companies House number shared with row(s) {dup}"
    if ch["how"] == "number" and ch.get("name_similarity", 0) < 0.5:
        return "REVIEW", f"recorded CH number belongs to '{ch.get('ch_name')}'"
    if ch.get("accounts_type") in SMALL_ACCOUNTS:
        return "FAIL_TOO_SMALL", f"latest accounts filed as {ch.get('accounts_type')}"
    return "PASS", f"{status}; accounts {ch.get('accounts_type')}; website {site}"


def main():
    if not KEY:
        sys.exit("COMPANIES_HOUSE_API_KEY not set")
    values = json.load(open(sys.argv[1], encoding="utf-8"))["values"]
    header = values[0]
    col = {h: i for i, h in enumerate(header)}
    get = lambda r, h: (r[col[h]] if h in col and len(r) > col[h] else "").strip()
    rows = [(i + 1, r) for i, r in enumerate(values) if i > 0 and len(r) > 1 and r[1].strip()]

    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        sites = dict(zip([n for n, _ in rows], ex.map(lambda x: check_site(get(x[1], "Website")), rows)))

    results, seen = [], {}
    for n, r in rows:
        ch = check_ch(get(r, "Company Name"), get(r, "Companies House Number"))
        num = ch.get("ch_number") if ch["how"] in ("number", "name_search") else None
        dup = seen.get(num)
        if num:
            seen.setdefault(num, n)
        v, why = verdict(ch, sites[n], dup)
        results.append({"row": n, "company": get(r, "Company Name"),
                        "has_verdict": bool(get(r, "Screening Verdict")),
                        "verdict": v, "why": why, "website": sites[n], **ch})
        print(f"{n}\t{v}\t{get(r, 'Company Name')}\t{why}", flush=True)

    json.dump(results, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
