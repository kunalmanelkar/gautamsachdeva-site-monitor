"""Content pages: books, writings, podcasts, events, galleries, about, recommended reading."""

import pytest
from playwright.sync_api import Page, expect

from .conftest import BASE_URL, check_link_status


def test_books_page_displays_books(desktop_page: Page):
    """Books page shows at least 5 book items — no text fallback."""
    desktop_page.goto(f"{BASE_URL}/books/", wait_until="domcontentloaded")

    # Books are displayed as linked items with pattern /book/[slug]/
    book_links = desktop_page.locator("a[href*='/book/']")
    assert book_links.count() >= 5, (
        f"Books page has only {book_links.count()} book links (expected >= 5)"
    )


def test_writings_page_loads(desktop_page: Page):
    """Writings/blog page loads with post elements — no text-length fallback."""
    desktop_page.goto(f"{BASE_URL}/writings/", wait_until="domcontentloaded")

    # Actual structure: .writing-grid > .writing-item divs with h4 titles
    posts = desktop_page.locator(
        ".writing-item, .writing-grid .writing-item, "
        "article, .post, .elementor-post__title"
    )
    assert posts.count() >= 3, (
        f"Writings page has only {posts.count()} writing items (expected >= 3)"
    )


def test_events_calendar_renders(desktop_page: Page):
    """Events page loads and the MEC calendar widget renders."""
    # Main events calendar is at /events-calendar/, /events/ is an archive
    desktop_page.goto(f"{BASE_URL}/events-calendar/", wait_until="domcontentloaded")
    desktop_page.wait_for_timeout(2000)  # Allow calendar JS to initialize

    body_text = desktop_page.text_content("body").lower()

    # MEC (Modern Events Calendar) selectors only — no broad [class*='event']
    calendar = desktop_page.locator(
        ".mec-wrap, .mec-calendar, .mec-events-list, .mec-event-listing"
    )

    # Accept "no event found" as valid (calendar rendered, just empty)
    has_no_event_msg = "no event found" in body_text or "no upcoming" in body_text

    assert calendar.count() > 0 or has_no_event_msg, (
        "No MEC calendar widget found on events page"
    )


def test_photo_galleries_load_images(desktop_page: Page):
    """ALL gallery pages contain loaded gallery images — no generic img fallback."""
    gallery_pages = {
        "/photo-gallery/": "Photo Gallery",
        "/photos-with-mystics-teachers-authors/": "Mystics, Teachers, Authors",
        "/photos-from-talks/": "Photos from Talks",
    }

    failures = []
    for path, name in gallery_pages.items():
        resp = desktop_page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
        if not resp or resp.status >= 400:
            failures.append(f"{name} ({path}): HTTP {resp.status if resp else 'no response'}")
            continue

        # Wait for lazy-loaded images
        desktop_page.wait_for_load_state("networkidle")

        # Gallery-specific selectors only — no generic img[src] fallback
        gallery_items = desktop_page.locator(
            ".m-media-gallery__item, .gallery-item, "
            ".wp-block-gallery img, .ngg-galleryoverview img, "
            "img[src*='wp-content/gallery']"
        )
        if gallery_items.count() < 3:
            failures.append(
                f"{name} ({path}): only {gallery_items.count()} gallery items (expected >= 3)"
            )

    assert len(failures) == 0, f"Gallery page failures: {failures}"


def test_about_page_content(desktop_page: Page):
    """About page loads with biographical content and images."""
    resp = desktop_page.goto(f"{BASE_URL}/about/", wait_until="domcontentloaded")
    assert resp and resp.status == 200, f"/about/ returned HTTP {resp.status if resp else 'no response'}"

    body_text = desktop_page.text_content("body").lower()

    # Must mention key biographical details — not just text length
    assert "gautam" in body_text, "About page doesn't mention 'Gautam'"
    key_terms = ["ramesh balsekar", "yogi impressions", "advaita"]
    found_terms = [t for t in key_terms if t in body_text]
    assert len(found_terms) >= 2, (
        f"About page missing biographical content. Found {len(found_terms)}/3 key terms: {found_terms}"
    )

    # At least one image should be present
    images = desktop_page.locator("img[src]")
    assert images.count() > 0, "No images found on About page"


