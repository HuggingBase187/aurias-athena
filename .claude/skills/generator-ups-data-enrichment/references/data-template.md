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
| H | Equipment Category | Every in-scope hardware category the company actually offers, from Section 0 of the "Scope & Search Vocabulary" doc — list them all, not just one. |
| I | Company Size on LinkedIn | LinkedIn's own banded size, e.g. "51-200 employees". |
| J | Associated Members on LinkedIn | LinkedIn's member count (the "X associated members" line on the company page) — a number, not a band. **Only looked up when K is missing or once the company has passed every other check** (see "Reading headcount"). Batch agents leave it blank; Athena fills it. |
| K | Employees - Companies House | The "average number of employees" note in the latest filed accounts (search the PDF for "average number of employees"). Often disclosed even when PBT isn't. **First headcount source** — see "Reading headcount". **Label trap:** in a note like "11 (2025 - 10)", the first number belongs to the period the accounts cover; check the accounts' own period, not the phrasing. |
| L | Ultimate Owner | Companies House / press — the owning entity or family, distinct from the named PSC individual. |
| M | Revenue | **Companies House filed accounts or a press release/investor-relations release only** — never an estimate, LinkedIn-derived guess, or other third-party figure. **Never leave this cell truly empty (Daniel, 2026-09-18).** If the figure genuinely can't be found, write the reason directly *in the cell itself* — e.g. "Not disclosed - micro-entity accounts (FRS 105), no income statement filed" or "Not disclosed - FY2025 accounts, Section 444 exemption (no income statement filed)" or whatever the actual reason is if it's something else. This is a structural fact about the filing, not a research gap, and the cell should say so on its own — don't make Daniel cross-reference Notes to find out why a number is missing. **Format (Daniel, 2026-09-18): `£X,XXX,XXX` — £ symbol, comma-grouped thousands, no decimals, never the text "GBP" and never a bare unformatted number.** Applies to every figure in the cell, including comparator years (e.g. "FY2024: £2,470,951", not "FY2024: 2470951"). A loss is `-£X,XXX,XXX`. |
| N | Profit Before Tax | Same sourcing rule as Revenue, including writing the reason directly in the cell (not just Notes) whenever the figure can't be found, and the same `£X,XXX,XXX` formatting rule above. |

**The "never truly empty" rule for M/N applies to confirmed-hallucination rows too, not just real-but-thin ones — caught by verification, 2026-09-18.** Three hallucination rows in one batch (Kenson Network Services, Kent Generators, Kingfisher Power) left M/N genuinely blank, while a hallucination row in a different batch the same session (Knight Power) got it right with "Not applicable - suspected hallucinated/fake entry, no operating business identified" — so this isn't an unclear rule, just an easy one to drop specifically when a row is about to be moved off Market Map entirely and feels like it's past mattering. It still needs the reason string, on both the Market Map verdict and the Suspected Hallucinations copy.

**The "never truly empty" rule for M/N applies especially hard to thin rows — caught by verification, 2026-09-18.** Batch 42 left Revenue and PBT genuinely blank on the two rows that had the least other data to work with (an unidentified entity, a dissolved company) — every other row in the same batch got the reason string right. The pattern: when a row is already thin, it's easy to let M/N go blank too, as if there's nothing left to say — but "no entity to pull accounts from" and "no accounts exist because it's dissolved" are exactly the kind of reasons this rule asks for. A thin row still gets a reason string in M/N, not a shrug.

