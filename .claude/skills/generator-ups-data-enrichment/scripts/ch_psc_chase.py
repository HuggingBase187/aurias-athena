#!/usr/bin/env python
"""
Walks a Companies House PSC chain to the underlying natural person(s).

Why this exists: sourcing.md's PSC-chase rule ("go to that company's own
PSC register, repeat until named individuals") was being done by hand, one
API call and one judgment call at a time -- exactly the kind of repeated,
error-prone task that let four switchgear companies get recorded with a
corporate PSC as if it were the final answer (2026-09-16 incident). This
walks the whole chain in one call and returns the full path plus the
terminal individual(s), or a clear "can't go further" reason when the
trail runs out -- same "leave it flagged, don't guess" rule as everywhere
else in this pipeline.

v2 (2026-09-18), fixing a real wrong answer v1 gave on Saepio Solutions
(10343084): v1 ignored the PSC register's own `ceased` flag and reported
two individuals as the current PSCs when Companies House had actually
recorded them as ceased since 2024-04-10 -- the real current PSC is a
corporate entity (Aurias Bidco Ltd) that v1 couldn't chase further
because that PSC record's `identification` block had no registration
number at all (a real gap in what Companies House captures, not a bug).
v2 fixes both: ceased PSCs are excluded from the answer entirely (kept
separately for context, never mistaken for the current position), and
when a corporate PSC has no registration number, this now falls back to
a Companies House name search and continues the chase automatically when
exactly one active company matches the name (flagged in the output as
`resolved_via_name_search` so that step stays auditable, never silent).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_KEY = os.environ["COMPANIES_HOUSE_API_KEY"]
BASE = "https://api.company-information.service.gov.uk"
MAX_DEPTH = 6  # safety cap; real chains seen so far are 1-4 hops


def ch_get(path):
    req = urllib.request.Request(BASE + path)
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


def resolve_by_name_search(name):
    """Companies House sometimes records a corporate PSC with no
    registration number in the PSC filing itself. Fall back to a name
    search and only auto-continue when exactly one ACTIVE company's
    title matches the PSC name exactly (case-insensitive) -- anything
    less certain comes back as no match, not a guess."""
    q = urllib.parse.quote(name)
    data, status = ch_get(f"/search/companies?q={q}&items_per_page=10")
    if status != 200:
        return None, f"name_search_api_error_{status}"
    exact_active = [
        item for item in data.get("items", [])
        if item.get("title", "").strip().lower() == name.strip().lower()
        and item.get("company_status") == "active"
    ]
    if len(exact_active) == 1:
        return exact_active[0]["company_number"], None
    if len(exact_active) > 1:
        return None, "multiple_active_companies_share_this_exact_name"
    return None, "no_exact_active_name_match_found"


def chase(company_number, chain, seen):
    if len(chain) >= MAX_DEPTH:
        return {"chain": chain, "terminal": "max_depth_reached", "individuals": [], "ceased_psc_for_context": []}
    if company_number in seen:
        return {"chain": chain, "terminal": "cycle_detected", "individuals": [], "ceased_psc_for_context": []}
    seen.add(company_number)

    profile, status = ch_get(f"/company/{company_number}")
    company_name = profile.get("company_name", "(lookup failed)") if status == 200 else "(lookup failed)"
    hop = {"company_number": company_number, "company_name": company_name}

    psc_data, status = ch_get(f"/company/{company_number}/persons-with-significant-control")
    if status == 404:
        return {"chain": chain + [hop], "terminal": "no_psc_data_filed", "individuals": [], "ceased_psc_for_context": []}
    if status != 200:
        return {"chain": chain + [hop], "terminal": f"api_error_{status}", "individuals": [], "ceased_psc_for_context": []}

    all_items = psc_data.get("items", [])
    if not all_items:
        return {"chain": chain + [hop], "terminal": "no_psc_listed", "individuals": [], "ceased_psc_for_context": []}

    # Ceased PSCs are the #1 real failure mode here (see docstring) --
    # split them off immediately and never let them into the "current
    # answer" path, only into a clearly-labelled context list.
    ceased_context = []
    active_items = []
    for item in all_items:
        if item.get("ceased"):
            ceased_context.append({
                "name": item.get("name"),
                "kind": item.get("kind"),
                "ceased_on": item.get("ceased_on"),
            })
        else:
            active_items.append(item)

    if not active_items:
        return {"chain": chain + [hop], "terminal": "no_current_psc_all_ceased_or_none",
                "individuals": [], "ceased_psc_for_context": ceased_context}

    individuals = []
    corporate_next = None
    corporate_next_note = None

    for item in active_items:
        kind = item.get("kind", "")
        if kind == "individual-person-with-significant-control":
            individuals.append({
                "type": "individual",
                "name": item.get("name"),
                "date_of_birth": item.get("date_of_birth"),
                "nationality": item.get("nationality"),
                "country_of_residence": item.get("country_of_residence"),
                "natures_of_control": item.get("natures_of_control", []),
            })
        elif kind == "corporate-entity-person-with-significant-control":
            if corporate_next is not None:
                continue  # only chase the first active corporate PSC per hop; multiple is rare and worth a manual look
            ident = item.get("identification", {}) or {}
            reg_number = ident.get("registration_number")
            country = ident.get("country_registered") or ident.get("place_registered")
            uk_words = ("united kingdom", "uk", "england", "wales", "scotland", "northern ireland", "great britain", "companies house")
            looks_uk = bool(reg_number) and len(reg_number.strip()) == 8 and (not country or any(w in country.lower() for w in uk_words))
            if looks_uk:
                corporate_next = reg_number
            else:
                resolved_number, fail_reason = resolve_by_name_search(item.get("name", ""))
                if resolved_number:
                    corporate_next = resolved_number
                    corporate_next_note = "resolved_via_name_search"
                else:
                    individuals.append({
                        "type": "terminal_corporate_entity",
                        "name": item.get("name"),
                        "reason": f"no_registration_number_in_psc_record_and_{fail_reason} -- resolve manually on Companies House",
                        "registration_number": reg_number,
                        "country_registered": country,
                    })
        elif kind in ("legal-person-person-with-significant-control", "super-secure-person-with-significant-control"):
            individuals.append({
                "type": "terminal_legal_entity",
                "name": item.get("name", "(unnamed legal entity/trust)"),
                "reason": "not_a_registrable_uk_company -- likely a trust/partnership, chase manually if needed",
                "kind": kind,
            })
        else:
            individuals.append({"type": "unhandled_kind", "kind": kind, "raw_name": item.get("name")})

    hop["ceased_psc_at_this_hop"] = ceased_context
    if corporate_next_note:
        hop["corporate_psc_resolution"] = corporate_next_note
    result_chain = chain + [hop]

    if corporate_next:
        return chase(corporate_next, result_chain, seen)

    has_individual = any(i["type"] == "individual" for i in individuals)
    terminal = "individuals_found" if has_individual else "no_further_individuals_reachable_via_companies_house"
    return {"chain": result_chain, "terminal": terminal, "individuals": individuals, "ceased_psc_for_context": ceased_context}


def main():
    if len(sys.argv) != 2:
        print("Usage: ch_psc_chase.py COMPANY_NUMBER", file=sys.stderr)
        sys.exit(1)
    result = chase(sys.argv[1].strip(), [], set())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
