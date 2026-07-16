# Polymarket Annotation Data

Dataset of AI-generated timeline annotations from Polymarket, collected and analyzed by the Tow Center for Digital Journalism at Columbia University.

## Background

Some Polymarket markets contain a section called "Market Context" that displays a price chart with a timeline of annotated events. These arebrief AI-generated blurbs that provide context for price movements. Each annotation includes a headline, a one-paragraph summary, and a list of cited news sources with outlet names and URLs.

These annotations are not written by humans. Polymarket's own API identifies each one with `"source": "linkup"`, attributing them to [Linkup](https://www.linkup.so), a third-party AI search and summarization service. 

Linkup operates in `sourcedAnswer` mode: given a query, it retrieves web sources and generates a summary. The result — headline, summary, and citations — is stored by Polymarket and displayed as context on each market page.

## What the data shows

Polymarket launched the "market context" timlines on **April 29, 2026**, although some of the items were older than that, dating back to 2024. We collected these timelines from May 21 to July 12, 2026 and analyzed the TK citations across TK timelines. 

We've categorized the urls into the following groups: 

| Issue type | Count |
|---|---|
| Non-news sources cited as journalism (Wikipedia, social media, odds pages) | 391 |
| Wrong outlet — URL does not match the named source | 201 |
| Hallucinated AP News URLs — return HTTP 404, structurally not real AP articles | 157 |
| Known AI-content or fringe domains | 24 |
| Wire copy misattributed to the original wire service | 13 |
| example.com placeholder URLs | 7 |
| **Total** | **793** |

Additionally, Polymarket cited its own platform pages (polymarket.com, polymarketanalytics.com, myriad.markets) **73 times**.

---

## How we know the citations are inaccurate

**AP News URLs:** Real AP article URLs always contain a 20+ character lowercase hexadecimal hash in the slug (e.g., `apnews.com/article/russia-ukraine-war-ab3f91c72e84d1a0...`). Hallucinated AP URLs use human-readable slugs the AI generated. All 157 flagged AP URLs return HTTP 404.

**Wrong outlet:** The outlet name in the annotation does not match the domain of the cited URL. For example, a citation labeled "Reuters" linking to a local TV station's website.

**Known bad domains:** A list of domains verified to publish AI-generated or low-quality content, cross-referenced against the citation data.

---

### Data collection period

Data was collected automatically via GitHub Actions on a 30-minute to 6-hour schedule.

**Collection period:** May 21 – July 12, 2026  
**Annotation timestamp range:** January 2023 – July 12, 2026  
**Markets covered:** 78  
**Total annotations:** 8,687  

---

## Files

### `data/annotations.csv`

All 8,687 annotations through July 12, 2026. One row per annotation.

| Column | Description |
|---|---|
| `event_slug` | Polymarket market identifier |
| `market_title` | Market question |
| `category` | Market category (politics, economy, etc.) |
| `timestamp` | Annotation timestamp (UTC, as labeled by Polymarket) |
| `outcome` | Outcome label associated with the price move |
| `time_range` | Time window the annotation covers |
| `price_before` | Yes price before the move (0–100) |
| `price_after` | Yes price after the move (0–100) |
| `price_change` | Change in percentage points |
| `title` | AI-generated headline |
| `summary` | AI-generated summary paragraph |
| `ai_source` | Attribution field from Polymarket API (`linkup` on 99.8%) |
| `sources_json` | JSON array of `{name, url}` citation objects |
| `first_seen` | Date the scraper first collected this annotation |

---

### `data/citation_issues.csv`

793 flagged citations. One row per citation issue.

| Column | Description |
|---|---|
| `issue_type` | Classification: `hallucinated_ap_url`, `wrong_outlet`, `non_news_source`, `known_bad_domain`, `syndicator`, `example_com` |
| `claimed_source` | Outlet name as displayed in annotation |
| `actual_domain` | Domain of the cited URL |
| `url` | Full URL |
| `market_slug` | Market this annotation belongs to |
| `market_title` | Market question |
| `annotation_title` | Annotation headline |
| `annotation_ts` | Annotation timestamp |
| `price_before` | Yes price before move |
| `price_after` | Yes price after move |
| `note` | Detail on the specific issue |

---

### `data/market_citations.csv`

Per-market, per-outlet citation summary. One row per market + outlet combination.

| Column | Description |
|---|---|
| `market_slug` | Market identifier |
| `market_title` | Market question |
| `category` | Market category |
| `outlet_name` | Outlet name as cited in annotations |
| `citations` | Number of citations to this outlet in this market |
| `dead_urls` | Citations returning HTTP 404 |
| `known_citation_issues` | Count of flagged citations for this outlet in this market |
| `market_total_citations` | Total citations across all annotations in this market |
| `market_total_dead` | Total dead URLs in this market |
| `market_total_issues` | Total flagged citations in this market |
| `market_dead_pct` | Percentage of citations that are dead |

---

### `data/url_status.csv`

HTTP status of every unique URL cited across all annotations. One row per URL.

| Column | Description |
|---|---|
| `url` | Full URL |
| `domain` | Domain |
| `outlet_names` | Outlet names used for this URL across annotations |
| `markets` | Markets where this URL appears |
| `http_status` | HTTP response code, or `CONNECTION_ERROR` / `TIMEOUT` / `SSL_ERROR` |
| `known_issue` | Issue type if flagged |

---

## Notes on methodology

- Citation classification is pattern-based and does not require HTTP requests, except for the URL status check which was run separately.
- The AP News hallucination detection relies on URL structure, not content: real AP URLs contain a hex hash; the flagged ones do not, and all return HTTP 404.
- Wrong-outlet detection uses a lookup table of known outlet names and their expected domains. It will miss misattributions for outlets not in the table.
- The dataset covers markets tracked during the collection period. Polymarket hosts thousands of markets; this dataset represents those with sufficient volume to appear in the top results by category.
- All annotation timestamps in this dataset reflect the labels Polymarket assigns, not when the text was written. Annotations predating April 29, 2026 were retroactively generated on or after that date.
- Polymarket's Terms of Use state the platform may "delete or otherwise materially modify content and information" at any time without notice.

---

## About

Collected and analyzed by **Tory Lysik**, Tow Center for Digital Journalism, Columbia University.
