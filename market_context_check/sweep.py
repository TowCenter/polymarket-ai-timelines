"""Sweep Polymarket for two "Market Context" signals:

  A) Grok single-paragraph summary via Gamma /events `eventMetadata.context_description`
  B) Linkup per-annotation timeline, detected by counting `"source":"linkup"`
     occurrences in the SSR-rendered event page HTML at polymarket.com/event/<slug>

See README.md in this folder for context and caveats.
"""
import re
import time
from pathlib import Path

import pandas as pd
import requests
import requests_cache

BASE = "https://gamma-api.polymarket.com/events"
PAGE = 100
OUT_DIR = Path(__file__).parent
HERE = OUT_DIR


def fetch_bucket(**filters):
    rows, offset = [], 0
    while True:
        params = {
            "limit": PAGE,
            "offset": offset,
            "order": "volume",
            "ascending": "false",
            **filters,
        }
        r = requests.get(BASE, params=params, timeout=60)
        if r.status_code == 422:
            print(f"  offset cap hit at {offset} for {filters}")
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < PAGE:
            break
        time.sleep(0.02)
    return rows


def context_fields(event):
    md = event.get("eventMetadata") or {}
    if not isinstance(md, dict):
        md = {}
    desc = md.get("context_description") or ""
    return {
        "slug": event.get("slug"),
        "title": event.get("title"),
        "id": event.get("id"),
        "volume": event.get("volume"),
        "closed": event.get("closed"),
        "archived": event.get("archived"),
        "has_context": bool(desc),
        "context_len": len(desc),
        "context_updated_at": md.get("context_updated_at"),
        "context_requires_regen": md.get("context_requires_regen"),
        "context_description": desc,
    }


# Annotation payloads are embedded in a JS string literal on the SSR page,
# so the JSON quotes are backslash-escaped. Match both raw and escaped.
LINKUP_MARKER = re.compile(r'\\?"source\\?"\s*:\s*\\?"linkup\\?"')
UA = {"User-Agent": "Mozilla/5.0 (compatible; polymarket-fact-check/1.0)"}

CACHE_PATH = Path(__file__).parent / "http_cache.sqlite"


def make_session():
    """Session with on-disk request caching. Only 200s are cached."""
    return requests_cache.CachedSession(
        str(CACHE_PATH),
        backend="sqlite",
        allowable_codes=(200,),
        expire_after=requests_cache.NEVER_EXPIRE,
    )


def count_linkup(slug, session):
    """Count Linkup annotation entries on the SSR event page (cached).

    Returns (count, error, from_cache). count is -1 on error.
    """
    url = f"https://polymarket.com/event/{slug}"
    try:
        r = session.get(url, headers=UA, timeout=30)
    except Exception as e:
        return -1, str(e)[:80], False
    if r.status_code != 200:
        return -1, f"HTTP {r.status_code}", False
    return len(LINKUP_MARKER.findall(r.text)), None, bool(getattr(r, "from_cache", False))


def main():
    # PART A: Grok context via Gamma /events
    # Base buckets: top-2100 open and top-2100 closed by volume.
    buckets = [
        dict(closed="false", archived="false"),
        dict(closed="true", archived="false"),
    ]
    # PLUS: fine-grained closed sub-buckets in the $1M-$4M range that fall below the
    # top-2100 closed cap but still large enough to plausibly carry Linkup timelines
    # (observed floor for Linkup events is ~$970k). Sub-buckets sized to each be < 2100.
    band_edges = [1_000_000, 1_250_000, 1_500_000, 1_750_000, 2_000_000, 2_250_000,
                  2_500_000, 2_750_000, 3_000_000, 3_250_000, 3_500_000, 3_750_000,
                  4_000_000]
    for lo, hi in zip(band_edges[:-1], band_edges[1:]):
        buckets.append(dict(closed="true", archived="false",
                            volume_min=str(lo), volume_max=str(hi)))

    by_id = {}
    for f in buckets:
        got = fetch_bucket(**f)
        print(f"filter={f}: {len(got):,} events (running total unique: {len(by_id)+sum(1 for e in got if e['id'] not in by_id):,})")
        for e in got:
            by_id[e["id"]] = e

    print(f"\nUnique events pulled: {len(by_id):,}")
    df = pd.DataFrame([context_fields(e) for e in by_id.values()])
    df = df.sort_values("volume", ascending=False, na_position="last").reset_index(drop=True)

    with_ctx = df[df["has_context"]]
    print(f"Grok context_description present: {len(with_ctx):,} "
          f"({len(with_ctx) / max(1, len(df)):.1%} of {len(df):,} events)")

    # PART B: Linkup timeline via event page scrape.
    # Sweep ALL events pulled from Gamma. Save incrementally so an interruption
    # doesn't lose progress.
    scrape = df.copy()
    scrape["linkup_annotations"] = 0
    scrape["scrape_error"] = None

    # Resume: if events.csv exists with a compatible schema, reuse
    # previously-scraped counts to skip re-fetching.
    resume_path = HERE / "events.csv"
    if resume_path.exists():
        prev = pd.read_csv(resume_path)
        if "linkup_annotations" in prev.columns and "slug" in prev.columns:
            prev_map = dict(zip(prev["slug"], prev["linkup_annotations"]))
            scrape["linkup_annotations"] = scrape["slug"].map(prev_map).fillna(-1).astype(int)
            already = int((scrape["linkup_annotations"] >= 0).sum())
            print(f"\nResuming: {already:,}/{len(scrape):,} events already scraped")

    s = make_session()
    N = len(scrape)
    print(f"\nScraping {N:,} events for Linkup annotations (cache: {CACHE_PATH.name})...")
    for i, row in scrape.iterrows():
        if row["linkup_annotations"] >= 0:
            continue
        n, err, from_cache = count_linkup(row["slug"], s)
        scrape.at[i, "linkup_annotations"] = n
        scrape.at[i, "scrape_error"] = err
        if (i + 1) % 100 == 0:
            hits = int((scrape["linkup_annotations"] > 0).sum())
            print(f"  scanned {i+1}/{N}, {hits} with linkup so far")
            scrape.to_csv(resume_path, index=False)
        if not from_cache:
            time.sleep(0.12)
    scrape.to_csv(resume_path, index=False)
    top = scrape  # keep downstream names

    linkup_events = top[top["linkup_annotations"] > 0]
    print(f"\n=== RESULTS ===")
    print(f"Events pulled from Gamma:                     {len(df):,}")
    print(f"  with Grok context_description (paragraph):  {len(with_ctx):,}")
    print(f"All {len(top):,} events scanned for Linkup timelines:")
    print(f"  events with >=1 linkup annotation:          {len(linkup_events):,}")
    print(f"  events with >=10 linkup annotations:        {(top['linkup_annotations']>=10).sum():,}")
    print(f"  events with >=50 linkup annotations:        {(top['linkup_annotations']>=50).sum():,}")

    # Compare to historic 107-market dataset
    hist = pd.read_csv(HERE.parent / "data" / "all_citations_full.csv")
    hist_slugs = set(hist["market_slug"].unique())
    scraped_slugs = set(top["slug"])
    linkup_slugs = set(linkup_events["slug"])
    print(f"\nHistoric 107-market dataset:")
    print(f"  historic slugs found in scraped events:         {len(hist_slugs & scraped_slugs)}")
    print(f"  historic slugs with active linkup annotations:  {len(hist_slugs & linkup_slugs)}")
    print(f"  linkup events NOT in historic set (new discoveries): {len(linkup_slugs - hist_slugs)}")


if __name__ == "__main__":
    main()
