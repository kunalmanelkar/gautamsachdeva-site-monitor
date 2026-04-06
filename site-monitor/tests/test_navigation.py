"""F10: Desktop dropdown menus, mobile hamburger, nav link validation."""

import pytest
from playwright.sync_api import Page, expect

from .conftest import BASE_URL


def test_desktop_nav_menus_present(desktop_page: Page):
    """Desktop navigation has expected top-level menu items."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")

    # Look for the primary navigation container
    nav = desktop_page.locator("nav, .elementor-nav-menu, .main-navigation, #site-navigation")
    expect(nav.first).to_be_visible()

    nav_text = nav.first.text_content().lower()
    # Actual nav items: About, Events, Books, Resources, Gallery, Contact, Get Updates
    expected_items = ["about", "events", "books", "resources", "contact"]
    missing = [item for item in expected_items if item not in nav_text]
    assert len(missing) == 0, f"Missing nav items: {missing}"


def test_desktop_dropdown_menus(desktop_page: Page):
    """Navigation has dropdown menus with submenu items (About, Resources, Gallery)."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")

    # Find menu items that have submenus
    parent_items = desktop_page.locator(
        ".menu-item-has-children, .elementor-item-has-children"
    )

    assert parent_items.count() > 0, "No dropdown menus found — navigation broken!"

    # Verify dropdown structure exists (sub-menu elements present in DOM)
    submenus = desktop_page.locator(".sub-menu")
    assert submenus.count() > 0, "No sub-menu elements found in navigation"

    # Verify known submenu items exist in the nav DOM (About, Resources, Gallery dropdowns)
    nav_html = desktop_page.locator("nav").first.inner_html().lower()
    expected_submenu_items = [
        # About dropdown
        "homage",
        # Resources dropdown
        "blog", "podcasts", "books to read",
        # Gallery dropdown — "Mentors" label links to /photo-gallery/
        "mentors", "mystics", "talks", "profile",
    ]
    found = [item for item in expected_submenu_items if item in nav_html]
    assert len(found) >= 7, f"Only {len(found)}/{len(expected_submenu_items)} expected submenu items found: {found}"


def test_mobile_hamburger_menu(mobile_page: Page):
    """Mobile viewport shows a menu toggle that opens navigation."""
    mobile_page.goto(BASE_URL, wait_until="domcontentloaded")

    # Actual hamburger is: <a class="m-nav-menu--mobile-icon" id="m-nav-menu--mobile-icon">
    hamburger = mobile_page.locator(
        "a.m-nav-menu--mobile-icon, #m-nav-menu--mobile-icon, "
        ".elementor-menu-toggle, .menu-toggle, "
        "[aria-label*='Menu' i], button.hamburger, "
        ".navbar-toggler, .mobile-menu-toggle"
    ).first

    assert hamburger.is_visible(), "Hamburger menu not visible on mobile viewport"

    hamburger.click()
    mobile_page.wait_for_timeout(1000)

    # After clicking, mobile nav should be visible
    mobile_nav = mobile_page.locator(
        ".m-nav-menu--mobile-holder a[href], "
        "nav a[href], .sub-menu a[href]"
    )
    assert mobile_nav.count() > 0, "No navigation links visible after opening mobile menu"

    # Verify submenu items are accessible in the mobile menu DOM
    mobile_html = mobile_page.locator(
        ".m-nav-menu--mobile-holder, nav"
    ).first.inner_html().lower()
    submenu_items = ["about gautam", "blog", "podcasts", "photo gallery"]
    found = [item for item in submenu_items if item in mobile_html]
    assert len(found) >= 2, f"Mobile menu missing submenu items. Found: {found}"


def test_nav_links_resolve(desktop_page: Page):
    """All navigation links return HTTP status < 400."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")

    nav_links = desktop_page.locator(
        "nav a[href], .elementor-nav-menu a[href], .main-navigation a[href]"
    )
    count = nav_links.count()
    assert count > 0, "No navigation links found"

    broken = []
    seen = set()
    for i in range(count):
        href = nav_links.nth(i).get_attribute("href") or ""
        if not href.startswith("http") or href in seen:
            continue
        seen.add(href)
        try:
            resp = desktop_page.request.head(href, timeout=10000)
            if resp.status >= 400:
                broken.append(f"{href} ({resp.status})")
        except Exception:
            broken.append(f"{href} (timeout)")

    assert len(broken) == 0, f"Broken nav links: {broken}"


def test_dropdown_works_on_subpages(desktop_page: Page):
    """Dropdown menus work on subpages (detects CSS .current-menu-ancestor bug)."""
    desktop_page.goto(f"{BASE_URL}/about/", wait_until="domcontentloaded")

    parent_items = desktop_page.locator(
        ".menu-item-has-children, .elementor-item-has-children"
    )
    assert parent_items.count() > 0, "No dropdown menus found on /about/ page"

    failures = []
    for i in range(parent_items.count()):
        parent = parent_items.nth(i)
        # Skip non-visible items (e.g. mobile-only duplicates)
        if not parent.is_visible():
            continue
        submenu = parent.locator(".sub-menu").first
        if submenu.count() == 0:
            continue
        parent.hover()
        desktop_page.wait_for_timeout(500)
        if not submenu.is_visible():
            label = parent.text_content().strip().split("\n")[0][:30]
            failures.append(label)

    assert len(failures) == 0, f"Dropdowns broken on /about/ page: {failures}"


def test_footer_links_present(desktop_page: Page):
    """Page has social media links and footer with key links."""
    desktop_page.goto(BASE_URL, wait_until="domcontentloaded")

    # Social links may be in footer, header, or a dedicated social bar
    # Check the full page for social links presence
    social_links = desktop_page.locator(
        "a[href*='youtube.com'], a[href*='facebook.com'], "
        "a[href*='instagram.com'], a[href*='patreon.com']"
    )
    assert social_links.count() > 0, "No social media links found on page"

    # Check for footer-area content (copyright, support link)
    body_text = desktop_page.text_content("body").lower()
    has_footer_content = "support the teaching" in body_text or "©" in body_text or "copyright" in body_text
    assert has_footer_content, "No footer content (copyright or Support link) found"