**Cross-reference every secondary-source figure/fact against the specific Companies House number cited in the row — caught by verification, 2026-09-18.** Batch 39 scored below Daniel's 95% floor on exactly this pattern, twice in the same batch: Hendy Power's Revenue/PBT were taken from a press article's headline figures, but the article's "£1.01bn turnover" turned out to be only the Vehicle Sales line item (not total turnover) and its "£18m loss" belonged to a different legal entity in the group (the ultimate parent, not the CH number actually cited in the row) — and separately, Himoinsa UK's Head Office Address and Company LinkedIn were both taken from a cached/global source rather than the live UK-subsidiary-specific page, and both turned out wrong. **The fix: once you have a figure or fact from a press release, a group-level number, or any source not itself scoped to the exact CH number/entity in the row, go confirm it directly against that entity's own live Companies House page or its own filed accounts before writing it down.** A press report or brand page is a fine lead to follow, never a fine thing to cite directly without that last confirmation step.
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
| Z | Services Offered | Use the real market vocabulary from the "Scope & Search Vocabulary" doc's Section 2 (see `references/live-resources.md` for the doc ID) — installation, maintenance, repairs, load bank testing, etc. This is a living list; if you notice a genuinely recurring service description that isn't in it yet, add it there and flag the addition. |
| AA | Primary Sectors | End-customer sectors served, e.g. data centres, healthcare, construction. |
| AB | Screening Verdict | In-scope / Out-of-scope (with reason) / Needs more info / Out of range — informational contact. Never blank. **Every "Needs more info" row is copied to Flagged to You**, whatever the reason — it means Daniel's eyes are needed. |
| AC | Notes | Free text — acquisition history, anything else that doesn't fit elsewhere. |
| AD | Accounts Next Due - Companies House | From the Companies House overview page, captured whenever you pull it: the **next** accounts' period and due date ("Next accounts made up to Y, due by Z") — never the last-filed period. Fill it for every company; the monthly sweep uses it to decide who's due a re-check. |
| AE | Sources | One citation per fact, not one blanket source for the whole row. **Moved here from AB on 2026-09-18 (Daniel moved it manually) — it's now the last column, not the fourth-from-last.** |
| AF | Discovery Method | **Added 2026-09-18.** Which of the seven list-building methodologies found this company: OEM dealer/partner directory · Trade association directory · Google / Google Maps search · LinkedIn search / People Also Viewed · Trade press / exhibitor list · Lookalikes search · Companies House name search (dropdown on the sheet; the seventh added 2026-09-18). Written once, at promotion from the Discovery Staging sheet — enrichment never edits it. All rows that pre-date the column were tagged "Legacy list (Gemini)" on 2026-09-18 (Daniel confirmed every pre-existing row came from the Gemini-built list) — Market Map, Qualified Leads, Flagged to You and Suspected Hallucinations. Never back-fill any other method by guesswork. |

## Columns I and J hold a number and nothing else (added 2026-09-18, narrowed same day)

**Daniel's direct feedback: "I just want the data. For example '2-10 employees' in I and 9 in J. I don't need any other commentary."** Company Size on LinkedIn (I) and Associated Members on LinkedIn (J) had been accumulating inline commentary — how the figure was confirmed, the date it was checked, a confidence caveat, a note that it's below/above another column's figure. That commentary crowds out the one thing these cells exist to hold, and makes the sheet harder to read and to sort/filter on as a plain number.

**This applies to I and J only — Employees - Companies House (K) is explicitly excluded.** An earlier draft of this rule (2026-09-18) wrongly swept K in too; Daniel corrected that directly: "Do not make any changes to how you are enriching the 'employees - companies house' cells." Enrich and format K exactly as its own column description above already says, unaffected by this section.

**I and J hold the band or figure alone** — `2-10 employees`, `9` — nothing else. Before/after example:
- Before: `72 (LinkedIn "employees on LinkedIn" figure via search snippet - could not confirm via logged-in view this session, low confidence, notably below the CH figure)`
- After: `72` in the cell, with `Associated Members (72, via search snippet, unconfirmed via logged-in view) notably below the Companies House figure` moved to Notes (AC) if that comparison matters to the verdict, or into Sources (AE) if it's purely a citation.

**Where does the commentary actually go, then — don't just delete it if it's load-bearing:**
- *How/when it was confirmed* (WebFetch, logged-in LinkedIn view, a search snippet, the date checked) — that's a citation, it belongs in Sources (AE), one line per fact, same as any other sourced field.
- *A genuine confidence caveat or a discrepancy between two figures that actually affects the verdict* (e.g. one source reads well under the 30-employee floor and another reads well over it) — that's analysis, it belongs in Notes (AC), not silently discarded and not left buried in the number cell where it won't surface when someone scans the column.
- Don't duplicate the same caveat in both Notes and Sources — pick whichever one it actually is (a citation vs. a judgment call) and put it there once.

This isn't a retroactive research requirement — it's about where a fact already gathered gets written down, not about gathering anything new.

## Screening rules (agreed with Daniel, 2026-09-18)

**Scope** is defined in one place: Section 0 of the "Scope & Search Vocabulary" doc (ID in `references/live-resources.md`). Read it; don't keep a copy here.

**Order of checks** — cheapest and most decisive first:
1. **Quality gate** (`scripts/quality_gate.py`): real Companies House company, active, not micro-entity/dormant, not a duplicate.
2. **Financials** from the latest filed accounts: PBT and Revenue (columns M/N).
3. **Ownership**: PSC chased to a named person (see "Chasing the PSC" below).
4. **Headcount** — only if no PBT is filed. Use the Companies House average-employees figure (K) first.
5. **LinkedIn** (I/J) — only if K is missing, or once the company has passed everything above. Batch agents leave I/J blank; Athena fills them.

