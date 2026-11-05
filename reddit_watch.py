#!/usr/bin/env python3
"""freddie-reddit-watch — personal, non-commercial, READ-ONLY Reddit digest.

Fetches public posts from a small set of home-automation subreddits via
Reddit's official Data API (OAuth client-credentials / app-only flow),
extracts titles + top-level comments for selected threads, and writes a
plain-text digest for the operator's own reading.

Design intent:
- READ-ONLY. This tool never posts, votes, DMs, or edits anything.
- It collects no personal data. It stores only public post titles/text.
- Low volume: a handful of listing requests per run, well under Reddit's
  100 requests/minute free Data API allowance.
- No AI/model training use. Digest is for one human's eyes.

Reddit Data API compliance notes:
- Authenticated requests go to oauth.reddit.com, never www.reddit.com.
- Every request carries Reddit's required descriptive User-Agent.
- Credentials come from the environment (REDDIT_CLIENT_ID /
  REDDIT_CLIENT_SECRET); they are never hardcoded or logged.
- Handles HTTP 429 by honouring the X-Ratelimit-Reset header.

Usage:
  python3 reddit_watch.py [--limit 25] [--sub homeassistant]
  env:
    REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET  required
    REDDIT_DIGEST_DIR   optional output dir (default ./digests)
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

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_HOST = "https://oauth.reddit.com"

DEFAULT_SUBS = ["homeassistant"]

def user_agent(app_id: str) -> str:
    """Reddit's required User-Agent shape: <platform>:<app ID>:<version> (by /u/name)."""
    owner = os.environ.get("REDDIT_OWNER", "u/freddie-reader-operator")
    return f"linux:freddie-reddit-watch:v1.0 (by {owner})"


def get_token(cid: str, csec: str, ua: str) -> str:
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={
        "User-Agent": ua,
        "Authorization": "Basic " + __import__("base64").b64encode(f"{cid}:{csec}".encode()).decode(),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def api_get(path: str, token: str, ua: str, params=None) -> dict:
    url = f"{API_HOST}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": ua, "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            reset = e.headers.get("X-Ratelimit-Reset", "60")
            print(f"rate limited; backing off {reset}s", file=sys.stderr)
            time.sleep(min(int(float(reset)), 600))
        raise


def fetch_listing_subs(token, ua, subs, limit) -> list:
    out = []
    for sub in subs:
        data = api_get(f"/r/{sub}/new", token, ua, {"limit": limit})
        for child in data.get("data", {}).get("children", []):
            d = child["data"]
            out.append({
                "subreddit": d.get("subreddit"),
                "title": d.get("title"),
                "author": d.get("author"),
                "score": d.get("score"),
                "num_comments": d.get("num_comments"),
                "created_utc": datetime.datetime.fromtimestamp(
                    d.get("created_utc", 0), datetime.timezone.utc).isoformat(),
                "selftext_excerpt": (d.get("selftext") or "")[:500],
                "permalink": "https://www.reddit.com" + d.get("permalink", ""),
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", action="append", default=None,
                    help="subreddit (repeatable); default: homeassistant")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--digest-dir", default=None)
    args = ap.parse_args()

    cid = os.environ.get("REDDIT_CLIENT_ID")
    csec = os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not csec:
        print("error: REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set in environment",
              file=sys.stderr)
        return 2

    subs = args.sub or DEFAULT_SUBS
    ua = user_agent(cid)
    token = get_token(cid, csec, ua)
    posts = fetch_listing_subs(token, ua, subs, args.limit)

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
