---
name: search-vocabulary-capture
description: Logs new market vocabulary (product names, service-list items, services-offered wording, possible new scope categories) found on company websites during Aurias 2 enrichment or discovery, and turns phrases seen at 3+ companies into Scope & Search Vocabulary doc updates — Section 2 descriptions and Services List words added directly (with a research task for Daniel), Product List and scope items proposed to Daniel. Use whenever an agent reads a company website and meets a term not already in the Scope & Search Vocabulary doc, or to process the Vocabulary Log.
---

# Search vocabulary capture — Aurias 2

The market's own words find more companies. Every agent that reads a company website logs the words it meets that aren't in the **Scope & Search Vocabulary** doc yet. Repeats build confidence: once a phrase has been seen at **3 different companies**, it acts (Daniel, 2026-09-19).

## Kinds

| Kind | Where it would go | At 3 companies |
|---|---|---|
| `description` | Section 2, services-offered wording (e.g. "hybrid power hire") | Added to the doc automatically |
| `product` | Section 1 Product List (hardware names — feeds search terms) | Proposed to Daniel |
| `service` | Section 1 Services List (service words — feeds search terms) | Added automatically, and a research task goes on Daniel's to-do list |
| `scope` | A category not in Section 0 at all | Proposed to Daniel |

Product List items are proposed, not added, because a new product widens the hunt. New service words go straight in, but never silently: Daniel gets a task to research the service and its market (Daniel, 2026-09-19).

## How to log

Log only what you actually read on the company's own site, with the page URL. Write a JSON list and run from `.claude/skills/generator-ups-data-enrichment/scripts`:

```
PYTHONIOENCODING=utf-8 python vocab_capture.py log sightings.json
# [{"phrase": "...", "kind": "description|product|service|scope", "company": "...", "ch_number": "...", "source_url": "...", "logged_by": "sourcing batch 57"}]
```

Phrases already in the doc are skipped automatically. Log the phrase as the company writes it; don't invent a tidier version.

## Processing

`python vocab_capture.py process` runs daily at 07:00 (scheduled task `regen-search-terms-daily`, just before the search terms regenerate). It:
- adds Section 2 descriptions that reached 3 companies to the "Added from company websites" line;
- adds Services List words that reached 3 companies to the table and prints a `RESEARCH TASK:` line, which the daily task turns into a to-do for Daniel on the dashboard;
- puts product and scope items that reached 3 companies on the **Tally** tab of the Vocabulary Log as **Pending**;
- applies Daniel's decisions: **Approved** product items are added to the Product List (search terms regenerate straight after); **Approved** scope items are reported for Athena to add to Section 0 by hand; **Rejected** items are never proposed again.

## Where things are

- Vocabulary Log — Aurias 2 (sheet): `1y1iOwjN1BHrNM0GKWZS68WuXZRIPAiHvy-jm-iZcq5A` — tabs Sightings, Tally.
- Scope & Search Vocabulary (doc): `1VcU78QCMR0Az9N-l-mVidFe5Qsu6ZvoD-xB6RzD9ScQ`.

## Never

Edit Section 0 or either Section 1 table directly — only the script changes them, under the rules above. Log a phrase from anything but the company's own website or filed documents.
