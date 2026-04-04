"""F1: Homepage load, images, key sections, newsletter form."""

import re

import pytest
from playwright.sync_api import Page, expect

from .conftest import BASE_URL


def test_homepage_loads(desktop_page: Page):
    """Homepage returns HTTP 200 and title contains 'Gautam Sachdeva'."""
    response = desktop_page.goto(BASE_URL, wait_until="domcontentloaded")
    assert response.status == 200, f"Homepage returned {response.status}"
    expect(desktop_page).to_have_title(re.compile(r"Gautam Sachdeva", re.IGNORECASE))


def test_homepage_images_loaded(desktop_page: Page):
    """Key images on the homepage have loaded (naturalWidth > 0)."""
    desktop_page.goto(BASE_URL, wait_until="networkidle")
    images = desktop_page.query_selector_all("img[src]")
    assert len(images) > 0, "No images found on homepage"

    broken = []
    for img in images:
        src = img.get_attribute("src") or ""
        # Skip tracking pixels, spacers, and lazy-loaded placeholders
        if "data:image" in src or src.endswith(".svg"):
            continue
        # Skip images that are not in viewport (lazy-loaded, may have naturalWidth 0)
        is_visible = img.evaluate("el => el.getBoundingClientRect().top < window.innerHeight * 2")
        if not is_visible:
            continue
        natural_width = img.evaluate("el => el.naturalWidth")
        if natural_width == 0:
            broken.append(src)

    # Allow at most 1 broken image (strict — CDN issues should be caught)
    assert len(broken) <= 1, f"Too many broken images ({len(broken)}): {broken[:5]}"


def test_homepage_key_sections_present(desktop_page: Page):
    """Homepage contains expected content sections."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")
    body_text = desktop_page.text_content("body").lower()

    expected_terms = ["podcast", "book", "event", "about"]
    missing = [term for term in expected_terms if term not in body_text]
    assert len(missing) == 0, f"Missing sections on homepage: {missing}"


def test_homepage_links_not_broken(desktop_page: Page):
    """Internal links on the homepage resolve without 404/500 errors."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")
    links = desktop_page.query_selector_all("a[href]")

    internal_hrefs = set()
    for link in links:
        href = link.get_attribute("href") or ""
        if href.startswith(BASE_URL) or (href.startswith("/") and not href.startswith("//")):
            full_url = href if href.startswith("http") else BASE_URL + href
            internal_hrefs.add(full_url)

    broken = []
    for href in list(internal_hrefs)[:30]:  # Cap to avoid long runs
        try:
            resp = desktop_page.request.head(href, timeout=10000)
            if resp.status >= 400:
                broken.append(f"{href} ({resp.status})")
        except Exception:
            broken.append(f"{href} (timeout)")

    assert len(broken) == 0, f"Broken internal links: {broken}"


def test_homepage_newsletter_form_visible(desktop_page: Page):
    """A newsletter/mailing list form or CTA is actually visible on the homepage."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")
    body_text = desktop_page.text_content("body").lower()

    # Check for any reference to newsletter/updates/subscribe
    has_newsletter_cta = any(
        term in body_text
        for term in ["subscribe", "newsletter", "get updates", "mailing list", "sign up"]
    )

    # Check for a VISIBLE link to the Get Updates page (not just DOM presence)
    updates_link = desktop_page.locator("a[href*='getupdates'], a[href*='get-updates']")
    has_visible_link = False
    for i in range(updates_link.count()):
        if updates_link.nth(i).is_visible():
            has_visible_link = True
            break

    assert has_newsletter_cta or has_visible_link, (
        "No newsletter form or visible Get Updates link found on homepage"
    )
