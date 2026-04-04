"""Site Health Dashboard — human-readable test results for gautamsachdeva.com."""

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RESULTS_DIR = Path(__file__).parent / "site-monitor" / "results"
SCREENSHOTS_DIR = Path(__file__).parent / "site-monitor" / "screenshots"

# ---------------------------------------------------------------------------
# Test metadata: friendly names, categories, and severity
# ---------------------------------------------------------------------------

CATEGORIES = {
    "test_homepage": "Homepage",
    "test_navigation": "Navigation",
    "test_content_pages": "Content Pages",
    "test_podcast_players": "Podcasts",
    "test_payment_pages": "Payments",
    "test_forms": "Forms & Contact",
    "test_external_links": "External Links",
    "test_technical": "Technical / SEO",
}

FRIENDLY_NAMES = {
    # Homepage
    "test_homepage_loads": "Homepage loads (HTTP 200 + title)",
    "test_homepage_images_loaded": "Homepage images load without errors",
    "test_homepage_key_sections_present": "Key sections present (podcast, book, event, about)",
    "test_homepage_links_not_broken": "Internal links resolve (no 404/500)",
    "test_homepage_newsletter_form_visible": "Newsletter / Get Updates CTA visible",
    # Navigation
    "test_desktop_nav_menus_present": "Desktop nav has all top-level items",
    "test_desktop_dropdown_menus": "Dropdown menus have submenu items",
    "test_mobile_hamburger_menu": "Mobile hamburger menu works",
    "test_nav_links_resolve": "All nav links resolve (no broken links)",
    "test_dropdown_works_on_subpages": "Dropdowns work on subpages (CSS bug check)",
    "test_footer_links_present": "Footer has social links and copyright",
    # Content Pages
    "test_books_page_displays_books": "Books page shows book items",
    "test_writings_page_loads": "Writings page shows blog posts",
    "test_events_calendar_renders": "Events calendar renders (MEC widget)",
    "test_photo_galleries_load_images": "All gallery pages load images",
    "test_about_page_content": "About page has biographical content and images",
    "test_recommended_reading_page": "Recommended reading page lists books",
    "test_events_page_key_links": "Events page has key links (mailing, WhatsApp, YouTube)",
    "test_gallery_pages_individually": "Gallery page loads",
    "test_mentors_page_exists": "Mentors page exists (not 404)",
    "test_homage_page_loads": "Homage page loads (About dropdown)",
    "test_recommended_reading_subpages": "Recommended reading subpage",
    "test_faq_page_loads": "FAQ page loads",
    "test_patreon_faq_page_loads": "Patreon FAQ page loads",
    "test_podcast_episode_archive": "Podcast episode archive (/podcast/)",
    "test_excerpts_from_talks_page": "Excerpts from talks page loads",
    "test_nav_dropdown_subpages_exist": "All nav dropdown pages return HTTP 200",
    "test_refund_policy_page_loads": "Refund policy page loads",
    "test_donations_page_loads": "Donations page loads",
    # Podcasts
    "test_podcast_page_audio_players": "Podcast page has audio players",
    "test_podcast_page_episode_list": "Podcast page has episode list / search",
    # Payments
    "test_support_page_content": "Support the Teaching page loads",
    "test_support_page_donation_iframe": "Donation payment iframe loads",
    "test_support_page_youtube_membership": "YouTube membership link works",
    "test_contact_page_payment_links": "Contact page has all payment links",
    "test_bank_transfer_details_visible": "Bank transfer details visible",
    "test_google_pay_upi_visible": "Google Pay UPI ID visible",
    "test_paypal_link_accessible": "PayPal link accessible",
    # Forms
    "test_get_updates_form_elements": "Get Updates form has required fields",
    "test_contact_page_mailto_links": "Contact page has mailto links",
    "test_contact_page_key_links": "Contact page has key links",
    "test_whatsapp_invite_link": "WhatsApp invite link works",
    # External Links
    "test_social_media_links_accessible": "Social media links accessible",
    "test_amazon_book_links": "Amazon purchase links work on book pages",
    "test_podcast_platform_links": "Podcast platform links work",
    # Technical
    "test_ssl_certificate_valid": "SSL certificate valid (>14 days)",
    "test_mobile_no_horizontal_overflow": "No horizontal overflow (iPhone 14)",
    "test_mobile_no_horizontal_overflow_pixel7": "No horizontal overflow (Pixel 7)",
    "test_key_pages_broken_link_scan": "Key pages broken link scan",
    "test_homepage_ttfb": "Homepage TTFB (time to first byte)",
}

