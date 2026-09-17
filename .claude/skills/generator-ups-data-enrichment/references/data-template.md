# Data template — field-by-field sourcing rules

This is the authoritative version of the per-company template. The "Legend & Sourcing Rules" tab on the live sheets is a human-readable mirror of this file — if one changes, update the other so they don't drift apart.

Column letters match the **Market Map** tab exactly (confirmed against the live sheet 2026-09-17):

| Col | Field | Sourcing rule |
|---|---|---|
| A | Number | Sequential, unique row ID. Existing numbering may have gaps or duplicates from earlier passes — fix as you touch a row, don't propagate the error. |
| B | Company Name | Legal or trading name. |
| C | Companies House Number | Search Companies House by company name. If the trading name is generic or ambiguous, get the exact legal entity name from the company's own site first (usually Terms & Conditions or Privacy Policy) and search that instead. |
| D | Website | Company's own site. |
| E | Company LinkedIn | LinkedIn company page URL. |
| F | Head Office Address | Company website or Google Maps — record which one you used. |
| G | Company Phone Number | Company website (Companies House doesn't carry phone numbers). |
| H | Equipment Category | One or more of: UPS, Backup generators, Transformers, Battery energy storage systems (BESS), Switchgears, Load banks. **List every category the company actually offers, not just the most obvious one.** A company selling both generators and switchgear gets `Backup generators, Switchgears` — dropping the second one because the first is the headline product is a real error, not a simplification. |
| I | Company Size on LinkedIn | LinkedIn's own banded size, e.g. "51-200 employees". |
| J | Associated Members on LinkedIn | LinkedIn's actual member count, e.g. "72" — a separate figure from the band above, both get recorded. |
| K | Ultimate Owner | Companies House / press — the owning entity or family, distinct from the named PSC individual. |
| L | Revenue | **Companies House filed accounts or a press release/investor-relations release only** — never an estimate, LinkedIn-derived guess, or other third-party figure. Leave blank rather than guess. |
| M | Profit Before Tax | Same sourcing rule as Revenue. Leave blank rather than guess. |
| N | Person of Significant Control (Companies House link) | `.../company/{number}/persons-with-significant-control` |
| O | Person of Significant Control Name | Companies House PSC register — **must resolve to a natural person, not a company.** See "Chasing the PSC to a real person" below when the register shows a company instead. |
| P | PSC LinkedIn | Pattern-matched then verified where possible. |
| Q | PSC Email | Pattern-matched then verified where possible. **Never a generic role address** (info@, hello@, sales@, contact@, etc.) — see "Contact rules" below. |
| R | PSC Phone | Pattern-matched then verified where possible. |
| S | CEO / MD Name | LinkedIn/website — tracked separately from the PSC, since the CEO/MD and the registered PSC are very often different people. UK small/private companies often use "Managing Director" rather than "CEO" — treat the two as the same target role, whichever title the company actually uses. |
| T | CEO / MD LinkedIn | Same treatment as PSC LinkedIn. |
| U | CEO / MD Email | Same treatment as PSC Email, **including the no-generic-address rule.** |
| V | CEO / MD Phone | Same treatment as PSC Phone. |
| W | Key OEM Partnerships | **Pair each OEM to the specific equipment category it applies to, for every category the company offers.** Format: `Category - OEM1, OEM2; Category2 - OEM3`. E.g. a company reselling Cummins and Perkins generators and Crestchic load banks gets `Generator - Cummins, Perkins; Load bank - Crestchic` — not a single flat list of OEM names with no indication of which product line each belongs to. |
| X | Type-Spec / Resale-Rental-Service | **List each of Resale / Rental / Service that genuinely applies, spelled out individually.** Never write "all" or "both" — if a company does resale and service but not rental, the cell reads `Resale, Service`. |
| Y | Services Offered | Use the real market vocabulary from the "Services Vocabulary & Search Keywords" doc's Section 2 (see `references/live-resources.md` for the doc ID) — installation, maintenance, repairs, load bank testing, etc. This is a living list; if you notice a genuinely recurring service description that isn't in it yet, add it there and flag the addition. |
| Z | Primary Sectors | End-customer sectors served, e.g. data centres, healthcare, construction. |
| AA | Sources | One citation per fact, not one blanket source for the whole row. |
| AB | Screening Verdict | In-scope / Out-of-scope (with reason) / Needs more info / Out of range — informational contact. Never left blank. |
| AC | Notes | Free text — acquisition history, anything else that doesn't fit elsewhere. |

## The sizing heuristic

Revenue is rarely disclosed for small private companies, so use **LinkedIn headcount as the triage proxy** (Company Size band + Associated Members count, columns I and J). Companies with **30–100 staff are in scope by default** — a wide, inclusive band, not a narrow target. Only mark one out-of-scope within that band if you know otherwise with real certainty. Below ~30 is usually too small; above ~100 needs more scrutiny before ruling in or out — check Ultimate Owner (column K) before ruling out on headcount alone, since a large group-level figure can mask a right-sized subsidiary or division.

## Chasing the PSC to a real person

Companies House often shows another company as the PSC rather than an individual — that's a pointer to keep following, not the answer. When PSC comes back as a company:

1. Note the intermediate entity in Ultimate Owner (column K) — it's real information, don't discard it.
2. Look up that company's own PSC register on Companies House.
3. Repeat until you reach one or more **named individuals**. Group structures sometimes go several layers deep — keep going until there's nowhere further to go, not just one hop.
4. If it's more than one layer, record the full chain (e.g. "PSC: R & B Switchgear Holdings Limited → ultimate PSC: Max Elliott Beswick") in Ultimate Owner or Notes, so the reasoning is traceable.

Stopping at the first company name found is the same category of error as leaving a fact silently blank — it looks like a finding but isn't one.

## Contact rules

A blank contact cell is honest; a generic one looks like a finding but isn't. For PSC Email (Q) and CEO/MD Email (U):

- Never a generic role address — info@, hello@, sales@, contact@, admin@, or similar.
- If the named person's real personal/direct email can't be found, **leave the cell blank.** Don't fill it with a generic address just to avoid an empty cell.
- Email verification/bounce-testing isn't something this skill does — record an email as found-but-unverified rather than trying to self-verify.

## What "qualified" means

A company is ready to copy into the Qualified Leads tab once you've: verified headcount (LinkedIn band + member count) and ownership (Companies House PSC, chased to a real person) independently of the company's own website, and checked for an obvious disqualifier (PE-owned, part of a large group, wrong sub-sector, recently acquired, out of the 30-100 headcount band without good reason). When you can't find or confirm something, leave it blank — don't guess, and don't quietly upgrade a guess into a stated fact.
