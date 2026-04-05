"""F1: Homepage load, images, key sections, newsletter form, videos, books, events."""

import re

import pytest
from playwright.sync_api import Page, expect

from .conftest import BASE_URL, check_link_status


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
        # Skip images not actually rendered (display:none containers report top=0
        # but width/height=0, so we must check both size and position)
        is_visible = img.evaluate(
            "el => {"
            "  const r = el.getBoundingClientRect();"
            "  return r.width > 0 && r.height > 0 && r.top < window.innerHeight * 2;"
            "}"
        )
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


def test_homepage_video_embeds_load(desktop_page: Page):
    """Homepage has embedded video (YouTube iframe) and it loads."""
    desktop_page.goto(BASE_URL, wait_until="networkidle")

    # Elementor injects the YouTube iframe via JS after page load — wait for it
    try:
        desktop_page.wait_for_selector(
            "iframe.elementor-video, iframe[src*='youtube.com/embed'], "
            "iframe[src*='youtu.be'], video",
            timeout=10_000,
        )
    except Exception:
        pass

    video_iframes = desktop_page.locator(
        "iframe.elementor-video, "
        "iframe[src*='youtube.com/embed'], "
        "iframe[src*='youtu.be']"
    )
    video_elements = desktop_page.locator("video")

    # Also check for Elementor's click-to-play overlay (video present but not yet iframe)
    video_overlays = desktop_page.locator(
        ".elementor-custom-embed-image-overlay, "
        "[data-settings*='youtube_url']"
    )

    has_iframe = video_iframes.count() > 0
    has_video = video_elements.count() > 0
    has_overlay = video_overlays.count() > 0

    assert has_iframe or has_video or has_overlay, (
        "No video embeds (YouTube iframes, <video>, or Elementor video widgets) found on homepage"
    )

    if has_iframe:
        src = video_iframes.first.get_attribute("src") or ""
        assert "youtube.com/embed/" in src or "youtu.be" in src, (
            f"Video iframe src is not a YouTube embed: {src}"
        )
        # Verify the YouTube embed URL is reachable
        status = check_link_status(src)
        assert status == 0 or status < 400, (
            f"YouTube embed URL broken: {src} (status {status})"
        )


def test_homepage_book_cards_render(desktop_page: Page):
    """Homepage book section displays actual book cover images, not just text."""
    desktop_page.goto(BASE_URL, wait_until="networkidle")

    # Books section uses Elementor widget-image elements with links to /book/ pages
    # Class is "book-liist-block" on /books/ page, but homepage uses Elementor image widgets
    book_section_images = desktop_page.locator(
        "section.elementor-element-e9be399 .elementor-widget-image a[href*='/book/'] img, "
        ".home-books .o-neuron-hover-holder img, "
        ".book-liist-block img"
    )

    # Fallback: any image that links to a book page anywhere on the homepage
    book_linked_images = desktop_page.locator("a[href*='/book/'] img")

    total = book_section_images.count() + book_linked_images.count()
    assert total >= 3, (
        f"Homepage shows only {total} book cover images (expected >= 3) — "
        "books may not be rendering visually"
    )

    # Verify at least 3 book cover images actually loaded (naturalWidth > 0)
    loaded = 0
    for loc in [book_section_images, book_linked_images]:
        for i in range(loc.count()):
            natural_width = loc.nth(i).evaluate("el => el.naturalWidth")
            if natural_width > 0:
                loaded += 1
    assert loaded >= 3, (
        f"Only {loaded} book cover images loaded on homepage (expected >= 3)"
    )


def test_homepage_upcoming_events_section(desktop_page: Page):
    """Homepage events section renders the MEC calendar widget or event listings."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")
    desktop_page.wait_for_timeout(2000)

    # MEC widget on homepage
    mec_widget = desktop_page.locator(
        ".mec-wrap, .mec-calendar, .mec-events-list, "
        ".mec-full-calendar-wrap, .mec-skin-list-events-container"
    )

    # Events heading
    events_heading = desktop_page.locator(
        "h5:has-text('Events'), h4:has-text('Events'), h3:has-text('Events'), "
        "h2:has-text('Events')"
    )

    has_mec = mec_widget.count() > 0
    has_heading = events_heading.count() > 0

    assert has_mec or has_heading, (
        "No events section found on homepage — neither MEC widget nor Events heading"
    )

    if has_mec:
        # Check if widget actually rendered (has content, even if "No event found")
        container_text = mec_widget.first.text_content().strip()
        assert len(container_text) > 0, "MEC widget exists but has no content"


def test_homepage_no_admin_links(desktop_page: Page):
    """No WordPress admin links leak into public homepage content."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")

    admin_links = desktop_page.locator(
        "a[href*='wp-admin'], a[href*='wp-login'], "
        "a[href*='/administrator/'], a[href*='action=edit']"
    )

    leaked = []
    for i in range(admin_links.count()):
        link = admin_links.nth(i)
        # Only flag visible links (not hidden meta/toolbar)
        if link.is_visible():
            href = link.get_attribute("href") or ""
            text = link.text_content().strip()[:50]
            leaked.append(f"'{text}' -> {href}")

    assert len(leaked) == 0, (
        f"Admin links visible on homepage: {leaked}"
    )