def test_recommended_reading_page(desktop_page: Page):
    """Recommended reading page returns 200 and lists book recommendations."""
    resp = desktop_page.goto(
        f"{BASE_URL}/recommended-reading/", wait_until="domcontentloaded"
    )
    assert resp and resp.status == 200, (
        f"/recommended-reading/ returned HTTP {resp.status if resp else 'no response'}"
    )

    body_text = desktop_page.text_content("body").lower()

    # Page should mention key authors/teachers
    expected_authors = [
        "nisargadatta", "ramesh balsekar", "ramana maharshi",
        "siddharameshwar", "eckhart tolle",
    ]
    found_authors = [a for a in expected_authors if a in body_text]
    assert len(found_authors) >= 3, (
        f"Only {len(found_authors)}/5 expected authors found: {found_authors}"
    )

    # Page should have book links (mostly Amazon)
    book_links = desktop_page.locator(
        "a[href*='amazon'], a[href*='yogiimpressions'], a[href*='/recommended-reading-']"
    )
    assert book_links.count() >= 10, (
        f"Only {book_links.count()} book/purchase links found (expected >= 10)"
    )


def test_events_page_key_links(desktop_page: Page):
    """Events page has key links: mailing list, WhatsApp group, YouTube, Support."""
    desktop_page.goto(f"{BASE_URL}/events-calendar/", wait_until="domcontentloaded")
    desktop_page.wait_for_timeout(2000)

    body_text = desktop_page.text_content("body").lower()

    # Events page should mention ways to stay updated
    has_mailing = desktop_page.locator(
        "a[href*='mailinglist'], a[href*='getupdates']"
    ).count() > 0
    has_whatsapp = desktop_page.locator(
        "a[href*='chat.whatsapp.com'], a[href*='wa.me']"
    ).count() > 0
    has_youtube = desktop_page.locator("a[href*='youtube.com']").count() > 0
    has_support = desktop_page.locator("a[href*='support-the-teaching']").count() > 0

    found = sum([has_mailing, has_whatsapp, has_youtube, has_support])
    missing = []
    if not has_mailing:
        missing.append("Mailing List")
    if not has_whatsapp:
        missing.append("WhatsApp")
    if not has_youtube:
        missing.append("YouTube")
    if not has_support:
        missing.append("Support the Teaching")

    # At least 3 of 4 key links should be present
    assert found >= 3, f"Events page missing key links ({found}/4). Missing: {missing}"


@pytest.mark.parametrize("path,name", [
    ("/photo-gallery/", "Photo Gallery"),
    ("/mentors/", "Mentors"),
    ("/photos-with-mystics-teachers-authors/", "Mystics, Teachers, Authors"),
    ("/photos-from-talks/", "Photos from Talks"),
])
def test_gallery_pages_individually(desktop_page: Page, path: str, name: str):
    """Each gallery page loads with HTTP 200 and contains gallery images."""
    resp = desktop_page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
    assert resp and resp.status == 200, (
        f"{name} ({path}) returned HTTP {resp.status if resp else 'no response'}"
    )

    # Wait for lazy-loaded images
    desktop_page.wait_for_load_state("networkidle")

    # Gallery-specific selectors
    gallery_items = desktop_page.locator(
        ".m-media-gallery__item, .gallery-item, "
        ".wp-block-gallery img, .ngg-galleryoverview img, "
        "img[src*='wp-content/gallery']"
    )
    assert gallery_items.count() >= 1, (
        f"{name} ({path}): no gallery images found"
    )


def test_mentors_page_exists(desktop_page: Page):
    """Mentors page (/mentors/) returns HTTP 200 — detects known 404 bug."""
    resp = desktop_page.goto(f"{BASE_URL}/mentors/", wait_until="domcontentloaded")
    assert resp and resp.status == 200, (
        f"/mentors/ returned HTTP {resp.status if resp else 'no response'} — "
        "this page is linked from the Gallery dropdown but returns 404"
    )


def test_homage_page_loads(desktop_page: Page):
    """Homage page (/homage/) loads — linked from About dropdown."""
    resp = desktop_page.goto(f"{BASE_URL}/homage/", wait_until="domcontentloaded")
    assert resp and resp.status == 200, (
        f"/homage/ returned HTTP {resp.status if resp else 'no response'}"
    )
    body_text = desktop_page.text_content("body").lower()
    # Page should mention spiritual masters
    masters = ["nisargadatta", "ramesh balsekar", "siddharameshwar", "ramana"]
    found = [m for m in masters if m in body_text]
    assert len(found) >= 2, f"Homage page missing master names. Found: {found}"


