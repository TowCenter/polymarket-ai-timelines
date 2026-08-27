# Polymarket Timelines

Dataset of AI-generated timeline annotations from Polymarket, collected and analyzed by the Tow Center for Digital Journalism at Columbia University.

## Background

Some Polymarket markets contain a section called "Market Context" that displays a price chart with a timeline of annotated events. These are brief AI-generated blurbs that provide context for price movements. Each annotation includes a title, a one-paragraph summary, and a list of cited news sources with outlet names and URLs.

## Collection

**Step 1** — On August 7, 2026, we used Polymarket's public Gamma API to enumerate all markets on the platform where over $1M in volume had been traded.

**Step 2** — We sent HTTP requests to all cited URLs and recorded their response codes.


## Files

### `citations.csv`

This file contains one row for every citation on a Polymarket "Market Context" timeline. Some entries in a timeline may have more than one citation. These entries will be repeated in the dataset, with one row for each citation.

| Column | Description |
|---|---|
| `market_slug` | Polymarket market identifier |
| `market_title` | Market question |
| `annotation_timestamp` | Annotation timestamp (UTC, as labeled by Polymarket) |
| `annotation_title` | AI-generated headline |
| `annotation_summary` | AI-generated summary paragraph |
| `ai_source` | Content of the `source` field of Polymarket timeline entry (usually `linkup`)|
| `claimed_source` | Name of sources that appears when hovering on a citation |
| `url` | URL cited when clicking on a citation |
| `actual_domain` | extracted from `url` |
| `http_status` | HTTP response code |
| `suspected_ap_hallucination` | TRUE the article is a citation of AP news that we suspect is hallucinated (methodology note below) |

## Notes on methodology

- The AP News hallucination detection relies on URL structure. We mark a citation as `suspected_ap_hallucination` only if:
    1. the `actual_domain` is apnews.com
    2. the `http_status` is 404
    3. the URL contains `/article/` but does not end in a 32-character hexadecimal hash (which valid AP News article URLs generally do).

## About

Collected and analyzed by **Tory Lysik** and **Dhrumil Mehta**, Tow Center for Digital Journalism, Columbia University.

Please direct questions or concerns to towcentercuj@gmail.com.
