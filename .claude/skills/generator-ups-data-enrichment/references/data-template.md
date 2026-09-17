# Data template — field-by-field sourcing rules

This is the authoritative version of the per-company template. The "Legend & Sourcing Rules" tab on the live sheets is a human-readable mirror of this file — if one changes, update the other so they don't drift apart.

Column letters match the **Market Map** tab exactly (confirmed against the live sheet 2026-09-17, including the "Employees - Companies House" column added that day between Associated Members and Ultimate Owner — everything from K onward shifted one letter right when it was inserted):

| Col | Field | Sourcing rule |
|---|---|---|
| A | Number | Sequential, unique row ID. Existing numbering may have gaps or duplicates from earlier passes — fix as you touch a row, don't propagate the error. |
| B | Company Name | Legal or trading name. |
| C | Companies House Number | Search Companies House by company name. If the trading name is generic or ambiguous, get the exact legal entity name from the company's own site first (usually Terms & Conditions or Privacy Policy) and search that instead. |
| D | Website | Company's own site. |
| E | Company LinkedIn | LinkedIn company page URL. |
| F | Head Office Address | Company website or Google Maps — record which one you used. |
| G | Company Phone Number | Company website (Companies House doesn't carry phone numbers). |
| H | Equipment Category | One or more of: UPS, Backup generators, Transformers, Battery energy storage systems (BESS), Switchgears, Load banks. **List every category the company actually offers, not just the most obvious one.** A company selling both generators and switchgear gets `Backup generators, Switchgears` — dropping the second one because the first is the headline product is a real error, not a simplification. Note this is deliberately 6 items, not the 7 named in the overall Scope — "Critical power services" is a *service*, not a piece of equipment, so it never appears in this column. A company doing critical power services work still gets categorized here by whichever equipment it actually services (e.g. a firm doing 24/7 critical-power maintenance across generators and UPS gets `Backup generators, UPS`), and the service itself is captured in Services Offered (column Z) and Type-Spec (column Y) instead. |
| I | Company Size on LinkedIn | LinkedIn's own banded size, e.g. "51-200 employees". |
| J | Associated Members on LinkedIn | LinkedIn's actual member count, e.g. "72" — a real number, not a band. Found on the company's LinkedIn page itself (the "X associated members" line on the About page) — actively look it up via the Claude-in-Chrome browser tool, don't leave it blank by default. Only leave it blank if you've genuinely tried and the page won't yield a number. |
| K | Employees - Companies House | **Added 2026-09-17, and now the anchor headcount signal alongside J.** The "average number of employees" note in the company's filed accounts (usually Note 3-5, sometimes higher-numbered — search the PDF for "average number of employees" or "monthly average number of persons employed"). This is disclosed even in many micro-entity/abridged filings that omit the P&L, so it's often available even when Revenue/PBT (columns M/N) aren't. See the sizing heuristic below — this and column J (Associated Members) are the two figures that actually decide the working headcount; column I (the LinkedIn band) is recorded for context only. |
| L | Ultimate Owner | Companies House / press — the owning entity or family, distinct from the named PSC individual. |
| M | Revenue | **Companies House filed accounts or a press release/investor-relations release only** — never an estimate, LinkedIn-derived guess, or other third-party figure. **Never leave this cell truly empty (Daniel, 2026-09-18).** If the figure genuinely can't be found, write the reason directly *in the cell itself* — e.g. "Not disclosed - micro-entity accounts (FRS 105), no income statement filed" or "Not disclosed - FY2025 accounts, Section 444 exemption (no income statement filed)" or whatever the actual reason is if it's something else. This is a structural fact about the filing, not a research gap, and the cell should say so on its own — don't make Daniel cross-reference Notes to find out why a number is missing. |
| N | Profit Before Tax | Same sourcing rule as Revenue, including writing the reason directly in the cell (not just Notes) whenever the figure can't be found. |
| O | Person of Significant Control (Companies House link) | `.../company/{number}/persons-with-significant-control` |
| P | Person of Significant Control Name | Companies House PSC register — **must resolve to a natural person, not a company.** See "Chasing the PSC to a real person" below when the register shows a company instead. |
| Q | PSC LinkedIn | **Search technique (Daniel, 2026-09-17): on LinkedIn, search the PSC's name together with the company name** (e.g. "Jane Example Sample Power Solutions") — this is the reliable way to land on the right profile rather than guessing from a bare name search. Verify the result is actually the same person (right company, plausible role) before recording it. |
| R | PSC Email | Pattern-matched then verified where possible. **Never a generic role address** (info@, hello@, sales@, contact@, etc.) — see "Contact rules" below. Fine to leave blank if not found — lower priority than PSC LinkedIn. |
| S | PSC Phone | Pattern-matched then verified where possible. Fine to leave blank if not found — lower priority than PSC LinkedIn. |
| T | CEO / MD Name | LinkedIn/website — tracked separately from the PSC, since the CEO/MD and the registered PSC are very often different people. UK small/private companies often use "Managing Director," "Director," or "General Manager" rather than "CEO" — treat these as the same target role: whoever is actually running the business day to day. |
| U | CEO / MD LinkedIn | **Essential, not optional (Daniel, 2026-09-17) — this is the single most important contact field in the row.** Same search technique as PSC LinkedIn (name + company name). Don't leave this blank without having actually tried the search. |
| V | CEO / MD Email | Same treatment as PSC Email, **including the no-generic-address rule.** Fine to leave blank if not found — lower priority than CEO/MD LinkedIn. |
| W | CEO / MD Phone | Same treatment as PSC Phone. Fine to leave blank if not found — lower priority than CEO/MD LinkedIn. |
| X | Key OEM Partnerships | **Pair each OEM to the specific equipment category it applies to, for every category the company offers.** Format: `Category - OEM1, OEM2; Category2 - OEM3`. E.g. a company reselling Cummins and Perkins generators and Crestchic load banks gets `Generator - Cummins, Perkins; Load bank - Crestchic` — not a single flat list of OEM names with no indication of which product line each belongs to. |
| Y | Type-Spec / Resale-Rental-Service | **List each of Resale / Rental / Service that genuinely applies, spelled out individually.** Never write "all" or "both" — if a company does resale and service but not rental, the cell reads `Resale, Service`. |
| Z | Services Offered | Use the real market vocabulary from the "Services Vocabulary & Search Keywords" doc's Section 2 (see `references/live-resources.md` for the doc ID) — installation, maintenance, repairs, load bank testing, etc. This is a living list; if you notice a genuinely recurring service description that isn't in it yet, add it there and flag the addition. |
| AA | Primary Sectors | End-customer sectors served, e.g. data centres, healthcare, construction. |
| AB | Sources | One citation per fact, not one blanket source for the whole row. |
| AC | Screening Verdict | In-scope / Out-of-scope (with reason) / Needs more info / Out of range — informational contact. Never left blank. |
| AD | Notes | Free text — acquisition history, anything else that doesn't fit elsewhere. |

## The sizing heuristic

Revenue is rarely disclosed for small private companies, so headcount is the triage proxy. As of 2026-09-17, collect three figures — Company Size band (I), Associated Members on LinkedIn (J), and Employees - Companies House (K) — but **only two of them decide the working headcount: Associated Members and Companies House, whichever is larger** (Daniel, 2026-09-17, correcting an earlier draft of this rule that wrongly included the LinkedIn band as a third contender). The Company Size band still gets recorded in column I for reference/context, but it's a coarse LinkedIn-assigned range, not a real count — it never wins the comparison.

**Take the larger of Associated Members (J) and Companies House employees (K), and specifically don't second-guess a larger Companies House number** (Daniel, 2026-09-17). The reasoning: some of these companies use a material number of contractors, and it's genuinely unclear from LinkedIn alone whether contractors are counted as staff. When the Companies House "average employees" figure comes out *larger* than Associated Members, that's evidence Companies House is capturing a fuller picture (contractors included) rather than a discrepancy to explain away. This isn't a one-directional rule, though — Companies House isn't always the larger number. On the first real batch this was tested against: Thermaright's LinkedIn Associated Members (9) was larger than its Companies House figure (3); Ability Power's Companies House figure (15) was more than 5x its LinkedIn Associated Members (3). Take whichever of the two is larger every time, and note in Sources/Notes which figure you used and why the other was lower — don't quietly drop the smaller reading, it's still informative (e.g. a small LinkedIn presence relative to a larger Companies House headcount can itself be worth a one-line note).

Companies with a working headcount of **30–100 staff are in scope by default** — a wide, inclusive band, not a narrow target. Only mark one out-of-scope within that band if you know otherwise with real certainty. Below ~30 is usually too small; above ~100 needs more scrutiny before ruling in or out — check Ultimate Owner (column L) before ruling out on headcount alone, since a large group-level figure can mask a right-sized subsidiary or division.

**The tie-break below is a genuine last resort, not a shortcut** — try to get real numbers for both Associated Members and Companies House employees first; Companies House especially is usually obtainable even when LinkedIn is ambiguous (it's a filed legal document, not a third-party platform). Only when both of those straddle the 30 or 100 boundary and neither resolves it — **default to In-scope rather than "Needs more info"** (Daniel, 2026-09-17). This is the same inclusive instinct as the wide 30-100 band itself: a company worth a second look shouldn't get stuck in limbo just because the available signals are coarser than our cutoff. If a more specific disqualifier turns up alongside the ambiguous headcount (PE-owned, wrong sub-sector, etc.), that still governs the verdict as normal — this rule only breaks the tie when headcount is the *only* open question.

## Chasing the PSC to a real person

Companies House often shows another company as the PSC rather than an individual — that's a pointer to keep following, not the answer. When PSC comes back as a company:

1. Note the intermediate entity in Ultimate Owner (column L) — it's real information, don't discard it.
2. Look up that company's own PSC register on Companies House.
3. Repeat until you reach one or more **named individuals**. Group structures sometimes go several layers deep — keep going until there's nowhere further to go, not just one hop.
4. If it's more than one layer, record the full chain (e.g. "PSC: R & B Switchgear Holdings Limited → ultimate PSC: Max Elliott Beswick") in Ultimate Owner or Notes, so the reasoning is traceable.

Stopping at the first company name found is the same category of error as leaving a fact silently blank — it looks like a finding but isn't one.

**The chain can legitimately end somewhere other than a named individual** (Daniel, 2026-09-17): if it terminates at a publicly-traded parent (e.g. a company whose PSC is itself owned by a listed group like ABB Ltd) or a private equity fund (e.g. KKR & Co. Inc.), that's a valid stopping point — there's no further natural person to find by design, since ownership sits with shareholders rather than a controlling individual. Record it as such (e.g. "PSC: Dawsongroup UK Limited → Dawsongroup Limited → KKR & Co. Inc. (NYSE: KKR, acquired Jan 2025)") rather than treating the absence of a named person as an unfinished chase. PE/public ownership is also, separately, a strong Out-of-scope signal in its own right (see "What qualified means" below) — the two facts (no natural person exists, and this disqualifies the company) usually arrive together. A large, publicly-traded multinational (e.g. ABB) is a flat Out-of-scope on its own scale alone — don't treat sheer size as grounds for an "informational contact" exception unless Daniel has specifically said so for that company; size by itself just means the company is too big, not that it's worth a courtesy conversation.

## Financial performance signals (added 2026-09-18)

Headcount was the only screening signal until now. Revenue and Profit Before Tax (columns M/N) add a second, independent path — but Daniel's own caveat going in: these two figures aren't always trustworthy on their own, particularly for companies with group structures or in a fast-growth phase, so apply the same "check the fuller picture before trusting one number" instinct already used for headcount.

**Profit Before Tax is an independent route to Qualified Leads, separate from headcount:**
- **PBT above £1m and up to £10m** → this alone is enough to copy the company into Qualified Leads, *even if headcount looked Out-of-scope or ambiguous.* Record in Notes which path qualified it (e.g. "Qualified via PBT (£2.3m) — headcount alone would have read Out-of-scope/borderline").
- **PBT above £10m** → too large for this path. This doesn't by itself force an Out-of-scope verdict (headcount could still independently qualify a company with high PBT), but it means PBT isn't the reason to qualify it.
- **PBT is in the £1m-£10m qualifying range, but the company is PE-owned or part of a larger group** → **don't auto-qualify and don't auto-disqualify — flag it in Notes for Daniel to judge himself** (Daniel, 2026-09-18: "it depends on who the owner is"). Record the PBT figure and the ownership context together, e.g. "PBT flag: £3.1m PBT, but owned by [PE fund / Group Name] — flagging for review rather than auto-qualifying, ownership context matters here." Set Screening Verdict to "Needs more info" in this case rather than silently picking a side.

**Revenue between £10m and £50m gets flagged for Daniel's own review, not an automatic verdict either way** — add a clear Notes callout (e.g. "Revenue flag: £24m — outside the usual profile, flagging for Daniel to consider fit") and leave the Screening Verdict as whatever the headcount/PBT logic already produced. Don't copy to Qualified Leads on this trigger alone — Daniel decides after seeing the flag, this isn't a path into Qualified Leads by itself the way PBT is.

## Contact rules

A blank contact cell is honest; a generic one looks like a finding but isn't. For PSC Email (R) and CEO/MD Email (V):

- Never a generic role address — info@, hello@, sales@, contact@, admin@, or similar.
- If the named person's real personal/direct email can't be found, **leave the cell blank.** Don't fill it with a generic address just to avoid an empty cell.
- Email verification/bounce-testing isn't something this skill does — record an email as found-but-unverified rather than trying to self-verify.

The same "leave it blank" principle applies to LinkedIn profiles too, not just emails: if a genuinely thorough search for a named PSC or CEO/MD's LinkedIn profile comes up empty, that's a legitimate blank, not a failure — record what you tried in Sources/Notes so it's clear the gap was checked, not skipped.

## What "qualified" means

A company is ready to copy into the Qualified Leads tab via **either** of two independent paths (Daniel, 2026-09-18: PBT is a second route in, not conditional on headcount):

1. **Headcount path**: verified headcount (the larger of Associated Members and Companies House employees, from the sizing heuristic above) in the 30-100 range, ownership (Companies House PSC, chased to a real person) independently confirmed, and no obvious disqualifier (PE-owned, part of a large group, wrong sub-sector, recently acquired).
2. **Financial performance path**: PBT above £1m and up to £10m, per the "Financial performance signals" section above — this qualifies a company even if headcount alone wouldn't have, *unless* the PE/large-group flag in that section applies, in which case it goes to Daniel for review instead of an automatic qualify.

Either path is sufficient on its own. When you can't find or confirm something, leave it blank — don't guess, and don't quietly upgrade a guess into a stated fact.
