"""F2: Newsletter signup, contact page links, WhatsApp invite."""

import pytest
from playwright.sync_api import Page, expect

from .conftest import BASE_URL, check_link_status


def test_get_updates_form_elements(desktop_page: Page):
    """Get Updates page has MailChimp form with email, name fields, checkboxes, and submit."""
    # Actual URL is /getupdates/ (no hyphen)
    desktop_page.goto(f"{BASE_URL}/getupdates/", wait_until="domcontentloaded")

    # MailChimp form container
    form = desktop_page.locator("form#mc-embedded-subscribe-form, form[action*='list-manage.com']")
    assert form.count() > 0, "MailChimp subscription form not found"

    # Email input (ID: mce-EMAIL)
    email_input = desktop_page.locator(
        "input#mce-EMAIL, input[type='email'], input[placeholder*='email' i]"
    )
    expect(email_input.first).to_be_visible()

    # GDPR checkboxes — "Subscribe to news and updates" + "Notify me about talks in Mumbai"
    checkboxes = desktop_page.locator("input[type='checkbox'].gdpr, input.av-checkbox")
    assert checkboxes.count() >= 2, f"Expected 2 GDPR checkboxes, found {checkboxes.count()}"

    # Submit button (ID: mc-embedded-subscribe, class: shadow-btn)
    submit_btn = desktop_page.locator(
        "input#mc-embedded-subscribe, input[type='submit'], "
        "button[type='submit']"
    )
    expect(submit_btn.first).to_be_visible()


def test_contact_page_mailto_links(desktop_page: Page):
    """Contact page contains valid mailto links."""
    desktop_page.goto(f"{BASE_URL}/contact/", wait_until="domcontentloaded")

    mailto_links = desktop_page.locator("a[href^='mailto:']")
    assert mailto_links.count() > 0, "No mailto links found on Contact page"

    for i in range(mailto_links.count()):
        href = mailto_links.nth(i).get_attribute("href") or ""
        # Extract email from mailto:
        email = href.replace("mailto:", "").split("?")[0]
        assert "@" in email, f"Invalid email in mailto link: {href}"


def test_contact_page_key_links(desktop_page: Page):
    """Contact page has all expected links: mailing list, email, talks, Patreon."""
    desktop_page.goto(f"{BASE_URL}/contact/", wait_until="domcontentloaded")

    # 1. Join Mailing List — links to /mailinglist/ or /getupdates/
    mailing_link = desktop_page.locator(
        "a[href*='mailinglist'], a[href*='getupdates'], a[href*='get-updates']"
    )
    assert mailing_link.count() > 0, "Contact page missing 'Join Mailing List' link"

    # 2. Email Us — mailto link with info@gautamsachdeva.com
    email_link = desktop_page.locator("a[href*='mailto:info@gautamsachdeva.com']")
    assert email_link.count() > 0, "Contact page missing 'Email Us' mailto link"

    # 3. Talks — YouTube channel link
    talks_link = desktop_page.locator("a[href*='youtube.com']")
    assert talks_link.count() > 0, "Contact page missing 'Talks' (YouTube) link"
    talks_href = talks_link.first.get_attribute("href")
    status = check_link_status(talks_href)
    assert status == 0 or status < 400, f"Talks/YouTube link broken: status {status}"

    # 4. Patreon Podcasts — Patreon link
    patreon_link = desktop_page.locator("a[href*='patreon.com']")
    assert patreon_link.count() > 0, "Contact page missing 'Patreon Podcasts' link"


def test_whatsapp_invite_link(desktop_page: Page):
    """WhatsApp group invite link is present and not expired."""
    # WhatsApp link may be on homepage, contact, or getupdates page
    wa_link = None
    checked = []
    for path in ["", "/contact/", "/getupdates/"]:
        desktop_page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
        links = desktop_page.locator("a[href*='chat.whatsapp.com'], a[href*='wa.me']")
        if links.count() > 0:
            wa_link = links.first
            break
        checked.append(path or "/")

    assert wa_link is not None, (
        f"No WhatsApp invite link found on: {checked}"
    )

    href = wa_link.get_attribute("href")
    assert href, "WhatsApp link has no href"

    # Check the link is accessible (don't navigate — WhatsApp may redirect)
    status = check_link_status(href)
    assert status == 0 or status < 400, f"WhatsApp link returned status {status}"


def test_mailing_list_form_fillable(desktop_page: Page):
    """Get Updates form fields are fillable (email, name, city, country, checkboxes).

    Fills all fields without submitting to verify the form is interactive.
    Does NOT submit — we never create real subscriptions in tests.
    """
    desktop_page.goto(f"{BASE_URL}/getupdates/", wait_until="domcontentloaded")

    # Email field
    email = desktop_page.locator("#mce-EMAIL")
    expect(email).to_be_visible()
    email.fill("test@example.com")
    assert email.input_value() == "test@example.com", "Email field not fillable"

    # First name
    fname = desktop_page.locator("#mce-FNAME")
    expect(fname).to_be_visible()
    fname.fill("Test")
    assert fname.input_value() == "Test", "First name field not fillable"

    # Last name
    lname = desktop_page.locator("#mce-LNAME")
    expect(lname).to_be_visible()
    lname.fill("User")
    assert lname.input_value() == "User", "Last name field not fillable"

    # City
    city = desktop_page.locator("#mce-CITY")
    expect(city).to_be_visible()
    city.fill("Mumbai")
    assert city.input_value() == "Mumbai", "City field not fillable"

    # Country
    country = desktop_page.locator("#mce-COUNTRY")
    expect(country).to_be_visible()
    country.fill("India")
    assert country.input_value() == "India", "Country field not fillable"

    # GDPR checkboxes exist and are interactive
    subscribe_cb = desktop_page.locator("#gdpr_15145")
    mumbai_cb = desktop_page.locator("#gdpr_15149")
    assert subscribe_cb.count() > 0, "Subscribe checkbox (#gdpr_15145) not found"
    assert mumbai_cb.count() > 0, "Mumbai talks checkbox (#gdpr_15149) not found"

    # Submit button is present and enabled
    submit = desktop_page.locator("#mc-embedded-subscribe")
    expect(submit).to_be_visible()
    expect(submit).to_be_enabled()