@pytest.mark.parametrize("slug,name", [
    ("siddharameshwar-maharaj", "Siddharameshwar Maharaj"),
    ("nisargadatta-maharaj", "Nisargadatta Maharaj"),
    ("ramesh-balsekar", "Ramesh Balsekar"),
    ("ramana-maharshi", "Ramana Maharshi"),
    ("eckhart-tolle", "Eckhart Tolle"),
    ("santosh-sachdeva", "Santosh Sachdeva"),
    ("the-sacred-india-tarot", "The Sacred India Tarot"),
])
def test_recommended_reading_subpages(desktop_page: Page, slug: str, name: str):
    """Each recommended reading subpage loads with HTTP 200 and has content."""
    path = f"/recommended-reading-{slug}/"
    resp = desktop_page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
    assert resp and resp.status == 200, (
        f"Recommended reading subpage {name} ({path}) returned HTTP "
        f"{resp.status if resp else 'no response'}"
    )
    body_text = desktop_page.text_content("body")
    assert len(body_text.strip()) > 200, f"{name} subpage appears empty"


def test_faq_page_loads(desktop_page: Page):
    """FAQ page loads with content."""
    resp = desktop_page.goto(
        f"{BASE_URL}/frequently-asked-questions/", wait_until="domcontentloaded"
    )
    assert resp and resp.status == 200, (
        f"/frequently-asked-questions/ returned HTTP {resp.status if resp else 'no response'}"
    )
    body_text = desktop_page.text_content("body").lower()
    assert "question" in body_text or "faq" in body_text or "?" in body_text, (
        "FAQ page has no question-related content"
    )


def test_patreon_faq_page_loads(desktop_page: Page):
    """Patreon FAQ page loads with content."""
    resp = desktop_page.goto(f"{BASE_URL}/faq-patreon/", wait_until="domcontentloaded")
    assert resp and resp.status == 200, (
        f"/faq-patreon/ returned HTTP {resp.status if resp else 'no response'}"
    )
    body_text = desktop_page.text_content("body").lower()
    assert "patreon" in body_text, "Patreon FAQ page doesn't mention Patreon"


def test_podcast_episode_archive(desktop_page: Page):
    """Podcast episode archive (/podcast/) loads and has episode links."""
    resp = desktop_page.goto(f"{BASE_URL}/podcast/", wait_until="domcontentloaded")
    assert resp and resp.status == 200, (
        f"/podcast/ returned HTTP {resp.status if resp else 'no response'}"
    )
    episode_links = desktop_page.locator("a[href*='/podcast/']")
    assert episode_links.count() >= 5, (
        f"Podcast archive has only {episode_links.count()} episode links (expected >= 5)"
    )


def test_excerpts_from_talks_page(desktop_page: Page):
    """Excerpts from talks page loads with content."""
    resp = desktop_page.goto(
        f"{BASE_URL}/excerpts-from-talks/", wait_until="domcontentloaded"
    )
    assert resp and resp.status == 200, (
        f"/excerpts-from-talks/ returned HTTP {resp.status if resp else 'no response'}"
    )
    body_text = desktop_page.text_content("body")
    assert len(body_text.strip()) > 200, "Excerpts from talks page appears empty"


def test_nav_dropdown_subpages_exist(desktop_page: Page):
    """All pages linked from nav dropdowns return HTTP 200 — catches 404 bugs."""
    # Pages linked from dropdown menus that should all exist
    dropdown_pages = {
        "/about/": "About (top-level)",
        "/homage/": "Homage (About dropdown)",
        "/events-calendar/": "Events Calendar",
        "/books/": "Books",
        "/recommended-reading/": "Books to Read (Resources dropdown)",
        "/writings/": "Blog (Resources dropdown)",
        "/podcasts/": "Podcasts (Resources dropdown)",
        "/photo-gallery/": "Photo Gallery (Gallery dropdown)",
        "/mentors/": "Mentors (Gallery dropdown)",
        "/photos-with-mystics-teachers-authors/": "Mystics (Gallery dropdown)",
        "/photos-from-talks/": "Talks (Gallery dropdown)",
        "/contact/": "Contact",
        "/getupdates/": "Get Updates",
    }

    failures = []
    for path, name in dropdown_pages.items():
        resp = desktop_page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
        if not resp or resp.status >= 400:
            failures.append(f"{name} ({path}): HTTP {resp.status if resp else 'no response'}")

    assert len(failures) == 0, f"Nav dropdown pages returning errors: {failures}"


