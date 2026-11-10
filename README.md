# freddie-reddit-watch

Personal, non-commercial, READ-ONLY Reddit digest for Bruce (freddie).

v2 runs in **RSS mode**: it reads each sub's public `.rss` feed
(`reddit.com/r/<sub>.rss`) — no OAuth, no Data API approval needed. The
Reddit Data API ticket (RRPR9RP-9W9ER, Nov 2026) remains pending; if ever
approved, v1's OAuth client-credentials mode is in git history.

Default subs: homeassistant, musicassistant, openclaw, Kubuntu.

Usage:
    python3 reddit_watch.py [--sub homeassistant ...] [--limit 25]

Output: `digests/digest-YYYYMMDD-HHMM.json` (same JSON shape as v1).

Etiquette: one request per sub per run, 15s between subs, honours 429
Retry-After. Intended cadence: every ~6 hours via scheduled job.