**Size.** Financials decide first; headcount is only a proxy when PBT isn't filed. If both exist and disagree, PBT wins.
- Map **PBT £1m–£10m**; sweet spot **PBT £2–4m**. The £1m floor exists because filed accounts lag 12–15 months.
- **PBT above £10m** doesn't qualify on PBT.
- **Revenue £10m–£50m** → note it for Daniel. Not a verdict either way.
- **Headcount (no PBT filed): 30–100 → in scope.** Above ~100, check ownership before ruling out — a group figure can hide a right-sized subsidiary.
- **Near misses** (PBT £700k–£1m, headcount 20–29): routing is defined in the **Near Miss Rules** doc (ID in `references/live-resources.md`). Read it every time; don't rely on memory or a copy.
- **No PBT disclosed**: record Accounts Next Due (AD). The monthly sweep re-checks the row when new accounts are due.

**Ownership.**
- Target is **owner-operated**.
- **Majority PE-owned or part of a group, with qualifying PBT** → "Needs more info" + Flagged to You. Daniel decides — what matters is who is behind the holding company (a known family differs from institutional PE).
- **PE holds a minority stake** (PSC register shows the fund at 25–50%) → treat as owner-operated; note "minority PE — worth a conversation".
- **PE has held the business 3+ years** (PSC notification date) → note it: the fund may be open to selling.
- **Listed multinationals** → Out-of-scope.

**Where a company ends up.**
- **Qualified Leads** (copy the row): PBT £1m–£10m and owner-operated; or no PBT filed and headcount 30–100 with ownership confirmed; or a near miss routed there by the Near Miss Rules doc. No other disqualifier (wrong sub-sector, recently acquired, listed).
- **Flagged to You** (copy the row): majority PE/group with qualifying PBT; near misses routed there by the Near Miss Rules doc; Revenue £10m–£50m on a row that would otherwise be Out-of-scope.
- **Suspected Hallucinations**: see the section below.
- **Out-of-scope**: always with the reason. Never deleted.
- Every row gets a Screening Verdict: In-scope / Out-of-scope (reason) / Needs more info / Out of range — informational contact.

**Figures.** Only figures as filed (Companies House accounts, or a company press/IR release). No calculated or derived metrics. Blank beats a guess.

## Untraceable companies may be hallucinated, not just hard to find (added 2026-09-18)

Daniel: "the original list was compiled by Gemini, and it's highly likely that there are a number of fake companies/hallucinated data." If a genuine, careful search — company website, Companies House name search including close variants, LinkedIn, Google Maps — turns up nothing at all (no matching entity, no working domain, no web presence), don't keep burning time trying to force a match or assume it's just an obscure/small business that's hard to find online. It may simply not exist. In that case, set Screening Verdict to **"Out-of-scope - suspected hallucinated/fake entry (no Companies House match, no website, no web presence found — original list compiled by Gemini)"** and note what you actually checked, the same way "Blue Diamond Generators" and "Blackout Power" were handled on 2026-09-18. This isn't a license to search less carefully — a company that's just badly documented (dissolved, tiny, rebranded) still deserves the full chase — but once that chase is genuinely exhausted, "probably never existed" is a legitimate conclusion, not a research failure.

**Wayback Machine check — known false-negative, verified 2026-09-18: don't trust a bare "zero snapshots" claim from the Availability API alone.** Verification independently reproduced this twice in one batch: querying the Wayback Availability API (`archive.org/wayback/available`) *with* a timestamp parameter can wrongly report zero snapshots for a domain that genuinely has archived history — supplying no timestamp and pulling the full CDX index instead gets the real answer. This matters because "zero Wayback snapshots ever" is one of the four standard legs of the hallucination checklist above; a false negative there doesn't necessarily flip the verdict (a domain can have real snapshots that are *still* just parking-page placeholders, which is exactly as damning as no snapshots at all), but the checklist should record what the history actually shows, not a wrong tool result. Before writing "zero snapshots" as a fact, query the CDX index (`web.archive.org/cdx/search/cdx?url=DOMAIN&output=json`) directly rather than relying on the Availability API's single-timestamp response.

## Reading headcount

- **K (Companies House average employees)** comes first — it's in the filed accounts, usually a note near the front, and is often disclosed even when PBT isn't.
- **J (LinkedIn Associated Members)** only when K is missing, or once the company has passed every other check. LinkedIn undercounts trade and field-service businesses, so a low J never overrides K.
- When both exist, the working headcount is the larger of J and K. A larger K is meaningful (it can include contractors), not an anomaly.
- **I (LinkedIn size band)** is context only; it never decides anything.
- The age that matters is the accounts' **period-end date**, not the filing date.

