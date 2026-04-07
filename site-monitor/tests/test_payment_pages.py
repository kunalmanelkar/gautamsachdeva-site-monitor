"""F7: Support the Teaching + Contact page payment links (bank, GPay, PayPal, YouTube)."""

import pytest
from playwright.sync_api import Page, expect

from .conftest import BASE_URL, check_link_status, is_bot_blocked


def test_support_page_content(desktop_page: Page):
    """Support the Teaching page loads with contribution info."""
    desktop_page.goto(
        f"{BASE_URL}/support-the-teaching/", wait_until="domcontentloaded"
    )

    body_text = desktop_page.text_content("body").lower()

    # Must mention contributing / support
    has_support_content = any(
        term in body_text
        for term in ["contribut", "support", "patron", "patreon", "youtube membership"]
    )
    assert has_support_content, "Support page doesn't mention contributions or patronage"

    # Email for transaction receipts should be present
    assert "info@gautamsachdeva.com" in body_text, (
        "Support page missing contact email info@gautamsachdeva.com"
    )


def test_support_page_payment_buttons(desktop_page: Page):
    """Support page has all 5 payment method buttons and their links work."""
    desktop_page.goto(
        f"{BASE_URL}/support-the-teaching/", wait_until="domcontentloaded"
    )

    expected_buttons = {
        "Bank Transfer": "bank-transfer-details",
        "Google Pay": "google-pay",
        "Youtube": "youtube.com",
        "Paypal": "paypal.com",
        "Patreon": "faq-patreon",
    }

    missing = []
    broken = []
    for label, href_fragment in expected_buttons.items():
        btn = desktop_page.locator(
            f"a.elementor-button[href*='{href_fragment}']"
        )
        if btn.count() == 0:
            missing.append(label)
            continue
        href = btn.first.get_attribute("href") or ""
        if href.startswith("/"):
            href = BASE_URL + href
        status = check_link_status(href)
        if is_bot_blocked(href, status):
            continue
        if (status >= 400 or status == -1):
            broken.append(f"{label}: {href} (status {status})")

    assert len(missing) == 0, f"Missing payment buttons: {missing}"
    assert len(broken) == 0, f"Broken payment button links: {broken}"


def test_support_page_youtube_membership(desktop_page: Page):
    """YouTube membership link is present and accessible."""
    desktop_page.goto(
        f"{BASE_URL}/support-the-teaching/", wait_until="domcontentloaded"
    )

    yt_link = desktop_page.locator("a[href*='youtube.com'][href*='join']")
    assert yt_link.count() > 0, "No YouTube membership link on Support page"

    href = yt_link.first.get_attribute("href")
    status = check_link_status(href)
    assert status == 0 or (0 < status < 400), f"YouTube membership link broken: status {status}"


def test_contact_page_payment_links(desktop_page: Page):
    """Contact page has payment method links (bank transfer, Google Pay, PayPal, YouTube)."""
    desktop_page.goto(f"{BASE_URL}/contact/", wait_until="domcontentloaded")

    # Payment links are on the Contact page
    payment_links = {
        "Bank Transfer": "a[href*='bank-transfer']",
        "Google Pay": "a[href*='google-pay']",
        "PayPal": "a[href*='paypal']",
        "YouTube Membership": "a[href*='youtube.com'][href*='join']",
    }

    found = {}
    for name, selector in payment_links.items():
        links = desktop_page.locator(selector)
        found[name] = links.count() > 0

    # All 4 payment methods must be linked
    found_count = sum(found.values())
    missing = [name for name, present in found.items() if not present]
    assert found_count == 4, f"Only {found_count}/4 payment links found. Missing: {missing}"


def test_bank_transfer_details_visible(desktop_page: Page):
    """Bank transfer details page shows account number, IFSC, and bank name."""
    desktop_page.goto(
        f"{BASE_URL}/bank-transfer-details/", wait_until="domcontentloaded"
    )

    body_text = desktop_page.text_content("body")

    # Verify key bank details are visible
    assert "920010066530594" in body_text, "Account number not visible"
    assert "UTIB0000447" in body_text, "IFSC code not visible"
    assert "Axis Bank" in body_text, "Bank name not visible"


def test_google_pay_upi_visible(desktop_page: Page):
    """Google Pay page shows UPI ID."""
    desktop_page.goto(f"{BASE_URL}/google-pay/", wait_until="domcontentloaded")

    body_text = desktop_page.text_content("body").lower()

    # Verify GPay UPI ID is visible
    assert "gautamadvaita@axl" in body_text, "Google Pay UPI ID not visible"


def test_paypal_link_accessible(desktop_page: Page):
    """PayPal.me payment link on Contact page is accessible."""
    desktop_page.goto(f"{BASE_URL}/contact/", wait_until="domcontentloaded")

    paypal_link = desktop_page.locator("a[href*='paypal']")
    assert paypal_link.count() > 0, "No PayPal link found on Contact page"

    href = paypal_link.first.get_attribute("href")
    status = check_link_status(href)
    assert is_bot_blocked(href, status) or status == 0 or status < 400, (
        f"PayPal link broken: status {status}"
    )
