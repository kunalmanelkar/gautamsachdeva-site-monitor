"""T1: SSL cert, T3: mobile responsiveness, T4: broken link scan, TTFB measurement."""

import pytest
from playwright.sync_api import Page

from .conftest import BASE_URL, check_link_status, get_ssl_expiry_days, is_bot_blocked


def test_ssl_certificate_valid(desktop_page: Page):
    """SSL certificate is valid and has > 14 days until expiry."""
    days_remaining = get_ssl_expiry_days("gautamsachdeva.com")
    assert days_remaining > 14, (
        f"SSL certificate expires in {days_remaining} days — renew immediately!"
    )


def test_mobile_no_horizontal_overflow(mobile_page: Page):
    """No horizontal scrollbar on mobile viewport (iPhone 14: 390px)."""
    mobile_page.goto(BASE_URL, wait_until="domcontentloaded")
    mobile_page.wait_for_timeout(1000)

    overflow = mobile_page.evaluate("""() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    }""")
    assert not overflow, (
        "Homepage has horizontal overflow on mobile viewport (390px) — "
        "content extends beyond screen width"
    )


def test_mobile_no_horizontal_overflow_pixel7(page: Page):
    """No horizontal scrollbar on Pixel 7 viewport (412px)."""
    page.set_viewport_size({"width": 412, "height": 915})
    page.set_default_timeout(30_000)
    page.set_default_navigation_timeout(60_000)
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1000)

    overflow = page.evaluate("""() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    }""")
    assert not overflow, (
        "Homepage has horizontal overflow on Pixel 7 viewport (412px)"
    )


def test_key_pages_broken_link_scan(desktop_page: Page):
    """Scan 8 key pages for broken internal + key external links (status >= 400)."""
    key_pages = [
        "",
        "/about/",
        "/books/",
        "/podcasts/",
        "/events/",
        "/contact/",
        "/getupdates/",
        "/support-the-teaching/",
    ]

    key_external_domains = [
        "youtube.com", "patreon.com", "paypal.com",
        "amazon.com", "spotify.com", "podcasts.apple.com",
    ]

    all_broken = []

    for path in key_pages:
        url = f"{BASE_URL}{path}"
        resp = desktop_page.goto(url, wait_until="domcontentloaded")
        if not resp or resp.status >= 400:
            all_broken.append(f"Page itself broken: {url} ({resp.status if resp else 'no response'})")
            continue

        links = desktop_page.query_selector_all("a[href]")
        seen = set()
        for link in links:
            href = link.get_attribute("href") or ""
            if not href.startswith("http") or href in seen:
                continue
            # Check internal links + key external domains
            is_internal = "gautamsachdeva.com" in href
            is_key_external = any(domain in href for domain in key_external_domains)
            if not is_internal and not is_key_external:
                continue
            seen.add(href)

        for href in list(seen)[:15]:  # Cap at 15 per page for speed
            status = check_link_status(href, timeout=10)
            if is_bot_blocked(href, status):
                continue
            if status >= 400 or status == -1:
                all_broken.append(f"{href} (from {path}, status {status})")

    assert len(all_broken) == 0, (
        f"Broken links found across key pages ({len(all_broken)}): "
        + "; ".join(all_broken[:10])
    )


def test_homepage_ttfb(desktop_page: Page):
    """Measure homepage TTFB. Informational — warns but doesn't hard-fail."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")

    ttfb_ms = desktop_page.evaluate("""() => {
        const nav = performance.getEntriesByType('navigation')[0];
        return nav ? nav.responseStart - nav.requestStart : -1;
    }""")

    if ttfb_ms < 0:
        pytest.skip("Could not measure TTFB via Navigation Timing API")

    ttfb_s = ttfb_ms / 1000
    # Warn at 3s, but don't hard-fail (baseline is ~3.68s)
    if ttfb_s > 5.0:
        pytest.fail(f"Homepage TTFB critically slow: {ttfb_s:.2f}s (> 5s threshold)")
    elif ttfb_s > 3.0:
        import warnings
        warnings.warn(f"Homepage TTFB is slow: {ttfb_s:.2f}s (> 3s)")


def test_events_calendar_renders_mobile(mobile_page: Page):
    """Events calendar MEC widget renders on mobile viewport."""
    resp = mobile_page.goto(
        f"{BASE_URL}/events-calendar/", wait_until="domcontentloaded"
    )
    assert resp and resp.status == 200, (
        f"/events-calendar/ returned HTTP {resp.status if resp else 'no response'} on mobile"
    )
    mobile_page.wait_for_timeout(3000)

    body_text = mobile_page.text_content("body").lower()

    # MEC widget should render on mobile
    mec_widget = mobile_page.locator(
        ".mec-wrap, .mec-calendar, .mec-events-list, "
        ".mec-full-calendar-wrap, .mec-event-listing"
    )
    has_no_event_msg = "no event found" in body_text or "no upcoming" in body_text

    assert mec_widget.count() > 0 or has_no_event_msg, (
        "MEC calendar widget not rendering on mobile viewport"
    )


def test_events_page_mobile_no_overflow(mobile_page: Page):
    """Events calendar page has no horizontal overflow on mobile."""
    mobile_page.goto(
        f"{BASE_URL}/events-calendar/", wait_until="domcontentloaded"
    )
    mobile_page.wait_for_timeout(3000)

    overflow_info = mobile_page.evaluate("""() => {
        const scrollW = document.documentElement.scrollWidth;
        const clientW = document.documentElement.clientWidth;
        // Find the widest offending element
        let widest = null;
        let widestW = clientW;
        for (const el of document.querySelectorAll('*')) {
            if (el.scrollWidth > widestW) {
                widestW = el.scrollWidth;
                widest = el.tagName + '.' + [...el.classList].join('.');
            }
        }
        return { scrollW, clientW, overflow: scrollW > clientW, widest, widestW };
    }""")

    assert not overflow_info["overflow"], (
        f"Events page has horizontal overflow on mobile — "
        f"scrollWidth={overflow_info['scrollW']}px vs clientWidth={overflow_info['clientW']}px. "
        f"Widest element: {overflow_info['widest']} ({overflow_info['widestW']}px)"
    )


def test_homepage_events_section_mobile(mobile_page: Page):
    """Homepage events section renders on mobile without breaking."""
    mobile_page.goto(BASE_URL, wait_until="domcontentloaded")
    mobile_page.wait_for_timeout(2000)

    # Events section should be present on mobile
    events_heading = mobile_page.locator(
        "h5:has-text('Events'), h4:has-text('Events'), "
        "h3:has-text('Events'), h2:has-text('Events')"
    )
    mec_widget = mobile_page.locator(".mec-wrap, .mec-full-calendar-wrap")

    has_heading = events_heading.count() > 0
    has_mec = mec_widget.count() > 0

    assert has_heading or has_mec, (
        "Events section not found on homepage mobile viewport"
    )
