"""Content pages: books, writings, podcasts, events, galleries, about, recommended reading."""

import pytest
from playwright.sync_api import Page, expect

from .conftest import BASE_URL


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
