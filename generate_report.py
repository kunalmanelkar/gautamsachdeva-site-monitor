#!/usr/bin/env python3
"""Generate a self-contained HTML audit report from pytest JSON results.

Usage:
    python generate_report.py                    # uses site-monitor/results/latest.json
    python generate_report.py path/to/results.json
    python generate_report.py --output report.html

The output is a single HTML file with zero dependencies — open it in any
browser.  Volunteers can check off manual items, add notes, and download
a timestamped copy of their completed report.
"""

import json
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# pytest writes results/latest.json relative to CWD (project root),
# not relative to site-monitor/ where pytest.ini lives.
RESULTS_DIR = Path(__file__).parent / "results"
DEFAULT_OUTPUT = Path(__file__).parent / "report.html"

# ---------------------------------------------------------------------------
# Mapping: CSV task-sheet rows -> automated test function names
# ---------------------------------------------------------------------------
# Each task mirrors the original volunteer CSV.  `auto` lists the test
# function names that cover it; `manual` lists checks a human must still do,
# each with a short instruction on HOW to verify.

TASKS = [
    {
        "id": 1,
        "title": "Home Page",
        "description": "Page loads fast, all links and images work, videos play, layout looks correct.",
        "url": "https://gautamsachdeva.com",
        "auto": [
            "test_homepage_loads",
            "test_homepage_images_loaded",
            "test_homepage_key_sections_present",
            "test_homepage_links_not_broken",
            "test_homepage_newsletter_form_visible",
            "test_homepage_video_embeds_load",
            "test_homepage_book_cards_render",
            "test_homepage_upcoming_events_section",
            "test_homepage_no_admin_links",
            "test_homepage_ttfb",
        ],
        "manual": [
            {
                "label": "Layout and alignment looks correct on your device",
                "how": "Scroll the entire homepage. Check that no text overlaps, no images are cut off, and sections are evenly spaced. Compare mobile vs desktop if possible.",
            },
            {
                "label": "No spelling mistakes or garbled characters",
                "how": "Scan all visible headings and paragraph text. Look for broken characters like \"Ã©\" or missing words.",
            },
            {
                "label": "Russian edition book links go to the correct page",
                "how": "If the homepage shows Russian-language book links, tap each one and confirm it opens a page on amrita-rus.ru with the correct book.",
            },
        ],
    },
    {
        "id": 2,
        "title": "Mailing List (Get Updates)",
        "description": "Subscription form loads, all fields work, and a test email arrives.",
        "url": "https://gautamsachdeva.com/getupdates/",
        "auto": [
            "test_get_updates_form_elements",
            "test_mailing_list_form_fillable",
        ],
        "manual": [
            {
                "label": "Submit a test subscription and confirm the welcome email arrives",
                "how": "Fill in your name, email, city, country. Check both checkboxes. Click Subscribe. Check your inbox (and spam) within 5 minutes for a confirmation email.",
            },
            {
                "label": "Confirmation email has correct branding and working links",
                "how": "Open the confirmation email. Verify it says \"Gautam Sachdeva\", has no broken images, and all links inside the email open correctly.",
            },
        ],
    },
    {
        "id": 3,
        "title": "WhatsApp Group",
        "description": "The \"Join WhatsApp Group\" button at the bottom of the homepage opens the right group.",
        "url": "https://gautamsachdeva.com",
        "auto": [
            "test_whatsapp_invite_link",
        ],
        "manual": [
            {
                "label": "Link opens WhatsApp and shows the correct group",
                "how": "On your phone, tap the WhatsApp button. Confirm WhatsApp opens and shows a group related to Gautam Sachdeva. If it says \"invite link is revoked\", the link has expired.",
            },
        ],
    },
    {
        "id": 4,
        "title": "Contact Us",
        "description": "All links work: mailing list, email, talks (YouTube), Patreon.",
        "url": "https://gautamsachdeva.com/contact/",
        "auto": [
            "test_contact_page_key_links",
            "test_contact_page_mailto_links",
        ],
        "manual": [
            {
                "label": "\"Email Us\" opens your email app",
                "how": "Tap/click the \"Email Us\" or info@gautamsachdeva.com link. Your email client (Gmail, Outlook, Apple Mail) should open with a new message pre-addressed to info@gautamsachdeva.com.",
            },
        ],
    },
    {
        "id": 5,
        "title": "Events",
        "description": "Events page loads, individual events open, registration links and forms work.",
        "url": "https://gautamsachdeva.com/events-calendar/",
        "auto": [
            "test_events_calendar_renders",
            "test_events_page_key_links",
            "test_individual_event_clickthrough",
            "test_event_detail_links_work",
            "test_events_calendar_renders_mobile",
            "test_events_page_mobile_no_overflow",
            "test_homepage_upcoming_events_section",
            "test_homepage_events_section_mobile",
        ],
        "manual": [
            {
                "label": "Each listed event shows the correct date and time",
                "how": "Compare the dates shown on the events page with what you know to be correct (check with the team if unsure). Look for past events still showing as upcoming.",
            },
            {
                "label": "Registration forms inside events work",
                "how": "Click into an event that has a registration form. Try filling it out (you can use test data). Confirm the form submits without errors.",
            },
            {
                "label": "WhatsApp/phone links inside events work on your phone",
                "how": "If an event page shows a phone number or WhatsApp link, tap it on your phone. Phone numbers should open the dialer; WhatsApp links should open WhatsApp.",
            },
        ],
    },
    {
        "id": 6,
        "title": "Social Media Links",
        "description": "YouTube, Facebook, Instagram, and Patreon links (top right) open the correct profiles.",
        "url": "https://gautamsachdeva.com",
        "auto": [
            "test_social_media_links_accessible",
            "test_footer_links_present",
        ],
        "manual": [
            {
                "label": "Each link opens the correct profile or channel",
                "how": "Click each social icon. YouTube should open Gautam's channel, Facebook his page, Instagram his profile, Patreon his creator page. If any opens a 404 or wrong account, flag it.",
            },
        ],
    },
    {
        "id": 7,
        "title": "Support the Teaching",
        "description": "Donation page loads; Bank Transfer, Google Pay, PayPal, and YouTube Membership all work.",
        "url": "https://gautamsachdeva.com/support-the-teaching/",
        "auto": [
            "test_support_page_content",
            "test_support_page_donation_iframe",
            "test_support_page_youtube_membership",
            "test_contact_page_payment_links",
            "test_bank_transfer_details_visible",
            "test_google_pay_upi_visible",
            "test_paypal_link_accessible",
        ],
        "manual": [
            {
                "label": "Bank account number and IFSC are correct",
                "how": "Verify the account number (920010066530594), IFSC (UTIB0000447), and bank name (Axis Bank) match what's on the page. If they differ, this is critical.",
            },
            {
                "label": "Google Pay UPI ID is correct",
                "how": "The page should show gautamadvaita@axl as the UPI ID. Try scanning or copying it into Google Pay to confirm it resolves to the right recipient.",
            },
            {
                "label": "PayPal link lands on the correct PayPal.me page",
                "how": "Click the PayPal link. It should open a PayPal.me page for the correct person, not a 404 or someone else's page.",
            },
        ],
    },
    {
        "id": 8,
        "title": "Dropdown Menus",
        "description": "All navigation dropdowns work on both mobile (hamburger menu) and desktop.",
        "url": "https://gautamsachdeva.com",
        "auto": [
            "test_desktop_nav_menus_present",
            "test_desktop_dropdown_menus",
            "test_mobile_hamburger_menu",
            "test_nav_links_resolve",
            "test_dropdown_works_on_subpages",
        ],
        "manual": [
            {
                "label": "Mobile: hamburger menu opens, dropdowns expand, sub-items load pages",
                "how": "On your phone, tap the three-line (hamburger) icon. Tap each dropdown (About, Resources, Gallery). Tap a sub-item and confirm the correct page loads.",
            },
            {
                "label": "Desktop: hover dropdowns open, clicking sub-items loads pages",
                "how": "On desktop, hover over About, Resources, and Gallery in the nav bar. Each should show a dropdown. Click a sub-item and confirm the page loads.",
            },
        ],
    },
    {
        "id": 9,
        "title": "Reads (Books, Writings, Recommended Reading)",
        "description": "Pages load with images, book covers link to the right pages, no admin links visible.",
        "url": "https://gautamsachdeva.com/books/",
        "auto": [
            "test_books_page_displays_books",
            "test_books_page_images_load",
            "test_writings_page_loads",
            "test_writings_page_images_load",
            "test_recommended_reading_page",
            "test_recommended_reading_subpages",
            "test_russian_edition_book_links",
            "test_about_page_content",
            "test_content_pages_no_admin_links",
        ],
        "manual": [
            {
                "label": "Clicking a book cover goes to the correct book (not the wrong one)",
                "how": "On the Books page, click 2-3 book covers. Each should open a page about THAT book, with the correct title and description.",
            },
            {
                "label": "No admin or edit links visible anywhere",
                "how": "Look for links like \"Edit\", \"wp-admin\", or anything that looks like a WordPress dashboard link. These should never be visible to the public.",
            },
            {
                "label": "Russian edition links open the correct Russian book page",
                "how": "Open \"Pointers from Ramesh Balsekar\" and \"The Buddha's Sword\". Each should have a \"Russian\" link. Click it — it should open amrita-rus.ru with the matching book.",
            },
        ],
    },
    {
        "id": 10,
        "title": "Podcasts & Player",
        "description": "Player loads, play/pause works, episodes are listed, Spotify link works.",
        "url": "https://gautamsachdeva.com/podcasts/",
        "auto": [
            "test_podcast_page_audio_players",
            "test_podcast_page_episode_list",
            "test_podcast_play_pause_controls",
            "test_podcast_platform_links",
            "test_podcast_episode_archive",
        ],
        "manual": [
            {
                "label": "Press Play — audio actually plays",
                "how": "Click the play button. Wait 3 seconds. You should hear audio. If the button changes to pause but there's no sound, the audio source may be broken.",
            },
            {
                "label": "Episode search box filters episodes when you type",
                "how": "Find the search box on the podcast page. Type a keyword (e.g. \"awareness\"). The episode list should filter to show only matching episodes.",
            },
            {
                "label": "\"Listen on Spotify\" opens the correct podcast page",
                "how": "Click the Spotify link. It should open Spotify (app or web) and show Gautam Sachdeva's podcast, not a 404 or wrong podcast.",
            },
        ],
    },
    {
        "id": 11,
        "title": "Other Pages & Technical",
        "description": "Galleries, Mentors, FAQ, SSL certificate, mobile layout, broken link scan.",
        "url": "https://gautamsachdeva.com",
        "auto": [
            "test_photo_galleries_load_images",
            "test_gallery_pages_individually",
            "test_mentors_page_exists",
            "test_homage_page_loads",
            "test_faq_page_loads",
            "test_patreon_faq_page_loads",
            "test_excerpts_from_talks_page",
            "test_nav_dropdown_subpages_exist",
            "test_refund_policy_page_loads",
            "test_donations_page_loads",
            "test_ssl_certificate_valid",
            "test_mobile_no_horizontal_overflow",
            "test_mobile_no_horizontal_overflow_pixel7",
            "test_key_pages_broken_link_scan",
            "test_amazon_book_links",
        ],
        "manual": [
            {
                "label": "Gallery images are not stretched or pixelated",
                "how": "Visit Photo Gallery, Mentors, and Photos from Talks pages. Images should look sharp and maintain their natural proportions (not squeezed or stretched).",
            },
            {
                "label": "Books on homepage are not elongated — aspect ratio looks natural",
                "how": "Scroll to the Books section on the homepage. Book covers should look like normal book covers — roughly 2:3 ratio, not tall and thin or short and wide.",
            },
            {
                "label": "Newsletter forward/share buttons work",
                "how": "If you received a recent newsletter email, try the forward and share buttons inside it. Confirm the forwarded email arrives and looks correct.",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Test metadata
# ---------------------------------------------------------------------------

FRIENDLY_NAMES = {
    "test_homepage_loads": "Homepage loads (HTTP 200)",
    "test_homepage_images_loaded": "Images load without errors",
    "test_homepage_key_sections_present": "Key sections present (podcast, book, event, about)",
    "test_homepage_links_not_broken": "Internal links resolve (no 404/500)",
    "test_homepage_newsletter_form_visible": "Newsletter CTA visible",
    "test_homepage_video_embeds_load": "Video embed loads (YouTube)",
    "test_homepage_book_cards_render": "Book covers render visually",
    "test_homepage_upcoming_events_section": "Events section present",
    "test_homepage_no_admin_links": "No admin links leak",
    "test_desktop_nav_menus_present": "Desktop nav has all items",
    "test_desktop_dropdown_menus": "Dropdown menus have sub-items",
    "test_mobile_hamburger_menu": "Mobile hamburger menu works",
    "test_nav_links_resolve": "All nav links resolve",
    "test_dropdown_works_on_subpages": "Dropdowns work on sub-pages",
    "test_footer_links_present": "Footer has social links",
    "test_books_page_displays_books": "Books page shows book items",
    "test_writings_page_loads": "Writings page shows posts",
    "test_events_calendar_renders": "Events calendar renders",
    "test_photo_galleries_load_images": "Gallery pages load images",
    "test_about_page_content": "About page has content + images",
    "test_recommended_reading_page": "Recommended reading lists books",
    "test_events_page_key_links": "Events page has key links",
    "test_gallery_pages_individually": "Gallery page loads",
    "test_mentors_page_exists": "Mentors page exists (not 404)",
    "test_homage_page_loads": "Homage page loads",
    "test_recommended_reading_subpages": "Reading sub-page loads",
    "test_faq_page_loads": "FAQ page loads",
    "test_patreon_faq_page_loads": "Patreon FAQ loads",
    "test_podcast_episode_archive": "Podcast archive loads",
    "test_excerpts_from_talks_page": "Excerpts page loads",
    "test_nav_dropdown_subpages_exist": "All dropdown pages return 200",
    "test_refund_policy_page_loads": "Refund policy loads",
    "test_donations_page_loads": "Donations page loads",
    "test_books_page_images_load": "Book cover images load",
    "test_writings_page_images_load": "Writing featured images load",
    "test_russian_edition_book_links": "Russian edition links accessible",
    "test_individual_event_clickthrough": "Event detail pages load",
    "test_event_detail_links_work": "Event detail links work",
    "test_content_pages_no_admin_links": "No admin links on content pages",
    "test_podcast_page_audio_players": "Audio player present",
    "test_podcast_page_episode_list": "Episode list / search present",
    "test_podcast_play_pause_controls": "Play/pause controls visible",
    "test_support_page_content": "Support page loads",
    "test_support_page_donation_iframe": "Donation iframe loads",
    "test_support_page_youtube_membership": "YouTube membership link works",
    "test_contact_page_payment_links": "Contact page has payment links",
    "test_bank_transfer_details_visible": "Bank transfer details visible",
    "test_google_pay_upi_visible": "Google Pay UPI ID visible",
    "test_paypal_link_accessible": "PayPal link accessible",
    "test_get_updates_form_elements": "Form has required fields",
    "test_contact_page_mailto_links": "Contact page has mailto links",
    "test_contact_page_key_links": "Contact page has key links",
    "test_whatsapp_invite_link": "WhatsApp link works",
    "test_mailing_list_form_fillable": "Form fields are fillable",
    "test_social_media_links_accessible": "Social media links accessible",
    "test_amazon_book_links": "Amazon purchase links work",
    "test_podcast_platform_links": "Podcast platform links work",
    "test_ssl_certificate_valid": "SSL certificate valid (>14 days)",
    "test_mobile_no_horizontal_overflow": "No overflow (iPhone 14)",
    "test_mobile_no_horizontal_overflow_pixel7": "No overflow (Pixel 7)",
    "test_key_pages_broken_link_scan": "Broken link scan",
    "test_homepage_ttfb": "Page speed (TTFB)",
    "test_events_calendar_renders_mobile": "Events calendar on mobile",
    "test_events_page_mobile_no_overflow": "Events page no overflow (mobile)",
    "test_homepage_events_section_mobile": "Homepage events on mobile",
}

SEVERITY = {
    "test_homepage_loads": "critical", "test_ssl_certificate_valid": "critical",
    "test_support_page_donation_iframe": "critical", "test_homepage_no_admin_links": "critical",
    "test_content_pages_no_admin_links": "critical",
    "test_books_page_displays_books": "high", "test_writings_page_loads": "high",
    "test_events_calendar_renders": "high", "test_podcast_page_audio_players": "high",
    "test_desktop_dropdown_menus": "high", "test_mobile_hamburger_menu": "high",
    "test_mentors_page_exists": "high", "test_dropdown_works_on_subpages": "high",
    "test_photo_galleries_load_images": "high", "test_nav_dropdown_subpages_exist": "high",
    "test_homepage_book_cards_render": "high", "test_homepage_upcoming_events_section": "high",
    "test_books_page_images_load": "high", "test_individual_event_clickthrough": "high",
    "test_podcast_play_pause_controls": "high", "test_mailing_list_form_fillable": "high",
    "test_events_calendar_renders_mobile": "high", "test_events_page_mobile_no_overflow": "high",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def func_name(nodeid: str) -> str:
    name = nodeid.split("::")[-1] if "::" in nodeid else nodeid
    b = name.find("[")
    return name[:b] if b > 0 else name

def param_label(nodeid: str) -> str:
    m = re.search(r"\[chromium-(.*)\]", nodeid)
    return m.group(1) if m else ""

def friendly(nodeid: str) -> str:
    fn = func_name(nodeid)
    base = FRIENDLY_NAMES.get(fn, fn.replace("_", " ").replace("test ", "").title())
    p = param_label(nodeid)
    return f"{base}: {p}" if p else base

def severity(nodeid: str) -> str:
    return SEVERITY.get(func_name(nodeid), "low")

def clean_error(t: dict) -> str:
    call = t.get("call", {})
    if not isinstance(call, dict): return ""
    crash = call.get("crash", {})
    if crash and crash.get("message"):
        lines = crash["message"].split("\n")
        clean = [l for l in lines if not l.strip().startswith(("assert ", "+  where ", "E  "))]
        return (clean[0] if clean else lines[0])[:300]
    lr = call.get("longrepr", "")
    if lr:
        e = [l.strip().lstrip("E").strip() for l in lr.split("\n") if l.strip().startswith("E ")]
        if e: return e[0][:300]
    return ""


_BASE = "https://gautamsachdeva.com"

# Map test function names to the page they check
_TEST_URLS = {
    "test_homepage_loads": "/", "test_homepage_images_loaded": "/",
    "test_homepage_key_sections_present": "/", "test_homepage_links_not_broken": "/",
    "test_homepage_newsletter_form_visible": "/", "test_homepage_video_embeds_load": "/",
    "test_homepage_book_cards_render": "/", "test_homepage_upcoming_events_section": "/",
    "test_homepage_no_admin_links": "/", "test_homepage_ttfb": "/",
    "test_desktop_nav_menus_present": "/", "test_desktop_dropdown_menus": "/",
    "test_mobile_hamburger_menu": "/", "test_nav_links_resolve": "/",
    "test_dropdown_works_on_subpages": "/about/",
    "test_footer_links_present": "/",
    "test_books_page_displays_books": "/books/", "test_books_page_images_load": "/books/",
    "test_writings_page_loads": "/writings/", "test_writings_page_images_load": "/writings/",
    "test_events_calendar_renders": "/events-calendar/",
    "test_events_page_key_links": "/events-calendar/",
    "test_individual_event_clickthrough": "/events-calendar/",
    "test_event_detail_links_work": "/events-calendar/",
    "test_events_calendar_renders_mobile": "/events-calendar/",
    "test_events_page_mobile_no_overflow": "/events-calendar/",
    "test_homepage_events_section_mobile": "/",
    "test_photo_galleries_load_images": "/photo-gallery/",
    "test_gallery_pages_individually": None,  # parametrized, extracted from error
    "test_mentors_page_exists": "/mentors/",
    "test_homage_page_loads": "/homage/",
    "test_about_page_content": "/about/",
    "test_recommended_reading_page": "/recommended-reading/",
    "test_recommended_reading_subpages": None,  # parametrized
    "test_faq_page_loads": "/frequently-asked-questions/",
    "test_patreon_faq_page_loads": "/faq-patreon/",
    "test_podcast_episode_archive": "/podcast/",
    "test_excerpts_from_talks_page": "/excerpts-from-talks/",
    "test_nav_dropdown_subpages_exist": None,  # multiple pages
    "test_refund_policy_page_loads": "/refund-and-cancellation-policy/",
    "test_donations_page_loads": "/donations/",
    "test_russian_edition_book_links": "/books/",
    "test_content_pages_no_admin_links": "/books/",
    "test_podcast_page_audio_players": "/podcasts/",
    "test_podcast_page_episode_list": "/podcasts/",
    "test_podcast_play_pause_controls": "/podcasts/",
    "test_podcast_platform_links": "/podcasts/",
    "test_support_page_content": "/support-the-teaching/",
    "test_support_page_donation_iframe": "/support-the-teaching/",
    "test_support_page_youtube_membership": "/support-the-teaching/",
    "test_contact_page_payment_links": "/contact/",
    "test_bank_transfer_details_visible": "/bank-transfer-details/",
    "test_google_pay_upi_visible": "/google-pay/",
    "test_paypal_link_accessible": "/contact/",
    "test_get_updates_form_elements": "/getupdates/",
    "test_mailing_list_form_fillable": "/getupdates/",
    "test_contact_page_mailto_links": "/contact/",
    "test_contact_page_key_links": "/contact/",
    "test_whatsapp_invite_link": "/",
    "test_social_media_links_accessible": "/",
    "test_amazon_book_links": "/books/",
    "test_ssl_certificate_valid": "/",
    "test_mobile_no_horizontal_overflow": "/",
    "test_mobile_no_horizontal_overflow_pixel7": "/",
    "test_key_pages_broken_link_scan": "/",
}


_ASSET_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js", ".woff", ".woff2", ".mp3", ".mp4")

def _get_check_url(fn: str, raw: str) -> str:
    """Get the URL a volunteer should visit to verify this error."""
    # 1. Prefer the test's known page — this is always the right page to visit
    path = _TEST_URLS.get(fn)
    if path:
        return _BASE + path

    # 2. Try to extract a page URL from the error (skip static assets)
    for m in re.finditer(r"(https://gautamsachdeva\.com[^\s',\]\)\"]*)", raw):
        candidate = m.group(1).rstrip(".")
        if not any(candidate.lower().endswith(ext) for ext in _ASSET_EXTS):
            return candidate

    # 3. Extract a path like /mentors/ from the error text
    path_match = re.search(r"(/[\w-]+/)", raw)
    if path_match:
        return _BASE + path_match.group(1)

    return _BASE


def humanize_error(fn: str, raw: str) -> tuple[str, str, str]:
    """Translate a raw error into (plain_english, suggestion, check_url).

    Returns a tuple of (what_happened, what_to_do, url_to_verify).
    """
    r = raw.lower()
    url = _get_check_url(fn, raw)

    # --- HTTP status errors ---
    if "returned http 404" in r or "http 404" in r:
        page = ""
        m = re.search(r"(/[\w-]+/)", raw)
        if m:
            page = m.group(1)
        return (
            f"The page {page} doesn't exist on the website (it shows a \"Page Not Found\" error).",
            "This page may have been deleted or renamed. Check with the website admin whether this page should still exist, or if the menu link pointing to it needs to be updated.",
            url,
        )
    if "returned http 500" in r or "http 500" in r:
        return (
            "The page is returning a server error (the website is crashing when loading it).",
            "This is a serious issue. The website admin or hosting provider needs to investigate. Share this report with them.",
            url,
        )
    if "returned http 403" in r or "http 403" in r:
        return (
            "The page is blocking access (\"Forbidden\" error).",
            "This might be a permissions issue on the server. Let the website admin know.",
            url,
        )

    # --- Connection errors ---
    if "err_connection_closed" in r or "err_connection_refused" in r or "err_connection_reset" in r:
        return (
            "Couldn't connect to the website — the connection was dropped.",
            "This usually means the website was temporarily down or overloaded when the test ran. Try visiting the page yourself. If it loads fine now, this was a temporary glitch. If it's still down, contact the hosting provider.",
            url,
        )
    if "timeout" in r and ("navigation" in r or "page.goto" in r):
        return (
            "The page took too long to load and the test gave up waiting.",
            "Try visiting the page yourself. If it's slow for you too, the website may be under heavy load or the hosting might need attention.",
            url,
        )

    # --- Broken images ---
    if "broken images" in r:
        m = re.search(r"\d+", raw)
        count = m.group(0) if m else "some"
        urls = re.findall(r"https?://[^\s',\]\)\"]+", raw)
        url_note = ""
        if urls:
            names = [u.split("/")[-1].rstrip("\"'").rstrip(".")[:40] for u in urls[:3]]
            url_note = " The images affected are: " + ", ".join(names) + "."
        return (
            f"{count} images on the page failed to load — visitors see blank spaces instead.{url_note}",
            "This could mean the image files were deleted, renamed, or the upload was corrupted. The website admin should re-upload these images in WordPress.",
            url,
        )

    # --- Dropdown / navigation ---
    if "dropdown" in r and ("broken" in r or "not" in r):
        return (
            "The dropdown navigation menus aren't opening properly when you hover over them.",
            "This is a CSS or JavaScript issue with the website theme. It may affect visitors trying to navigate the site. Let the website admin know.",
            url,
        )
    if "submenu items" in r or "expected submenu" in r:
        return (
            "Some items are missing from the navigation dropdown menus.",
            "Menu items may have been accidentally removed in WordPress. Check Appearance > Menus in the WordPress admin panel.",
            url,
        )
    if "hamburger" in r and "not visible" in r:
        return (
            "The mobile menu icon (three lines) isn't showing up on phone screens.",
            "Without this, visitors on phones can't navigate the website. This is likely a theme or CSS issue.",
            url,
        )

    # --- SSL ---
    if "ssl" in r and "expire" in r:
        m = re.search(r"(\d+)\s*days", raw)
        days = m.group(1) if m else "soon"
        return (
            f"The website's security certificate (SSL) expires in {days} days.",
            "When it expires, visitors will see a scary \"Not Secure\" warning in their browser. Contact the hosting provider to renew the certificate immediately.",
            url,
        )

    # --- Donation / payment ---
    if "donation iframe" in r or "donate-module" in r:
        return (
            "The donation payment form on the Support page isn't loading.",
            "Visitors can't donate through the website. The payment widget may need to be re-configured in WordPress, or the payment provider (Razorpay/Stripe) may have an issue.",
            url,
        )

    # --- Overflow / mobile layout ---
    if "horizontal overflow" in r or "scrollwidth" in r:
        return (
            "The page is wider than the screen on mobile phones, causing awkward sideways scrolling.",
            "This is a layout bug — something on the page is too wide for phone screens. A developer needs to inspect which element is overflowing and fix the CSS.",
            url,
        )

    # --- Missing content ---
    if "no audio" in r or "no play" in r or "no.*player" in r:
        return (
            "The podcast player isn't loading — visitors can't listen to episodes on the page.",
            "The podcast plugin may have been deactivated or there's a JavaScript error. Check the Plugins page in WordPress admin.",
            url,
        )
    if "not found on" in r and "link" in r:
        return (
            "An expected link is missing from the page.",
            "Someone may have accidentally removed it while editing the page. Check the page content in WordPress.",
            url,
        )
    if "no.*found" in r and "form" in r:
        return (
            "The form on this page isn't showing up.",
            "The form plugin or embed code may have been removed or broken. Check the page editor in WordPress.",
            url,
        )

    # --- Broken links ---
    if "broken" in r and "link" in r:
        urls = re.findall(r"https?://[^\s',\]]+", raw)
        if urls:
            return (
                f"Some links on the page are broken — they lead to error pages. The affected links include: {', '.join(u.split('/')[-1][:30] for u in urls[:3])}.",
                "These links need to be updated or removed. Check each one by clicking it yourself, then fix or remove it in the WordPress page editor.",
                url,
            )
        return (
            "Some links on this page are broken — they lead to error pages.",
            "Click through the links on the page yourself to find which ones are broken, then update or remove them in WordPress.",
            url,
        )

    # --- Admin link leakage ---
    if "admin link" in r:
        return (
            "WordPress admin/edit links are visible to the public on this page.",
            "This is a security issue — visitors shouldn't see admin links. It's usually caused by being logged into WordPress while viewing the site. Log out and check again, or contact the developer.",
            url,
        )

    # --- Generic fallback: strip technical prefixes ---
    cleaned = raw
    for prefix in ["AssertionError: ", "AssertionError:", "playwright._impl._errors.Error: ",
                    "Page.goto: ", "net::", "Error: "]:
        cleaned = cleaned.replace(prefix, "")
    cleaned = cleaned.strip()
    if cleaned:
        return (cleaned, "", url)
    return (raw, "", url)

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

CSS = """
:root {
  --font: Inter, Roboto, 'Helvetica Neue', Arial, sans-serif;
  --pass-bg: #ECFDF5; --pass-fg: #065F46; --pass-bd: #A7F3D0;
  --warn-bg: #FFFBEB; --warn-fg: #92400E; --warn-bd: #FDE68A;
  --fail-bg: #FEF2F2; --fail-fg: #991B1B; --fail-bd: #FECACA;
  --info-bg: #F0F4FF; --info-fg: #3730A3; --info-bd: #C7D2FE;
  --surface: #FFFFFF; --surface2: #F9FAFB; --surface3: #F3F4F6;
  --border: #E5E7EB; --border2: #F0F1F3;
  --text1: #111827; --text2: #4B5563; --text3: #9CA3AF;
  --accent: #6366F1; --accent-light: #EEF2FF;
  --radius: 12px;
  --shadow: 0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.03);
}
*, *::before, *::after { box-sizing: border-box; }
body {
  font-family: var(--font); font-size: 15px; line-height: 1.55;
  color: var(--text1); background: var(--surface2); margin: 0;
  -webkit-font-smoothing: antialiased;
  padding-bottom: 80px;
}

/* === HEADER === */
.header { background: var(--surface); border-bottom: 1px solid var(--border); }
.header-inner {
  max-width: 720px; margin: 0 auto; padding: 28px 20px 20px;
}
.header h1 {
  font-size: 22px; font-weight: 700; margin: 0 0 2px;
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.header .subtitle {
  font-size: 13px; color: var(--text3); margin-top: 2px;
}
.header .site-link {
  font-size: 13px; color: var(--accent); text-decoration: none;
  font-weight: 500;
}
.header .site-link:hover { text-decoration: underline; }

/* === SUMMARY STRIP === */
.summary-strip {
  max-width: 720px; margin: 0 auto; padding: 16px 20px;
  display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
}
.summary-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 100px; font-size: 13px;
  font-weight: 600; border: 1px solid;
}
.summary-pill.pass { background: var(--pass-bg); color: var(--pass-fg); border-color: var(--pass-bd); }
.summary-pill.fail { background: var(--fail-bg); color: var(--fail-fg); border-color: var(--fail-bd); }
.summary-pill.skip { background: var(--surface3); color: var(--text3); border-color: var(--border); }
.summary-pill.time { background: var(--surface); color: var(--text2); border-color: var(--border); }

/* === STICKY PROGRESS === */
.progress-sticky {
  position: sticky; top: 0; z-index: 100;
  background: rgba(255,255,255,.92); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  padding: 12px 20px;
}
.progress-inner {
  max-width: 720px; margin: 0 auto;
  display: flex; align-items: center; gap: 14px;
}
.progress-label { font-size: 13px; font-weight: 600; color: var(--text2); white-space: nowrap; }
.progress-track {
  flex: 1; height: 6px; background: var(--surface3); border-radius: 100px; overflow: hidden;
}
.progress-fill {
  height: 100%; border-radius: 100px;
  background: linear-gradient(90deg, var(--accent), #818CF8);
  transition: width .4s cubic-bezier(.4,0,.2,1);
}
.progress-count {
  font-size: 13px; font-weight: 600; color: var(--text1);
  font-variant-numeric: tabular-nums; white-space: nowrap;
}

/* === VOLUNTEER BAR === */
.vol-bar {
  max-width: 720px; margin: 16px auto 0; padding: 0 20px;
  display: flex; gap: 12px; flex-wrap: wrap; align-items: center;
}
.vol-bar label { font-size: 13px; font-weight: 600; color: var(--text2); }
.vol-bar input, .vol-bar select {
  border: 1px solid var(--border); border-radius: 8px;
  padding: 7px 12px; font-size: 15px; font-family: var(--font);
  background: var(--surface); color: var(--text1);
}
.vol-bar input { width: 180px; }
.vol-bar input:focus, .vol-bar select:focus {
  outline: 2px solid var(--accent); border-color: transparent;
}

/* === TASK CARDS === */
.tasks { max-width: 720px; margin: 20px auto 0; padding: 0 20px; }
.task {
  background: var(--surface); border-radius: var(--radius);
  border: 1px solid var(--border); margin-bottom: 14px;
  box-shadow: var(--shadow); overflow: hidden;
}

/* Task header */
.task-hd {
  padding: 16px 20px; cursor: pointer; user-select: none;
  display: flex; align-items: center; gap: 14px;
  transition: background .15s;
}
.task-hd:hover { background: var(--surface2); }
.task-num {
  width: 28px; height: 28px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; flex-shrink: 0;
}
.task-hd.has-fail .task-num { background: var(--fail-bg); color: var(--fail-fg); }
.task-hd.all-pass .task-num { background: var(--pass-bg); color: var(--pass-fg); }
.task-hd.neutral  .task-num { background: var(--surface3); color: var(--text2); }
.task-title-text { flex: 1; font-weight: 600; font-size: 15px; }
.task-status-tag {
  font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 100px;
  letter-spacing: .3px; text-transform: uppercase; flex-shrink: 0;
}
.task-hd.has-fail .task-status-tag { background: var(--fail-bg); color: var(--fail-fg); }
.task-hd.all-pass .task-status-tag { background: var(--pass-bg); color: var(--pass-fg); }
.task-hd.neutral  .task-status-tag { background: var(--surface3); color: var(--text3); }
.chevron {
  font-size: 11px; color: var(--text3); transition: transform .2s;
  flex-shrink: 0;
}
.chevron.open { transform: rotate(180deg); }

/* Task body */
.task-body { padding: 0 20px 20px; }
.task-desc {
  font-size: 13px; color: var(--text3); margin-bottom: 16px;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.task-url {
  font-size: 12px; color: var(--accent); text-decoration: none;
  background: var(--accent-light); padding: 2px 8px; border-radius: 6px;
}
.task-url:hover { text-decoration: underline; }

/* Section labels */
.section-label {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .8px; color: var(--text3); margin: 18px 0 8px;
  display: flex; align-items: center; gap: 8px;
}
.section-label::after {
  content: ''; flex: 1; height: 1px; background: var(--border2);
}
.section-label .icon { font-style: normal; }

/* Automated checks (collapsed summary) */
.auto-summary {
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 10px; overflow: hidden;
}
.auto-header {
  padding: 10px 14px; font-size: 13px; color: var(--text2);
  display: flex; align-items: center; gap: 8px; cursor: pointer;
  list-style: none;
}
.auto-header::-webkit-details-marker { display: none; }
.auto-header::before {
  content: '\\25B6'; font-size: 8px; color: var(--text3);
  transition: transform .2s;
}
details[open] > .auto-header::before { transform: rotate(90deg); }
.auto-tag {
  font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 100px;
  text-transform: uppercase; letter-spacing: .4px;
}
.auto-tag.ok { background: var(--pass-bg); color: var(--pass-fg); }
.auto-tag.issue { background: var(--fail-bg); color: var(--fail-fg); }
.auto-list { list-style: none; padding: 0; margin: 0; }
.auto-item {
  padding: 7px 14px; font-size: 13px; border-top: 1px solid var(--border2);
  display: flex; align-items: flex-start; gap: 8px;
}
.auto-icon { flex-shrink: 0; font-size: 13px; line-height: 1.55; }
.auto-item.pass { color: var(--text2); }
.auto-item.pass .auto-icon { color: var(--pass-fg); }
.auto-item.fail { color: var(--fail-fg); font-weight: 500; }
.auto-item.fail .auto-icon { color: var(--fail-fg); }
.auto-item.skip { color: var(--text3); }
.auto-item.skip .auto-icon { color: var(--text3); }
.auto-err {
  margin-top: 6px; padding: 10px 12px; border-radius: 8px;
  background: var(--fail-bg); border: 1px solid var(--fail-bd);
  font-size: 13px; color: var(--fail-fg); font-weight: 400; line-height: 1.5;
}
.auto-err .err-what { font-weight: 500; }
.auto-err .err-do { color: var(--text2); margin-top: 4px; font-size: 12px; }
.auto-err .err-link {
  margin-top: 8px;
}
.auto-err .err-link a {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 13px; font-weight: 600; color: var(--accent);
  text-decoration: none; padding: 4px 12px;
  border: 1px solid var(--accent); border-radius: 6px;
  background: var(--surface); transition: background .15s;
}
.auto-err .err-link a:hover { background: var(--accent-light); }
.auto-err .err-raw {
  margin-top: 6px;
}
.auto-err .err-raw summary {
  font-size: 11px; color: var(--text3); cursor: pointer; list-style: none; user-select: none;
}
.auto-err .err-raw summary::-webkit-details-marker { display: none; }
.auto-err .err-raw pre {
  font-size: 11px; color: var(--text3); margin: 4px 0 0; white-space: pre-wrap;
  word-break: break-word; font-family: var(--font); line-height: 1.4;
}

/* Manual checks */
.manual-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
  transition: border-color .15s, opacity .3s, background .3s;
}
.manual-card:hover { border-color: #C5CAD1; }
.manual-card.done { opacity: .65; background: var(--surface2); border-color: var(--pass-bd); }
.manual-label {
  display: flex; align-items: flex-start; gap: 12px; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.manual-cb {
  appearance: none; -webkit-appearance: none;
  width: 22px; height: 22px; min-width: 22px;
  border: 2px solid #D1D5DB; border-radius: 6px;
  cursor: pointer; position: relative; margin-top: 1px;
  transition: background .15s, border-color .15s; background: #FFF;
}
.manual-cb:hover { border-color: #9CA3AF; }
.manual-cb:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.manual-cb:checked { background: var(--accent); border-color: var(--accent); }
.manual-cb:checked::after {
  content: ''; position: absolute; top: 3px; left: 7px;
  width: 5px; height: 10px; border: solid #FFF; border-width: 0 2.5px 2.5px 0;
  transform: rotate(45deg);
  animation: checkPop .2s cubic-bezier(.175,.885,.32,1.275);
}
@keyframes checkPop {
  0% { transform: rotate(45deg) scale(0); }
  50% { transform: rotate(45deg) scale(1.2); }
  100% { transform: rotate(45deg) scale(1); }
}
.manual-text { font-size: 15px; font-weight: 500; color: var(--text1); }
.manual-card.done .manual-text { color: var(--text3); text-decoration: line-through; }
.manual-help {
  margin: 8px 0 0 34px;
}
.manual-help summary {
  font-size: 13px; color: var(--accent); cursor: pointer;
  font-weight: 500; list-style: none; user-select: none;
}
.manual-help summary::-webkit-details-marker { display: none; }
.manual-help summary::before {
  content: '?'; display: inline-flex; align-items: center;
  justify-content: center; width: 16px; height: 16px; border-radius: 50%;
  background: var(--accent-light); color: var(--accent);
  font-size: 10px; font-weight: 700; margin-right: 6px;
}
.manual-help-body {
  background: #F8FAFF; border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0; padding: 10px 14px; margin-top: 8px;
  font-size: 13px; line-height: 1.6; color: var(--text2);
}

/* Notes */
.notes-area { margin-top: 14px; }
.notes-area label { font-size: 12px; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: .5px; }
.notes-area textarea {
  display: block; width: 100%; border: 1px solid var(--border); border-radius: 8px;
  padding: 10px 12px; font-size: 15px; font-family: var(--font);
  resize: vertical; margin-top: 6px; min-height: 48px;
  background: var(--surface2); color: var(--text1);
}
.notes-area textarea:focus { outline: 2px solid var(--accent); border-color: transparent; background: #FFF; }

/* === BOTTOM BAR === */
.bottom-bar {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: rgba(255,255,255,.95); backdrop-filter: blur(10px);
  border-top: 1px solid var(--border); padding: 10px 20px;
  display: flex; align-items: center; justify-content: space-between;
  z-index: 200;
}
.bottom-bar .hint { font-size: 12px; color: var(--text3); }
.btn {
  padding: 8px 18px; border-radius: 8px; border: none; cursor: pointer;
  font-size: 14px; font-weight: 600; font-family: var(--font);
  transition: filter .15s;
}
.btn:hover { filter: brightness(.93); }
.btn-primary { background: var(--accent); color: #FFF; }
.btn-ghost { background: transparent; color: var(--text2); }
.btn-ghost:hover { background: var(--surface3); }
.btns { display: flex; gap: 6px; }

/* === PRINT === */
@media print {
  .bottom-bar, .vol-bar, .progress-sticky { display: none !important; }
  .task-body { display: block !important; }
  .task { break-inside: avoid; box-shadow: none; }
  body { padding-bottom: 0; background: #fff; }
}
/* === MOBILE === */
@media (max-width: 600px) {
  .header-inner, .summary-strip, .vol-bar, .tasks { padding-left: 14px; padding-right: 14px; }
  .progress-sticky { padding: 10px 14px; }
  .task-hd { padding: 14px; gap: 10px; }
  .task-body { padding: 0 14px 16px; }
  .vol-bar input { width: 130px; }
  body { font-size: 16px; }
  .manual-text { font-size: 16px; }
}
"""

def build_html(results: dict, output: Path) -> None:
    summary = results.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    duration = results.get("duration", 0)
    created = results.get("created", 0)
    run_time = datetime.fromtimestamp(created).strftime("%B %d, %Y at %I:%M %p") if created else "Unknown"
    run_date = datetime.fromtimestamp(created).strftime("%Y-%m-%d") if created else "unknown"

    tests_by_func: dict[str, list[dict]] = {}
    for t in results.get("tests", []):
        fn = func_name(t.get("nodeid", ""))
        tests_by_func.setdefault(fn, []).append(t)

    # Count total manual checks for progress
    total_manual = sum(len(task["manual"]) for task in TASKS)

    # --- Build task cards ---
    cards = []
    for task in TASKS:
        tid = task["id"]

        # Auto checks
        auto_pass = auto_fail = auto_skip = 0
        auto_items = []
        for fn in task["auto"]:
            variants = tests_by_func.get(fn, [])
            if not variants:
                auto_items.append(f'<li class="auto-item skip"><span class="auto-icon">&#8212;</span><span>{escape(FRIENDLY_NAMES.get(fn, fn))}<div class="auto-err">Not run</div></span></li>')
                continue
            for v in variants:
                nid = v.get("nodeid", "")
                out = v.get("outcome", "unknown")
                nm = friendly(nid)
                err = clean_error(v) if out == "failed" else ""
                if out == "passed":
                    auto_pass += 1
                    auto_items.append(f'<li class="auto-item pass"><span class="auto-icon">&#10003;</span><span>{escape(nm)}</span></li>')
                elif out == "failed":
                    auto_fail += 1
                    err_html = ''
                    if err:
                        what, do, check_url = humanize_error(fn, err)
                        do_html = f'<div class="err-do">{escape(do)}</div>' if do else ''
                        link_html = f'<div class="err-link"><a href="{escape(check_url)}" target="_blank">Check it yourself &#8599;</a></div>' if check_url else ''
                        raw_html = f'<details class="err-raw"><summary>Technical details</summary><pre>{escape(err)}</pre></details>'
                        err_html = f'<div class="auto-err"><div class="err-what">{escape(what)}</div>{do_html}{link_html}{raw_html}</div>'
                    auto_items.append(f'<li class="auto-item fail"><span class="auto-icon">&#10007;</span><span>{escape(nm)}{err_html}</span></li>')
                elif out == "skipped":
                    auto_skip += 1
                    auto_items.append(f'<li class="auto-item skip"><span class="auto-icon">&#8212;</span><span>{escape(nm)}</span></li>')

        auto_total = auto_pass + auto_fail + auto_skip
        if auto_fail > 0:
            tag_cls = "issue"
            tag_text = f"{auto_fail} issue{'s' if auto_fail != 1 else ''}"
            hd_cls = "has-fail"
            status_text = f"{auto_fail} issue{'s' if auto_fail != 1 else ''}"
        elif auto_pass == auto_total and auto_total > 0:
            tag_cls = "ok"
            tag_text = "all clear"
            hd_cls = "all-pass"
            status_text = "all clear"
        else:
            tag_cls = "ok"
            tag_text = f"{auto_pass}/{auto_total}"
            hd_cls = "neutral"
            status_text = f"{auto_pass}/{auto_total}"

        # Manual checks
        manual_cards = []
        for j, item in enumerate(task["manual"]):
            cb_id = f"m-{tid}-{j}"
            manual_cards.append(f"""
            <div class="manual-card" id="card-{cb_id}">
              <label class="manual-label">
                <input type="checkbox" class="manual-cb" id="{cb_id}" data-task="{tid}" data-idx="{j}">
                <span class="manual-text">{escape(item["label"])}</span>
              </label>
              <details class="manual-help">
                <summary>How to check this</summary>
                <div class="manual-help-body">{escape(item["how"])}</div>
              </details>
            </div>""")

        url_html = f' <a class="task-url" href="{escape(task["url"])}" target="_blank">{escape(task["url"].replace("https://",""))}</a>' if task.get("url") else ""
        collapsed = ' style="display:none"' if auto_fail == 0 else ''

        cards.append(f"""
        <section class="task" id="task-{tid}">
          <div class="task-hd {hd_cls}" onclick="toggle({tid})">
            <span class="task-num">{tid}</span>
            <span class="task-title-text">{escape(task["title"])}</span>
            <span class="task-status-tag">{escape(status_text)}</span>
            <span class="chevron{'open' if auto_fail > 0 else ''}" id="chev-{tid}">&#9662;</span>
          </div>
          <div class="task-body" id="body-{tid}"{collapsed}>
            <p class="task-desc">{escape(task["description"])}{url_html}</p>

            <div class="section-label"><em class="icon">&#9881;</em> Automated checks</div>
            <details class="auto-summary"{"open" if auto_fail > 0 else ""}>
              <summary class="auto-header">
                {auto_pass + auto_fail + auto_skip} checks ran
                <span class="auto-tag {tag_cls}">{escape(tag_text)}</span>
              </summary>
              <ul class="auto-list">{"".join(auto_items)}</ul>
            </details>

            <div class="section-label"><em class="icon">&#9997;</em> Your turn</div>
            {"".join(manual_cards)}

            <div class="notes-area">
              <label for="notes-{tid}">Notes</label>
              <textarea id="notes-{tid}" data-task="{tid}" rows="1" placeholder="Anything to flag for this section..."></textarea>
            </div>
          </div>
        </section>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Site Audit \u2014 gautamsachdeva.com \u2014 {run_date}</title>
<style>{CSS}</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <h1>Site Audit Report</h1>
    <div class="subtitle">{escape(run_time)} &nbsp;&middot;&nbsp;
      <a class="site-link" href="https://gautamsachdeva.com" target="_blank">gautamsachdeva.com &#8599;</a>
    </div>
  </div>
</div>

<div class="summary-strip">
  <span class="summary-pill pass">&#10003; {passed} passed</span>
  {"<span class='summary-pill fail'>&#10007; " + str(failed) + " failed</span>" if failed else ""}
  {"<span class='summary-pill skip'>" + str(skipped) + " skipped</span>" if skipped else ""}
  <span class="summary-pill time">&#9201; {duration:.0f}s</span>
</div>

<div class="progress-sticky">
  <div class="progress-inner">
    <span class="progress-label">Your progress</span>
    <div class="progress-track"><div class="progress-fill" id="pbar" style="width:0%"></div></div>
    <span class="progress-count" id="pcount">0/{total_manual}</span>
  </div>
</div>

<div class="vol-bar">
  <label for="vname">Name</label>
  <input id="vname" placeholder="Your name">
  <label for="vdevice">Device</label>
  <select id="vdevice"><option>Mobile</option><option>Desktop</option><option>Both</option></select>
</div>

<div class="tasks">
{"".join(cards)}
</div>

<div class="bottom-bar">
  <span class="hint">Progress auto-saved in this browser</span>
  <div class="btns">
    <button class="btn btn-ghost" onclick="resetAll()">Reset</button>
    <button class="btn btn-primary" onclick="download()">Download Report</button>
  </div>
</div>

<script>
const TOTAL_MANUAL = {total_manual};
const KEY = 'audit-{run_date}';

function toggle(id) {{
  const b = document.getElementById('body-'+id);
  const c = document.getElementById('chev-'+id);
  const show = b.style.display === 'none';
  b.style.display = show ? '' : 'none';
  c.classList.toggle('open', show);
}}

// --- State ---
function load() {{ try {{ return JSON.parse(localStorage.getItem(KEY))||{{}}; }} catch {{ return {{}}; }} }}
function save(s) {{ localStorage.setItem(KEY, JSON.stringify(s)); }}
function collect() {{
  const s = {{ name: document.getElementById('vname').value, device: document.getElementById('vdevice').value, checks: {{}}, notes: {{}} }};
  document.querySelectorAll('.manual-cb').forEach(cb => s.checks[cb.id] = cb.checked);
  document.querySelectorAll('textarea[data-task]').forEach(t => s.notes[t.id] = t.value);
  return s;
}}
function restore() {{
  const s = load();
  if (s.name) document.getElementById('vname').value = s.name;
  if (s.device) document.getElementById('vdevice').value = s.device;
  if (s.checks) Object.entries(s.checks).forEach(([id,v]) => {{
    const el = document.getElementById(id);
    if (el) {{ el.checked = v; if (v) document.getElementById('card-'+id)?.classList.add('done'); }}
  }});
  if (s.notes) Object.entries(s.notes).forEach(([id,v]) => {{
    const el = document.getElementById(id);
    if (el) el.value = v;
  }});
}}
function updateProgress() {{
  const done = document.querySelectorAll('.manual-cb:checked').length;
  const pct = TOTAL_MANUAL ? Math.round(done/TOTAL_MANUAL*100) : 0;
  document.getElementById('pbar').style.width = pct+'%';
  document.getElementById('pcount').textContent = done+'/'+TOTAL_MANUAL;
}}

// Wire events
document.querySelectorAll('.manual-cb').forEach(cb => {{
  cb.addEventListener('change', () => {{
    const card = document.getElementById('card-'+cb.id);
    card?.classList.toggle('done', cb.checked);
    if (navigator.vibrate) navigator.vibrate(10);
    save(collect()); updateProgress();
  }});
}});
document.querySelectorAll('textarea[data-task]').forEach(t => t.addEventListener('input', () => save(collect())));
document.getElementById('vname').addEventListener('input', () => save(collect()));
document.getElementById('vdevice').addEventListener('change', () => save(collect()));

restore(); updateProgress();

// Open failed sections
document.querySelectorAll('.task-hd.has-fail').forEach(h => {{
  const id = h.closest('.task').id.replace('task-','');
  document.getElementById('chev-'+id)?.classList.add('open');
}});

function resetAll() {{
  if (!confirm('Clear all your notes and checkboxes?')) return;
  localStorage.removeItem(KEY);
  document.querySelectorAll('.manual-cb').forEach(cb => {{ cb.checked = false; document.getElementById('card-'+cb.id)?.classList.remove('done'); }});
  document.querySelectorAll('textarea[data-task]').forEach(t => t.value = '');
  document.getElementById('vname').value = '';
  updateProgress();
}}

function download() {{
  const c = document.documentElement.cloneNode(true);
  // Bake state
  document.querySelectorAll('.manual-cb').forEach((cb,i) => {{
    const cc = c.querySelectorAll('.manual-cb')[i];
    if (cb.checked) cc.setAttribute('checked',''); else cc.removeAttribute('checked');
    const card = c.querySelectorAll('.manual-card')[i];
    if (cb.checked) card?.classList.add('done'); else card?.classList.remove('done');
  }});
  document.querySelectorAll('textarea').forEach((ta,i) => c.querySelectorAll('textarea')[i].textContent = ta.value);
  document.querySelectorAll('input[type=text]').forEach((inp,i) => c.querySelectorAll('input[type=text]')[i].setAttribute('value', inp.value));
  const sels = document.querySelectorAll('select');
  sels.forEach((sel,i) => {{
    const opts = c.querySelectorAll('select')[i].querySelectorAll('option');
    opts.forEach(o => o.removeAttribute('selected'));
    if (opts[sel.selectedIndex]) opts[sel.selectedIndex].setAttribute('selected','');
  }});
  c.querySelectorAll('.task-body').forEach(b => b.style.display = '');
  c.querySelectorAll('.chevron').forEach(ch => ch.classList.add('open'));
  const vol = document.getElementById('vname').value || 'volunteer';
  const blob = new Blob(['<!DOCTYPE html><html>'+c.innerHTML+'</html>'], {{type:'text/html'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'site-audit-{run_date}-' + vol.toLowerCase().replace(/\\s+/g,'-') + '.html';
  a.click(); URL.revokeObjectURL(a.href);
}}
</script>
</body>
</html>"""

    output.write_text(html, encoding="utf-8")
    print(f"Report: {output}  ({len(html):,} bytes)")


def main():
    import argparse
    p = argparse.ArgumentParser(description="Generate HTML audit report.")
    p.add_argument("input", nargs="?", default=str(RESULTS_DIR / "latest.json"))
    p.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT))
    args = p.parse_args()
    path = Path(args.input)
    if not path.exists():
        print(f"Error: {path} not found. Run pytest first.", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    build_html(data, Path(args.output))


if __name__ == "__main__":
    main()
