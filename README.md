# freddie-reddit-watch

A personal, non-commercial, **read-only** Reddit digest tool, submitted for
Reddit Data API (non-commercial) access under Reddit's Responsible Builder
Policy.

## What it is

Runs on the operator's home machine (a personal Linux box). It:

1. Authenticates via Reddit's official OAuth app-only flow
   (`client_credentials`) using environment-provided credentials.
2. Periodically (roughly hourly, far below Reddit's 100 requests/minute free
   tier) fetches **public** post listings (`/r/<sub>/new`) from a small set of
   home-automation subreddits (primarily `r/homeassistant`).
3. Extracts titles, authors, scores, and short self-text excerpts into a local
   JSON digest file for the operator to read.

## What it is NOT

- **No posting, voting, commenting, or messaging.** The access token is
  app-only; the tool performs GET requests exclusively.
- **No personal data collected or stored.** Only public post titles/text land
  in the digest, on one local disk.
- **No AI/ML training use.** The digest is read by one human.
- **No redistribution.** Nothing is republished, resold, or shared.

The current interest is tracking community-reported fallout around the Home
Assistant 2026.11 release (HACS → built-in Marketplace migration) for the
operator's own smart-home maintenance.

## Configuration

Credentials are read from the environment only — never hardcoded:

```
REDDIT_CLIENT_ID      OAuth app client id
REDDIT_CLIENT_SECRET  OAuth app client secret
REDDIT_OWNER          optional, for the User-Agent string
REDDIT_DIGEST_DIR     optional output directory
```

Every request uses Reddit's required User-Agent format
(`linux:freddie-reddit-watch:v1.0 (by /u/<user>)`), targets `oauth.reddit.com`
only, and honours `X-Ratelimit-Reset` on HTTP 429.

## License

MIT
