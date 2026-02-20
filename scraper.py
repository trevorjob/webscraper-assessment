import csv
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quotes.toscrape.com"
DEFAULT_TIMEOUT = 15


def fetch_page(
    session: requests.Session,
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    Fetch a single page and return its text content.

    Args:
        session: Reusable HTTP session.
        url: Full URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Page HTML as string.

    Raises:
        requests.RequestException: On connection or timeout errors.
    """
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_quotes(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """
    Extract quote, author, tags, and author profile URL from a quotes page.

    Args:
        soup: Parsed BeautifulSoup of a quotes listing page.

    Returns:
        List of dicts with keys: quote_text, author_name, tags, author_url.
    """
    results = []
    for quote_div in soup.select("div.quote"):
        text_el = quote_div.select_one("span.text")
        author_el = quote_div.select_one("small.author")
        author_link = quote_div.select_one("a[href*='/author/']")
        tag_els = quote_div.select("div.tags a.tag")

        quote_text = text_el.get_text(strip=True).strip('"') if text_el else ""
        author_name = author_el.get_text(strip=True) if author_el else ""

        author_url = ""
        if author_link and author_link.get("href"):
            author_url = author_link["href"].strip("/")
            if not author_url.startswith("http"):
                author_url = f"{BASE_URL}/{author_url}"

        tags = [t.get_text(strip=True) for t in tag_els] if tag_els else []
        tags_str = ",".join(tags)

        results.append({
            "quote_text": quote_text,
            "author_name": author_name,
            "tags": tags_str,
            "author_url": author_url,
        })
    return results


def parse_author(soup: BeautifulSoup) -> dict[str, str]:
    """
    Extract author full name, date of birth, and place of birth from a profile page.

    Args:
        soup: Parsed BeautifulSoup of an author profile page.

    Returns:
        Dict with keys: full_name, birth_date, birth_place.
    """
    full_name = ""
    birth_date = ""
    birth_place = ""

    h3 = soup.select_one("h3.author-title")
    if h3:
        full_name = h3.get_text(strip=True)

    born_el = soup.select_one("span.author-born-date")
    if born_el:
        birth_date = born_el.get_text(strip=True)
    location_el = soup.select_one("span.author-born-location")
    if location_el:
        raw = location_el.get_text(strip=True)
        birth_place = re.sub(r"^\s*in\s+", "", raw, flags=re.IGNORECASE).strip()
        
    return {
        "full_name": full_name,
        "birth_date": birth_date,
        "birth_place": birth_place,
    }


def get_author_info(
    session: requests.Session,
    author_url: str,
    cache: dict[str, dict[str, str]],
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, str]:
    """
    Fetch author profile and return parsed data. Uses cache to avoid repeated requests.

    Args:
        session: Reusable HTTP session.
        author_url: Full URL of the author profile page.
        cache: Mutable dict mapping author_url -> parsed author info.
        timeout: Request timeout in seconds.

    Returns:
        Dict with full_name, birth_date, birth_place.
    """
    if author_url in cache:
        return cache[author_url]
    html = fetch_page(session, author_url, timeout=timeout)
    soup = BeautifulSoup(html, "html.parser")
    info = parse_author(soup)
    cache[author_url] = info
    return info


def scrape_all(timeout: int = DEFAULT_TIMEOUT) -> list[dict[str, Any]]:
    """
    Scrape all quote pages and enrich each quote with author profile data.

    Pagination is followed until no "next" link exists. Each author profile
    is fetched at most once (cached).

    Args:
        timeout: HTTP request timeout in seconds.

    Returns:
        List of dicts, one per quote, with quote and author fields for CSV.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "QuotesScraper/1.0 (Assessment)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    author_cache: dict[str, dict[str, str]] = {}
    all_rows: list[dict[str, Any]] = []

    next_url: str | None = BASE_URL

    while next_url:
        html = fetch_page(session, next_url, timeout=timeout)
        soup = BeautifulSoup(html, "html.parser")
        quotes = parse_quotes(soup)

        for q in quotes:
            author_info = {"full_name": "", "birth_date": "", "birth_place": ""}
            if q["author_url"]:
                try:
                    author_info = get_author_info(
                        session, q["author_url"], author_cache, timeout=timeout
                    )
                except requests.RequestException:
                    print(f"Failed to fetch author page: {e}")
            row = {
                "quote_text": q["quote_text"],
                "author_name": q["author_name"],
                "tags": q["tags"],
                "author_full_name": author_info["full_name"],
                "author_birth_date": author_info["birth_date"],
                "author_birth_place": author_info["birth_place"],
            }
            all_rows.append(row)

        next_link = soup.select_one("li.next a")
        next_url = None
        if next_link and next_link.get("href"):
            href = next_link["href"].strip("/")
            next_url = f"{BASE_URL}/{href}" if not href.startswith("http") else href

    return all_rows


def save_to_csv(rows: list[dict[str, Any]], filepath: str) -> None:
    """
    Write scraped rows to a CSV file.

    Args:
        rows: List of dicts with consistent keys.
        filepath: Output CSV path.
    """
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Scrape quotes and author data, then save to output.csv."""
    output_path = "output.csv"
    try:
        rows = scrape_all()
        save_to_csv(rows, output_path)
        print(f"Done. Scraped {len(rows)} quotes to {output_path}")
    except requests.RequestException as e:
        raise SystemExit(f"Scraping failed (network/timeout): {e}") from e


if __name__ == "__main__":
    main()
