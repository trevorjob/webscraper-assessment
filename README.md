# Quotes Scraper

A minimal Python scraper for [quotes.toscrape.com](https://quotes.toscrape.com) that collects quotes, tags, and author profile data into a single CSV.

## Approach

The scraper (1) walks all quote listing pages via the "next" link until none remains, (2) for each quote extracts text, author name, and tags, (3) visits each author's profile URL once (with caching), and (4) parses full name, date of birth, and place of birth from the profile. A single `requests.Session()` is used for all requests, and author responses are cached in memory so each author is fetched only once. Results are written to `output.csv` with one row per quote and columns for quote text, author name, tags, and the three author-profile fields.

## Why requests + BeautifulSoup

The site is static HTML with no JavaScript-dependent content. `requests` plus BeautifulSoup is sufficient, keeps dependencies small, and avoids the overhead of a browser or async stack. It's the right fit for a straightforward, synchronous scraper that must stay simple and reviewer-friendly.

## Pagination

Listing pages are followed using the "next" link in the page footer (`li.next a`). The first page is the base URL; each subsequent page is the `href` of that link. When no "next" link exists, pagination stops. No fixed page count or URL pattern is assumed.

## Author Caching

A `dict` keyed by author profile URL is passed through the scrape. Before requesting an author page, the code checks this cache; on a hit it reuses the already-parsed author data. On a miss it fetches the page, parses it, stores the result in the cache, and returns it. This avoids duplicate HTTP requests when the same author appears on multiple quotes.

## Challenge and Solution

**Challenge:** The `span.author-born-location` element returns text prefixed with "in " (e.g. `"in Ulm, Germany"`). Writing that raw value to the CSV would produce inconsistent, dirty data where every place of birth starts with "in ".

**Solution:** A lightweight `re.sub(r"^\s*in\s+", "", raw)` strips the prefix before storing the value, producing a clean `"Ulm, Germany"` in the output. This keeps the CSV reviewer-friendly without hard-coding assumptions about whitespace or casing.

## Scalability Improvement

For higher scale (many domains or millions of pages), the next step would be **retry with exponential backoff** on transient failures (e.g. 5xx, timeouts). A small helper that retries `session.get()` 2-3 times with increasing delays would improve robustness without introducing async or new frameworks. Optionally, failed URLs could be logged or written to a "retry" list for a second pass.

## Usage

```bash
pip install -r requirements.txt
python scraper.py
```

Output: `output.csv` in the same directory (quote text, author name, tags, author full name, author birth date, author birth place).
