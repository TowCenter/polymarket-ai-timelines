"""Extract Linkup annotation timelines from cached Polymarket event HTML.

Each annotation is a JSON object embedded in a Next.js dehydrated-query payload
as a backslash-escaped string. We locate each `"source":"linkup"` marker (in
its escaped form `\\"source\\":\\"linkup\\"`) and walk backward to the matching
opening brace, then json.loads the un-escaped substring.

Output schema mirrors the historic `data/annotations.csv`:
  market_slug, market_title, timestamp, outcome, title, summary,
  price_before, price_after, price_change, sources
"""
import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests_cache

HERE = Path(__file__).parent
CACHE_PATH = HERE / "http_cache.sqlite"
UA = {"User-Agent": "Mozilla/5.0 (compatible; polymarket-fact-check/1.0)"}

# The marker inside the escaped JSON string literal.
LINKUP_MARKER = r'\"source\":\"linkup\"'


def find_object_bounds(text, source_pos):
    """Given a position inside the escaped `"source":"linkup"` marker, walk
    backward to find the enclosing `{` and forward to the matching `}`.
    Returns (start, end) with text[start:end] being the raw escaped JSON.

    We do naive brace counting — no string awareness. In this data set,
    annotation summaries/titles don't contain literal `{` or `}`, so the count
    stays balanced. In the raw HTML the only real quotes are the outer JS
    string-literal boundaries; JSON quotes appear as `\\"` (two chars) and
    are irrelevant to brace matching.
    """
    # Backward: nearest unmatched `{` before source_pos.
    depth = 0
    start = None
    for i in range(source_pos, -1, -1):
        c = text[i]
        if c == '}':
            depth += 1
        elif c == '{':
            if depth == 0:
                start = i
                break
            depth -= 1
    if start is None:
        return None

    # Forward: matching `}` from start.
    depth = 0
    for j in range(start, len(text)):
        c = text[j]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return start, j + 1
    return None


def parse_annotation(escaped_json):
    """Decode the backslash-escaped JSON substring and parse it.

    The substring is the JSON representation of an object with JSON's own
    string chars re-escaped one extra time (so it can live inside a JS string
    literal). To reverse: wrap it in outer quotes to make it a valid JSON
    string, json.loads that to un-escape, then json.loads again to get the
    object. This preserves UTF-8 correctly.
    """
    return json.loads(json.loads(f'"{escaped_json}"'))


def extract_from_html(html):
    """Return a list of parsed annotation dicts found in the page HTML.

    Naive brace matching sometimes picks a `{` that lives inside a title/outcome
    string (real Polymarket data has cases like `{Casey Putsch"`). On a parse
    failure we back up to the next `{` before the last one and retry, up to a
    small number of attempts.
    """
    out = []
    seen_bounds = set()
    for m in re.finditer(re.escape(LINKUP_MARKER), html):
        source_pos = m.start()
        for _ in range(5):
            bounds = find_object_bounds(html, source_pos)
            if bounds is None:
                break
            if bounds in seen_bounds:
                bounds = None
                break
            raw = html[bounds[0]:bounds[1]]
            try:
                obj = parse_annotation(raw)
            except Exception as e:
                # Back up past this false-opening `{` and try again.
                source_pos = bounds[0] - 1
                last_err = (str(e)[:100], raw[:200])
                continue
            seen_bounds.add(bounds)
            if isinstance(obj, dict) and obj.get("source") == "linkup":
                out.append(obj)
            break
        else:
            out.append({"__parse_error__": last_err[0], "__raw__": last_err[1]})
    return out


def annotations_to_rows(slug, title, anns):
    rows = []
    for a in anns:
        if "__parse_error__" in a:
            rows.append({
                "market_slug": slug,
                "market_title": title,
                "timestamp": None,
                "outcome": None,
                "title": None,
                "summary": f"PARSE ERROR: {a['__parse_error__']}",
                "price_before": None,
                "price_after": None,
                "price_change": None,
                "sources": "[]",
            })
            continue
        rows.append({
            "market_slug": slug,
            "market_title": title,
            "timestamp": a.get("timestamp"),
            "outcome": a.get("outcome"),
            "title": a.get("title"),
            "summary": a.get("summary"),
            "price_before": a.get("priceBefore"),
            "price_after": a.get("priceAfter"),
            "price_change": a.get("priceChange"),
            "sources": json.dumps(a.get("sources") or []),
        })
    return rows


def log(msg, logf=None):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if logf:
        logf.write(line + "\n")
        logf.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", type=int, default=0,
                    help="if >0, only process this many slugs")
    ap.add_argument("--max-anns", type=int, default=None,
                    help="only consider slugs with linkup_annotations <= this")
    ap.add_argument("--min-anns", type=int, default=1,
                    help="only consider slugs with linkup_annotations >= this")
    ap.add_argument("--out", default=str(HERE / "annotations_new.csv"))
    ap.add_argument("--logfile", default=str(HERE / "extract.log"))
    args = ap.parse_args()

    logf = open(args.logfile, "a")
    log(f"=== extract_annotations run ===", logf)
    log(f"args: {vars(args)}", logf)

    df = pd.read_csv(HERE / "events_top_scraped.csv")
    linkup = df[df["linkup_annotations"] >= args.min_anns]
    if args.max_anns is not None:
        linkup = linkup[linkup["linkup_annotations"] <= args.max_anns]
    linkup = linkup.sort_values("linkup_annotations",
                                 ascending=False).reset_index(drop=True)
    log(f"candidate slugs (min={args.min_anns}, max={args.max_anns}): {len(linkup)}", logf)

    if args.test:
        linkup = linkup.head(args.test)
        log(f"TEST MODE — processing {args.test} slugs", logf)

    session = requests_cache.CachedSession(
        str(CACHE_PATH), backend="sqlite",
        allowable_codes=(200,), expire_after=requests_cache.NEVER_EXPIRE)

    all_rows = []
    for i, row in linkup.iterrows():
        slug = row["slug"]
        t0 = time.perf_counter()
        log(f"[{i+1}/{len(linkup)}] {slug}  (markers={row['linkup_annotations']})", logf)

        t_req = time.perf_counter()
        r = session.get(f"https://polymarket.com/event/{slug}",
                        headers=UA, timeout=30)
        req_ms = (time.perf_counter() - t_req) * 1000
        from_cache = getattr(r, "from_cache", False)
        log(f"    fetched: {len(r.text)/1e6:.2f} MB, "
            f"{req_ms:.0f} ms, from_cache={from_cache}", logf)

        t_ext = time.perf_counter()
        anns = extract_from_html(r.text)
        ext_ms = (time.perf_counter() - t_ext) * 1000
        log(f"    extracted: {len(anns)} annotations in {ext_ms:.0f} ms", logf)

        rows = annotations_to_rows(slug, row["title"], anns)
        all_rows.extend(rows)
        if args.test:
            for a in anns[:2]:
                if "__parse_error__" in a:
                    log(f"    ! parse error: {a['__parse_error__']}", logf)
                else:
                    log(f"    - {a.get('timestamp','?')}  "
                        f"{str(a.get('title',''))[:80]}", logf)
        log(f"    total: {(time.perf_counter()-t0)*1000:.0f} ms", logf)

    out_df = pd.DataFrame(all_rows)
    out_df.to_csv(args.out, index=False)
    log(f"Wrote {len(out_df):,} annotation rows to {args.out}", logf)
    covered = out_df["market_slug"].nunique() if not out_df.empty else 0
    log(f"Markets covered: {covered}", logf)
    logf.close()


if __name__ == "__main__":
    main()