SEVERITY = {
    "test_homepage_loads": "critical",
    "test_ssl_certificate_valid": "critical",
    "test_books_page_displays_books": "high",
    "test_writings_page_loads": "high",
    "test_events_calendar_renders": "high",
    "test_podcast_page_audio_players": "high",
    "test_desktop_dropdown_menus": "high",
    "test_mobile_hamburger_menu": "high",
    "test_mentors_page_exists": "high",
    "test_dropdown_works_on_subpages": "high",
    "test_photo_galleries_load_images": "high",
    "test_contact_page_payment_links": "medium",
    "test_homepage_images_loaded": "medium",
    "test_key_pages_broken_link_scan": "medium",
    "test_nav_links_resolve": "medium",
    "test_homepage_newsletter_form_visible": "medium",
    "test_homage_page_loads": "medium",
    "test_recommended_reading_subpages": "low",
    "test_faq_page_loads": "low",
    "test_patreon_faq_page_loads": "low",
    "test_podcast_episode_archive": "medium",
    "test_excerpts_from_talks_page": "low",
    "test_nav_dropdown_subpages_exist": "high",
    "test_refund_policy_page_loads": "medium",
    "test_donations_page_loads": "medium",
    "test_support_page_donation_iframe": "critical",
}

SEVERITY_LABELS = {
    "critical": ("CRITICAL", "#dc3545"),
    "high": ("HIGH", "#fd7e14"),
    "medium": ("MEDIUM", "#ffc107"),
    "low": ("LOW", "#6c757d"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _func_name(nodeid: str) -> str:
    """Extract the test function name from a nodeid like 'tests/test_foo.py::test_bar[chromium]'."""
    # Strip parameters like [chromium] or [chromium-/mentors/-Mentors]
    name = nodeid.split("::")[-1] if "::" in nodeid else nodeid
    # Remove parametrize suffix
    bracket = name.find("[")
    if bracket > 0:
        return name[:bracket]
    return name


def _param_label(nodeid: str) -> str:
    """Extract parametrize label from nodeid, e.g. '/mentors/-Mentors' from '[chromium-/mentors/-Mentors]'."""
    match = re.search(r"\[chromium-(.*)\]", nodeid)
    if match:
        return match.group(1)
    return ""


def _file_name(nodeid: str) -> str:
    """Extract the test file stem from a nodeid."""
    parts = nodeid.split("::")
    if parts:
        return Path(parts[0]).stem
    return "unknown"


def _category(nodeid: str) -> str:
    """Map nodeid to a human-readable category."""
    file_stem = _file_name(nodeid)
    return CATEGORIES.get(file_stem, file_stem)


def _friendly_name(nodeid: str) -> str:
    """Map nodeid to a human-readable test name."""
    func = _func_name(nodeid)
    base = FRIENDLY_NAMES.get(func, func.replace("_", " ").replace("test ", "").title())
    param = _param_label(nodeid)
    if param:
        return f"{base}: {param}"
    return base


def _severity(nodeid: str) -> str:
    """Get severity level for a test."""
    func = _func_name(nodeid)
    return SEVERITY.get(func, "low")


def _clean_error(test_data: dict) -> str:
    """Extract a clean, human-readable error message from test data."""
    call_info = test_data.get("call", {})
    if not isinstance(call_info, dict):
        return ""
    # Prefer crash.message (concise assertion error)
    crash = call_info.get("crash", {})
    if crash and crash.get("message"):
        msg = crash["message"]
        # Take just the AssertionError line, drop the 'assert X == Y' noise
        lines = msg.split("\n")
        clean_lines = [l for l in lines if not l.strip().startswith(("assert ", "+  where ", "E  "))]
        if clean_lines:
            return clean_lines[0]
        return lines[0]
    # Fall back to longrepr
    longrepr = call_info.get("longrepr", "")
    if longrepr:
        # Extract just the E: lines (assertion messages)
        e_lines = [l.strip().lstrip("E").strip() for l in longrepr.split("\n") if l.strip().startswith("E ")]
        if e_lines:
            return e_lines[0]
    return ""


def load_latest_results() -> dict | None:
    """Load the most recent test results JSON."""
    latest = RESULTS_DIR / "latest.json"
    if latest.exists():
        with open(latest) as f:
            return json.load(f)
    return None


def load_historical_results() -> list[dict]:
    """Load all dated result files for trend analysis."""
    results = []
    if not RESULTS_DIR.exists():
        return results
    for f in sorted(RESULTS_DIR.glob("*.json")):
        if f.name == "latest.json":
            continue
        try:
            with open(f) as fh:
                data = json.load(fh)
                date_str = f.stem
                data["_date"] = date_str
                results.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def parse_tests(data: dict) -> pd.DataFrame:
    """Parse pytest-json-report into a human-readable DataFrame."""
    tests = data.get("tests", [])
    rows = []
    for t in tests:
        nodeid = t.get("nodeid", "unknown")
        outcome = t.get("outcome", "unknown")
        duration = t.get("duration", 0)

        rows.append({
            "nodeid": nodeid,
            "Category": _category(nodeid),
            "Test": _friendly_name(nodeid),
            "Status": outcome,
            "Severity": _severity(nodeid),
            "Duration (s)": round(duration, 2),
            "Error": _clean_error(t) if outcome == "failed" else "",
            "_raw_error": t.get("call", {}).get("longrepr", "") if isinstance(t.get("call"), dict) else "",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Site Health — gautamsachdeva.com", page_icon="🏥", layout="wide")

st.title("Site Health Dashboard")
st.caption("Automated monitoring for gautamsachdeva.com")


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

results = load_latest_results()

if results is None:
    st.warning(
        "No test results found. Run `pytest` in the `site-monitor/` directory "
        "or trigger the GitHub Actions workflow."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Summary row
# ---------------------------------------------------------------------------

summary = results.get("summary", {})
total = summary.get("total", 0)
passed = summary.get("passed", 0)
failed = summary.get("failed", 0)
errors = summary.get("error", 0)
skipped = summary.get("skipped", 0)
duration = results.get("duration", 0)
created = results.get("created", 0)

if failed == 0 and errors == 0:
    st.success(f"ALL {passed} TESTS PASSED", icon="✅")
else:
    st.error(f"{failed + errors} ISSUE(S) DETECTED — {passed}/{total} checks passed", icon="❌")

run_time = datetime.fromtimestamp(created).strftime("%b %d, %Y at %I:%M %p") if created else "Unknown"

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Checks", total)
col2.metric("Passed", passed)
col3.metric("Failed", failed, delta=f"-{failed}" if failed else None, delta_color="inverse")
col4.metric("Skipped", skipped)
col5.metric("Duration", f"{duration:.0f}s")

st.caption(f"Last run: {run_time}")


# ---------------------------------------------------------------------------
# Failures summary (if any)
# ---------------------------------------------------------------------------

df = parse_tests(results)

if df.empty:
    st.info("No individual test results found in the report.")
    st.stop()

failures = df[df["Status"].isin(["failed", "error"])].copy()

if not failures.empty:
    st.divider()
    st.subheader("Issues Found")

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    failures = failures.sort_values("Severity", key=lambda s: s.map(severity_order))

    for _, row in failures.iterrows():
        sev = row["Severity"]
        sev_label, sev_color = SEVERITY_LABELS.get(sev, ("LOW", "#6c757d"))

        with st.expander(f":{sev_color[1:] if sev_color.startswith('#') else 'red'}[{sev_label}]  {row['Test']}", expanded=True):
            # Clean error message
            if row["Error"]:
                st.markdown(f"**What happened:** {row['Error']}")

            # Show category and duration
            st.caption(f"Category: {row['Category']}  ·  Duration: {row['Duration (s)']}s")

            # Full traceback in collapsed section
            if row["_raw_error"]:
                with st.popover("Show full traceback"):
                    st.code(row["_raw_error"], language="text")

            # Check for screenshot
            nodeid = row["nodeid"]
            test_name = nodeid.replace("/", "-").replace("::", "-").replace(".", "-")
            for ext in [".png", ".jpg"]:
                if SCREENSHOTS_DIR.exists():
                    for screenshot_file in SCREENSHOTS_DIR.glob(f"*{ext}"):
                        if test_name in screenshot_file.name or nodeid.split("::")[-1] in screenshot_file.name:
                            st.image(str(screenshot_file), caption=f"Screenshot: {screenshot_file.name}")
                            break


# ---------------------------------------------------------------------------
# Test results by category
# ---------------------------------------------------------------------------

st.divider()
st.subheader("All Checks by Category")

show_filter = st.radio("Show:", ["All checks", "Failures only", "Passed only"], horizontal=True)
if show_filter == "Failures only":
    df_filtered = df[df["Status"].isin(["failed", "error"])]
elif show_filter == "Passed only":
    df_filtered = df[df["Status"] == "passed"]
else:
    df_filtered = df

# Group by category
categories_in_order = [
    "Homepage", "Navigation", "Content Pages", "Podcasts",
    "Payments", "Forms & Contact", "External Links", "Technical / SEO",
]

for cat in categories_in_order:
    cat_df = df_filtered[df_filtered["Category"] == cat]
    if cat_df.empty:
        continue

    cat_passed = len(cat_df[cat_df["Status"] == "passed"])
    cat_failed = len(cat_df[cat_df["Status"].isin(["failed", "error"])])
    cat_total = len(cat_df)

    if cat_failed > 0:
        icon = "🔴"
    elif cat_passed == cat_total:
        icon = "🟢"
    else:
        icon = "🟡"

    with st.expander(f"{icon} **{cat}** — {cat_passed}/{cat_total} passed", expanded=(cat_failed > 0)):
        for _, row in cat_df.iterrows():
            status = row["Status"]
            if status == "passed":
                st.markdown(f"&nbsp;&nbsp; ✅ &nbsp; {row['Test']}  &nbsp; `{row['Duration (s)']}s`")
            elif status in ("failed", "error"):
                sev = row["Severity"]
                sev_label, _ = SEVERITY_LABELS.get(sev, ("LOW", "#6c757d"))
                st.markdown(f"&nbsp;&nbsp; ❌ &nbsp; **{row['Test']}** &nbsp; [{sev_label}]")
                if row["Error"]:
                    st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ↳ {row['Error']}")
            elif status == "skipped":
                st.markdown(f"&nbsp;&nbsp; ⏭️ &nbsp; ~~{row['Test']}~~ &nbsp; *(skipped)*")


# ---------------------------------------------------------------------------
# Screenshots gallery
# ---------------------------------------------------------------------------

if SCREENSHOTS_DIR.exists():
    screenshots = list(SCREENSHOTS_DIR.glob("*.png")) + list(SCREENSHOTS_DIR.glob("*.jpg"))
    screenshots = [s for s in screenshots if s.name != ".gitkeep"]
    if screenshots:
        st.divider()
        st.subheader("Failure Screenshots")
        cols = st.columns(min(len(screenshots), 3))
        for i, screenshot in enumerate(sorted(screenshots, reverse=True)[:9]):
            with cols[i % 3]:
                st.image(str(screenshot), caption=screenshot.name, use_container_width=True)


# ---------------------------------------------------------------------------
# Trend chart (historical data)
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Pass Rate Trend")

historical = load_historical_results()
if historical:
    trend_data = []
    for h in historical[-30:]:
        s = h.get("summary", {})
        date = h.get("_date", "unknown")
        t = s.get("total", 0)
        p = s.get("passed", 0)
        f_count = s.get("failed", 0)
        rate = (p / t * 100) if t > 0 else 0
        trend_data.append({
            "Date": date,
            "Pass Rate (%)": round(rate, 1),
            "Total": t,
            "Passed": p,
            "Failed": f_count,
        })

    trend_df = pd.DataFrame(trend_data)

    fig = px.line(
        trend_df,
        x="Date",
        y="Pass Rate (%)",
        markers=True,
        hover_data=["Passed", "Failed", "Total"],
    )
    fig.update_layout(
        yaxis_range=[0, 105],
        height=350,
        margin=dict(t=20, b=20),
    )
    fig.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="100%")
    st.plotly_chart(fig, use_container_width=True)

    # Show pass/fail counts over time as stacked bar
    fig2 = px.bar(
        trend_df,
        x="Date",
        y=["Passed", "Failed"],
        color_discrete_map={"Passed": "#28a745", "Failed": "#dc3545"},
        barmode="stack",
    )
    fig2.update_layout(
        height=250,
        margin=dict(t=20, b=20),
        yaxis_title="Test Count",
        legend_title_text="",
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info(
        "Trend data will appear after multiple test runs. "
        "Each run saves a dated copy automatically."
    )
