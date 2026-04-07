"""F6+F8: Social media, Amazon, Patreon, PayPal, YouTube, Spotify links."""

import pytest
from playwright.sync_api import Page

from .conftest import BASE_URL, check_link_status, is_bot_blocked


SOCIAL_MEDIA_DOMAINS = {
    "YouTube": "youtube.com",
    "Facebook": "facebook.com",
    "Instagram": "instagram.com",
    "Patreon": "patreon.com",
}


def test_social_media_links_accessible(desktop_page: Page):
    """Social media links (YouTube, Facebook, Instagram, Patreon) are present and reachable."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")

    broken = []
    missing = []

    for platform, domain in SOCIAL_MEDIA_DOMAINS.items():
        links = desktop_page.locator(f"a[href*='{domain}']")
        if links.count() == 0:
            missing.append(platform)
            continue

        href = links.first.get_attribute("href")
        status = check_link_status(href)
        if is_bot_blocked(href, status):
            continue
        if status >= 400 or status == -1:
            broken.append(f"{platform}: {href} (status {status})")

    assert len(missing) == 0, f"Missing social links: {missing}"
    assert len(broken) == 0, f"Broken social links: {broken}"


def test_amazon_book_links(desktop_page: Page):
    """Individual book pages have Amazon purchase links (presence check).

    Note: Amazon blocks bot user-agents (405/503), so we verify links are
    present and well-formed rather than checking HTTP status.
    """
    desktop_page.goto(f"{BASE_URL}/books/", wait_until="domcontentloaded")

    # Collect individual book page URLs
    book_links = desktop_page.locator("a[href*='/book/']")
    assert book_links.count() >= 1, "No book links found on /books/ page"

    seen_urls = set()
    book_urls = []
    for i in range(book_links.count()):
        href = book_links.nth(i).get_attribute("href") or ""
        if href.startswith("http") and href not in seen_urls:
            seen_urls.add(href)
            book_urls.append(href)

    # Visit up to 5 individual book pages and check for Amazon links
    books_with_amazon = []
    books_without_amazon = []
    for url in book_urls[:5]:
        resp = desktop_page.goto(url, wait_until="domcontentloaded")
        if not resp or resp.status >= 400:
            continue

        amazon_links = desktop_page.locator("a[href*='amazon']")
        if amazon_links.count() > 0:
            # Verify links are well-formed (start with https://www.amazon.)
            for j in range(min(amazon_links.count(), 3)):
                href = amazon_links.nth(j).get_attribute("href") or ""
                if href.startswith("https://www.amazon."):
                    books_with_amazon.append(url)
                    break
            else:
                books_without_amazon.append(url)
        else:
            books_without_amazon.append(url)

    assert len(books_with_amazon) >= 3, (
        f"Only {len(books_with_amazon)}/{len(book_urls[:5])} book pages have Amazon links. "
        f"Missing on: {books_without_amazon}"
    )


def test_podcast_platform_links(desktop_page: Page):
    """Podcast page has Spotify and/or Apple Podcasts links — no homepage fallback."""
    desktop_page.goto(f"{BASE_URL}/podcasts/", wait_until="domcontentloaded")

    platform_domains = {
        "Spotify": "spotify.com",
        "Apple Podcasts": "podcasts.apple.com",
    }

    missing = []
    broken = []

    for platform, domain in platform_domains.items():
        links = desktop_page.locator(f"a[href*='{domain}']")
        if links.count() == 0:
            missing.append(platform)
            continue

        href = links.first.get_attribute("href")
        status = check_link_status(href)
        if is_bot_blocked(href, status):
            continue
        if status >= 400 or status == -1:
            broken.append(f"{platform}: {href} (status {status})")

    # At least 1 of 2 platforms must be present on /podcasts/
    assert len(missing) < 2, (
        f"Podcast page missing ALL platform links: {missing}"
    )
    assert len(broken) == 0, f"Broken podcast platform links: {broken}"