def test_refund_policy_page_loads(desktop_page: Page):
    """Refund and cancellation policy page loads."""
    resp = desktop_page.goto(
        f"{BASE_URL}/refund-and-cancellation-policy/", wait_until="domcontentloaded"
    )
    assert resp and resp.status == 200, (
        f"/refund-and-cancellation-policy/ returned HTTP {resp.status if resp else 'no response'}"
    )


def test_donations_page_loads(desktop_page: Page):
    """Donations page loads."""
    resp = desktop_page.goto(f"{BASE_URL}/donations/", wait_until="domcontentloaded")
    assert resp and resp.status == 200, (
        f"/donations/ returned HTTP {resp.status if resp else 'no response'}"
    )


def test_books_page_images_load(desktop_page: Page):
    """Books page displays cover images for each book and they load correctly."""
    desktop_page.goto(f"{BASE_URL}/books/", wait_until="networkidle")

    # Book cards use class "book-liist-block" (note the typo — double i)
    book_cards = desktop_page.locator(".book-liist-block")
    assert book_cards.count() >= 5, (
        f"Books page has only {book_cards.count()} book cards (expected >= 5)"
    )

    # Check that each book card has a cover image that loaded
    broken_covers = []
    for i in range(book_cards.count()):
        card = book_cards.nth(i)
        img = card.locator("img").first
        if img.count() == 0:
            title = card.locator("h2").text_content().strip()[:40]
            broken_covers.append(f"'{title}' — no <img> element")
            continue
        natural_width = img.evaluate("el => el.naturalWidth")
        if natural_width == 0:
            src = img.get_attribute("src") or "unknown"
            broken_covers.append(f"image not loaded: {src}")

    assert len(broken_covers) == 0, (
        f"Book cover images broken: {broken_covers}"
    )


def test_writings_page_images_load(desktop_page: Page):
    """Writings/blog page displays featured images for each post and they load."""
    desktop_page.goto(f"{BASE_URL}/writings/", wait_until="networkidle")

    writing_items = desktop_page.locator(".writing-item")
    assert writing_items.count() >= 3, (
        f"Writings page has only {writing_items.count()} items (expected >= 3)"
    )

    # Check featured images in writing items
    broken = []
    checked = 0
    for i in range(min(writing_items.count(), 15)):
        item = writing_items.nth(i)
        img = item.locator("img.wp-post-image, img")
        if img.count() == 0:
            title = item.locator("h4").text_content().strip()[:40] if item.locator("h4").count() > 0 else f"item {i}"
            broken.append(f"'{title}' — no featured image")
            continue
        natural_width = img.first.evaluate("el => el.naturalWidth")
        checked += 1
        if natural_width == 0:
            src = img.first.get_attribute("src") or "unknown"
            broken.append(f"image not loaded: {src}")

    assert checked > 0, "No writing items with images found to check"
    assert len(broken) <= 1, (
        f"Writing featured images broken ({len(broken)}): {broken}"
    )


def test_russian_edition_book_links(desktop_page: Page):
    """Russian edition book links on individual book pages are present and accessible."""
    # These books are known to have Russian edition links (to amrita-rus.ru)
    books_with_russian = [
        ("/book/pointers-from-ramesh-balsekar/", "Pointers from Ramesh Balsekar"),
        ("/book/the-buddhas-sword/", "The Buddha's Sword"),
    ]

    failures = []
    for path, name in books_with_russian:
        resp = desktop_page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
        if not resp or resp.status >= 400:
            failures.append(f"{name}: page returned HTTP {resp.status if resp else 'no response'}")
            continue

        # Look for Russian edition links
        russian_links = desktop_page.locator(
            "a:has-text('Russian'), a:has-text('russian'), "
            "a[href*='amrita-rus.ru'], a[href*='russian']"
        )
        if russian_links.count() == 0:
            failures.append(f"{name}: no Russian edition link found")
            continue

        # Verify the link is well-formed and record status
        href = russian_links.first.get_attribute("href") or ""
        if href:
            assert href.startswith("http"), (
                f"{name}: Russian link is not a valid URL: {href}"
            )
            status = check_link_status(href, timeout=15)
            # amrita-rus.ru returns 405 for bot user-agents — accept as "link present"
            bot_blocked = "amrita-rus.ru" in href and status in (403, 405, 503)
            if not bot_blocked and (status >= 400 or status == -1):
                failures.append(f"{name}: Russian link broken — {href} (status {status})")

    assert len(failures) == 0, (
        f"Russian edition book link issues: {failures}"
    )