## Chasing the PSC to a real person

Companies House often shows another company as the PSC rather than an individual — that's a pointer to keep following, not the answer. When PSC comes back as a company:

1. Note the intermediate entity in Ultimate Owner (column L) — it's real information, don't discard it.
2. Look up that company's own PSC register on Companies House.
3. Repeat until you reach one or more **named individuals**. Group structures sometimes go several layers deep — keep going until there's nowhere further to go, not just one hop.
4. If it's more than one layer, record the full chain (e.g. "PSC: R & B Switchgear Holdings Limited → ultimate PSC: Max Elliott Beswick") in Ultimate Owner or Notes, so the reasoning is traceable.

Stopping at the first company name found is the same category of error as leaving a fact silently blank — it looks like a finding but isn't one.

**Don't conflate the PSC chain with a statutory "ultimate parent undertaking" disclosure — they're two different things (learned from ADE Power Limited, 2026-09-18).** The PSC register (Persons with Significant Control) is a specific legal requirement to identify natural persons with real control, and UK company law makes it resolve to a person directly even when a foreign holding company sits above it in the ownership structure — so a UK subsidiary's PSC register can name a natural person immediately, in the same filing, without mentioning an overseas parent at all. Separately, a company's own filed **statutory accounts** often carry a note titled something like "Ultimate parent undertaking and controlling party," which discloses who legally owns the shares / consolidates the group accounts — this can be a company (including one abroad) even though the PSC register elsewhere correctly resolves to a named person. Both facts can be true and non-contradictory at once. When you write the Ultimate Owner cell, keep these visibly separate: state the actual PSC chain first (verified via the PSC register, ending at a named person or documented terminus), then add the parent-undertaking disclosure as separate context if it adds something — don't write it as if it were one continuous chain the PSC had to pass through, since that reads as though the person is harder to reach than they actually are.

**The chain can legitimately end somewhere other than a named individual** (Daniel, 2026-09-17): if it terminates at a publicly-traded parent (e.g. a company whose PSC is itself owned by a listed group like ABB Ltd) or a private equity fund (e.g. KKR & Co. Inc.), that's a valid stopping point — there's no further natural person to find by design, since ownership sits with shareholders rather than a controlling individual. Record it as such (e.g. "PSC: Dawsongroup UK Limited → Dawsongroup Limited → KKR & Co. Inc. (NYSE: KKR, acquired Jan 2025)") rather than treating the absence of a named person as an unfinished chase. PE/public ownership is also, separately, a strong Out-of-scope signal in its own right (see "What qualified means" below) — the two facts (no natural person exists, and this disqualifies the company) usually arrive together. A large, publicly-traded multinational (e.g. ABB) is a flat Out-of-scope on its own scale alone — don't treat sheer size as grounds for an "informational contact" exception unless Daniel has specifically said so for that company; size by itself just means the company is too big, not that it's worth a courtesy conversation.

**"Terminates at a public/PE parent" is a conclusion to verify at each hop, not a pattern-match to stop on early — caught 3 times by verification (IPU Group, John F Hunt Power, Legrand Electric Ltd, all 2026-09-18).** All three misses had the same shape: the chain looked done ("this is a big multinational, job finished") one hop before it actually was — an intermediate holding company's *own* PSC register was never pulled, so a real entity in the chain (a second holding company, a different family branch, a specific French/US parent one layer more precise than "the group") went unrecorded. The fix from the "Chasing the PSC to a real person" steps above already covers this — "keep going until there's nowhere further to go, not just one hop" — but recognizing a familiar big-company name is exactly the moment that discipline tends to lapse. Pull the immediate PSC's own PSC page even when you're fairly sure you already know how the story ends.

## Contact rules

A blank contact cell is honest; a generic one looks like a finding but isn't. For PSC Email (R) and CEO/MD Email (V):

- Never a generic role address — info@, hello@, sales@, contact@, admin@, or similar.
- If the named person's real personal/direct email can't be found, **leave the cell blank.** Don't fill it with a generic address just to avoid an empty cell.
- Email verification/bounce-testing isn't something this skill does — record an email as found-but-unverified rather than trying to self-verify.

The same "leave it blank" principle applies to LinkedIn profiles too, not just emails: if a genuinely thorough search for a named PSC or CEO/MD's LinkedIn profile comes up empty, that's a legitimate blank, not a failure — record what you tried in Sources/Notes so it's clear the gap was checked, not skipped.
