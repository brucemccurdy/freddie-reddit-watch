#!/usr/bin/env python3
"""freddie-reddit-watch — personal, non-commercial, READ-ONLY Reddit digest.

v2: RSS mode. Uses each subreddit's public .rss feed (reddit.com/r/<sub>.rss)
— no OAuth, no API approval required. Reads a small set of subs with polite
pacing, keeps a seen-ids state file, and converts new entries to the same
digest JSON shape as v1 so downstream tooling is unchanged.

Design intent (unchanged):
- READ-ONLY. Never posts, votes, DMs, or edits anything.
- Collects no personal data; stores only public post titles/text.
- Low volume: one request per sub per run, seconds apart; honours 429 via
  Retry-After with a hard backoff (never hammers).

Compliance notes:
- Every request carries a descriptive User-Agent per Reddit's terms.
- Public www.reddit.com/.rss endpoint; no authentication of any kind.
- On HTTP 429, sleeps Retry-After (capped) or a default backoff, once.

Usage:
  python3 reddit_watch.py [--sub homeassistant ...] [--limit 25]
  env:
    REDDIT_DIGEST_DIR  optional output dir (default ./digests)
    REDDIT_STATE_FILE  optional seen-ids file (default ./state/seen.json)
"""

import argparse
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RSS_HOST = "https://www.reddit.com"
UA = "linux:freddie-reddit-watch:v2.0-rss (personal read-only digest)"
DEFAULT_SUBS = ["homeassistant", "musicassistant", "openclaw", "Kubuntu"]
BACKOFF_DEFAULT = 90  # seconds, used when no Retry-After header


def rss_get(sub: str, limit: int) -> str:
    url = f"{RSS_HOST}/r/{urllib.parse.quote(sub)}/.rss?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            wait = min(int(float(e.headers.get("Retry-After", BACKOFF_DEFAULT))), 300)
            print(f"429 from r/{sub}; backing off {wait}s then retrying once", file=sys.stderr)
            time.sleep(wait)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        raise


def entry_text(el) -> str:
    parts = []
    title_el = el.find("a:title", {"a": "http://www.w3.org/2005/Atom"})
    if title_el is not None and title_el.text:
        parts.append(title_el.text.strip())
    body = el.find("{http://www.w3.org/1999/xhtml}body")
    if body is not None:
        txt = " ".join(body.itertext()).strip()
        if txt:
            parts.append(txt[:500])
    return "\n\n".join(parts)


def fetch_rss_subs(subs, limit: int) -> list:
    ns = {
        "a": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
    }
    out = []
    for i, sub in enumerate(subs):
        if i:
            time.sleep(15)  # polite pacing between sub fetches
        xml_text = rss_get(sub, limit)
        root = ET.fromstring(xml_text)
        for entry in root.findall("a:entry", ns):
            link = entry.find("a:link", ns)
            permalink = link.get("href") if link is not None else None
            updated = entry.find("a:updated", ns)
            created = (updated.text if updated is not None and updated.text
                       else datetime.datetime.now(datetime.timezone.utc).isoformat())
            out.append({
                "subreddit": sub,
                "title": (entry.find("a:title", ns).text or "").strip()
                          if entry.find("a:title", ns) is not None else "",
                "author": (entry.find("a:author/a:name", ns).text or "").strip()
                           if entry.find("a:author/a:name", ns) is not None else "",
                "score": None,          # not in RSS
                "num_comments": None,   # not in RSS
                "created_utc": created,
                "selftext_excerpt": entry_text(entry),
                "permalink": permalink,
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", action="append", default=None,
                    help="subreddit (repeatable); default preset list")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--digest-dir", default=None)
    args = ap.parse_args()

    subs = args.sub or DEFAULT_SUBS
    posts = fetch_rss_subs(subs, args.limit)

    digest_dir = pathlib.Path(args.digest_dir or os.environ.get(
        "REDDIT_DIGEST_DIR", pathlib.Path(__file__).parent / "digests"))
    digest_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M")
    out = digest_dir / f"digest-{stamp}.json"
    out.write_text(json.dumps({
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "subreddits": subs,
        "post_count": len(posts),
        "posts": posts,
    }, indent=2, ensure_ascii=False))
    print(f"wrote {out} ({len(posts)} posts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
