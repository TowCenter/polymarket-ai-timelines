# Polymarket Annotation Data

Dataset of AI-generated timeline annotations from Polymarket, collected and analyzed by the Tow Center for Digital Journalism at Columbia University.

## Background

Some Polymarket markets contain a section called "Market Context" that displays a price chart with a timeline of annotated events. These are brief AI-generated blurbs that provide context for price movements. Each annotation includes a headline, a one-paragraph summary, and a list of cited news sources with outlet names and URLs.

These annotations are not written by humans. Polymarket's own API identifies each one with `"source": "linkup"`, attributing them to [Linkup](https://www.linkup.so), a third-party AI search and summarization service.

Linkup operates in `sourcedAnswer` mode: given a query, it retrieves web sources and generates a summary. The result — headline, summary, and citations — is stored by Polymarket and displayed as context on each market page.

## Definitions

**Annotation** — A single AI-generated entry on a market's timeline. Each annotation has a headline, a summary paragraph, and a list of sources. One market can have hundreds of annotations.

**Citation** — A single source linked within an annotation, consisting of an outlet name and a URL. One annotation typically has multiple citations.

## Collection

**Step 1** — We used Polymarket's public Gamma API to enumerate all markets on the platform (2,098 total, active and closed), sorted by trading volume. We checked each for AI-generated annotation timelines and found 62 with them.

**Step 2** — We supplemented the sweep with 44 additional markets captured during our reporting window (May 12–July 15, 2026) that had since resolved and been removed from the platform. Combined dataset: 107 markets.

**Step 3** — We sent HTTP requests to all 7,830 unique cited URLs and recorded their response codes.

**Step 4** — We categorized each citation using a taxonomy of 1,513 domains.

**Step 5** — We exported the final dataset.

**107 markets · 12,890 annotations · 13,595 citations · 1,692 flagged**

## What the data shows

| Issue type | Count |
|---|---|
| Dead links — URL returns HTTP 404 or DNS failure | 866 |
| Propaganda — link goes to a known propaganda outlet | 359 |
| Pink slime — link goes to a known content farm | 252 |
| Wrong outlet — URL does not match the named source | 215 |
| **Total flagged** | **1,692** |

Issues were found in 88 of 107 markets.

## How we know the citations are flagged

**Dead links:** We sent HTTP requests to all 7,830 unique URLs. Citations returning HTTP 404 or a DNS failure are flagged as dead links.

**Wrong outlet:** The outlet name in the annotation does not match the domain of the cited URL — for example, a citation labeled "Reuters" linking to a local radio station's website. Detection uses a lookup table of known outlet names and their expected domains. Also flags AP News URLs that lack the hexadecimal hash present in all real AP article URLs (e.g., `apnews.com/article/russia-ukraine-ab3f91c72e84d1a0...`); hallucinated AP URLs use human-readable slugs and return HTTP 404.

**Propaganda / pink slime:** Flagged against a taxonomy of 1,513 classified domains. Propaganda includes outlets such as RT, TASS, and the news-pravda.com network. Pink slime includes known AI-generated content farms.

## Files

### `data/annotations.csv` — one row per annotation

| Column | Description |
|---|---|
| `market_slug` | Polymarket market identifier |
| `market_title` | Market question |
| `timestamp` | Annotation timestamp (UTC, as labeled by Polymarket) |
| `outcome` | Outcome label associated with the price move |
| `title` | AI-generated headline |
| `summary` | AI-generated summary paragraph |
| `price_before` | Market price before the event (0–100) |
| `price_after` | Market price after the event (0–100) |
| `price_change` | Change in percentage points |
| `sources` | JSON array of `{name, url}` citation objects |

### `data/flagged_citations.csv` — one row per flagged citation

| Column | Description |
|---|---|
| `market_slug` | Market identifier |
| `market_title` | Market question |
| `annotation_timestamp` | Timestamp of the annotation |
| `annotation_title` | AI-generated headline |
| `claimed_source` | Outlet name as cited in the annotation |
| `url` | URL cited |
| `actual_domain` | Domain the URL resolves to |
| `issue_type` | `dead link` · `wrong outlet` · `propaganda` · `pink slime` |
| `http_status` | HTTP response code |

## Notes on methodology

- The AP News hallucination detection relies on URL structure: real AP URLs contain a 20+ character hexadecimal hash; flagged ones do not, and all return HTTP 404.
- Wrong-outlet detection uses a lookup table of known outlet names and their expected domains. It will miss misattributions for outlets not in the table.
- All annotation timestamps reflect the labels Polymarket assigns, not when the text was written. Annotations predating Polymarket's feature launch were retroactively generated.
- The dataset covers 107 markets identified during the collection period (May 12–July 21, 2026). Polymarket hosts thousands of markets; this dataset represents those confirmed to have Linkup annotation timelines.
- Polymarket's Terms of Use state the platform may "delete or otherwise materially modify content and information" at any time without notice.

## About

Collected and analyzed by **Tory Lysik**, Tow Center for Digital Journalism, Columbia University.