def test_individual_event_clickthrough(desktop_page: Page):
    """Click into individual events from the events calendar and verify detail pages load."""
    desktop_page.goto(f"{BASE_URL}/events-calendar/", wait_until="domcontentloaded")
    desktop_page.wait_for_timeout(3000)

    # MEC event articles
    event_links = desktop_page.locator(
        ".mec-event-article a.mec-color-hover, "
        ".mec-event-title a, "
        "a[href*='/events/']"
    )

    body_text = desktop_page.text_content("body").lower()
    has_no_events = "no event found" in body_text or "no upcoming" in body_text

    if event_links.count() == 0 and has_no_events:
        pytest.skip("No events currently listed — cannot test click-through")

    if event_links.count() == 0:
        pytest.fail("Events page has neither event links nor a 'no event found' message")

    # Collect unique event URLs
    seen = set()
    event_urls = []
    for i in range(event_links.count()):
        href = event_links.nth(i).get_attribute("href") or ""
        if href.startswith("http") and "/events/" in href and href not in seen:
            seen.add(href)
            event_urls.append(href)

    failures = []
    for url in event_urls[:5]:
        resp = desktop_page.goto(url, wait_until="domcontentloaded")
        if not resp or resp.status >= 400:
            failures.append(f"{url}: HTTP {resp.status if resp else 'no response'}")
            continue

        # Event detail page should have title and content
        title = desktop_page.locator(
            "h1.mec-single-title, .mec-event-title, h1"
        )
        if title.count() == 0:
            failures.append(f"{url}: no event title found")
            continue

        # Check body has meaningful content
        event_body = desktop_page.text_content("body").strip()
        if len(event_body) < 100:
            failures.append(f"{url}: event detail page appears empty")

    assert len(failures) == 0, (
        f"Event detail page issues: {failures}"
    )


def test_event_detail_links_work(desktop_page: Page):
    """Links within event detail pages (registration, WhatsApp, phone, maps) work."""
    desktop_page.goto(f"{BASE_URL}/events-calendar/", wait_until="domcontentloaded")
    desktop_page.wait_for_timeout(3000)

    event_links = desktop_page.locator(
        ".mec-event-article a.mec-color-hover, "
        ".mec-event-title a, "
        "a[href*='/events/']"
    )

    body_text = desktop_page.text_content("body").lower()
    has_no_events = "no event found" in body_text or "no upcoming" in body_text

    if event_links.count() == 0 and has_no_events:
        pytest.skip("No events currently listed — cannot test event detail links")

    if event_links.count() == 0:
        pytest.fail("Events page has neither event links nor a 'no event found' message")

    # Visit up to 3 event detail pages and check their internal links
    seen = set()
    event_urls = []
    for i in range(event_links.count()):
        href = event_links.nth(i).get_attribute("href") or ""
        if href.startswith("http") and "/events/" in href and href not in seen:
            seen.add(href)
            event_urls.append(href)

    broken_links = []
    for url in event_urls[:3]:
        resp = desktop_page.goto(url, wait_until="domcontentloaded")
        if not resp or resp.status >= 400:
            continue

        # Gather all links on the event detail page
        all_links = desktop_page.locator(
            ".mec-event-content a[href], .mec-single-event-description a[href], "
            ".mec-events-content a[href]"
        )

        for i in range(all_links.count()):
            href = all_links.nth(i).get_attribute("href") or ""
            if not href.startswith("http"):
                continue
            # Skip mailto/tel
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            status = check_link_status(href, timeout=10)
            if status >= 400 or status == -1:
                text = all_links.nth(i).text_content().strip()[:30]
                broken_links.append(f"'{text}' -> {href} (status {status})")

    assert len(broken_links) == 0, (
        f"Broken links in event detail pages: {broken_links}"
    )


def test_content_pages_no_admin_links(desktop_page: Page):
    """No WordPress admin links leak into public content pages."""
    pages_to_check = [
        "/books/",
        "/writings/",
        "/podcasts/",
        "/events-calendar/",
        "/recommended-reading/",
    ]

    leaked = []
    for path in pages_to_check:
        desktop_page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")

        admin_links = desktop_page.locator(
            "a[href*='wp-admin'], a[href*='wp-login'], "
            "a[href*='/administrator/'], a[href*='action=edit']"
        )

        for i in range(admin_links.count()):
            link = admin_links.nth(i)
            if link.is_visible():
                href = link.get_attribute("href") or ""
                text = link.text_content().strip()[:50]
                leaked.append(f"{path}: '{text}' -> {href}")

    assert len(leaked) == 0, (
        f"Admin links visible on content pages: {leaked}"
    )
