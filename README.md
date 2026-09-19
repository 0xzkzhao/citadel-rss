# Citadel Securities Market Insights RSS Feed

Auto-updating RSS feed for Citadel Securities Market Insights, bypassing Cloudflare Turnstile bot protection and embedding full article contents for modern feed readers (such as [Folo](https://folo.is)).

## Feed URL

Subscribe in your RSS reader (e.g. Folo):

```
https://raw.githubusercontent.com/0xzkzhao/citadel-rss/main/feed.xml
```

## How It Works

- Citadel Securities protects `citadelsecurities.com` behind Cloudflare Turnstile, blocking regular RSS readers and scrapers.
- A GitHub Action runs every 4 hours using TLS fingerprint impersonation (`curl_cffi`) to bypass the WAF.
- It scrapes the category feed and extracts the full body text of each market insight note.
- It compiles the enriched feed into `feed.xml`.
