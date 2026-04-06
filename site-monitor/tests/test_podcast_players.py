"""F9: Audio players load, episode search, Patreon links on podcast page."""

import time

import pytest
from playwright.sync_api import Page, expect

from .conftest import BASE_URL


def test_podcast_page_audio_players(desktop_page: Page):
    """Podcast page has actual audio player elements — platform links don't count."""
    desktop_page.goto(f"{BASE_URL}/podcasts/", wait_until="domcontentloaded")
    desktop_page.wait_for_timeout(2000)  # Allow audio widgets to initialize

    # Only count actual audio/player elements and episode links
    audio_elements = desktop_page.locator("audio")
    player_widgets = desktop_page.locator("[class*='player'], [class*='audio']")
    episode_links = desktop_page.locator("a[href*='PatreonPodcastsGenerator']")

    # Episode navigation controls (Starter Starter Player plugin uses pp- prefix)
    nav_buttons = desktop_page.locator(
        "button.pp-prev-btn, button.pp-next-btn, button.pp-list-btn, "
        "button:has-text('Previous'), button:has-text('Next')"
    )

    has_audio = audio_elements.count() > 0
    has_player = player_widgets.count() > 0
    has_episodes = episode_links.count() >= 3
    has_nav = nav_buttons.count() > 0

    assert has_audio or has_player or has_episodes or has_nav, (
        f"Podcast page has no audio players or episode content. "
        f"audio={audio_elements.count()}, players={player_widgets.count()}, "
        f"episodes={episode_links.count()}, nav_buttons={nav_buttons.count()}"
    )


def test_podcast_page_episode_list(desktop_page: Page):
    """Podcast page has episode search or episode links — no content-length fallback."""
    desktop_page.goto(f"{BASE_URL}/podcasts/", wait_until="domcontentloaded")
    desktop_page.wait_for_timeout(2000)

    # Podcast player search — actual input is type="text" with placeholder "Search Episodes"
    search_input = desktop_page.locator(
        "input[placeholder*='Search Episodes'], "
        "input[title*='Search Podcast'], "
        "input[placeholder*='search' i], input[type='search']"
    )

    # Episode links to PatreonPodcastsGenerator
    episode_links = desktop_page.locator("a[href*='PatreonPodcastsGenerator']")

    has_search = search_input.count() > 0
    has_episodes = episode_links.count() >= 3

    assert has_search or has_episodes, (
        f"Podcast page lacks episode search input and has only "
        f"{episode_links.count()} episode links (expected search OR >= 3 links)"
    )


def test_podcast_play_pause_controls(desktop_page: Page):
    """Podcast player has visible play/pause, skip, and navigation controls."""
    desktop_page.goto(f"{BASE_URL}/podcasts/", wait_until="networkidle")

    # The podcast player plugin initializes asynchronously via JS.
    # Wait generously for the player container, then for controls inside it.
    try:
        desktop_page.wait_for_selector(
            ".pp-podcast, [class*='pp-podcast']",
            timeout=15_000,
        )
    except Exception:
        pass
    desktop_page.wait_for_timeout(5000)

    # Play/Pause button — try multiple selector strategies
    play_pause = desktop_page.locator(
        ".ppjs__playpause-button button, "
        ".ppjs__playpause-button, "
        "[class*='playpause'] button, "
        "button[aria-label*='play' i], "
        "button[aria-label*='pause' i]"
    )

    # Fallback: any button inside a podcast player container
    if play_pause.count() == 0:
        play_pause = desktop_page.locator(
            ".pp-podcast button, [class*='pp-podcast'] button"
        )

    assert play_pause.count() > 0, (
        "No play/pause button found on podcast page"
    )

    # Verify at least one play/pause button is visible
    visible_pp = False
    for i in range(play_pause.count()):
        if play_pause.nth(i).is_visible():
            visible_pp = True
            break
    assert visible_pp, "Play/pause button exists but is not visible"

    # Skip/navigation controls
    skip_controls = desktop_page.locator(
        ".ppjs__skip-backward-button button, .ppjs__jump-forward-button button, "
        "button.pp-prev-btn, button.pp-next-btn"
    )
    assert skip_controls.count() >= 2, (
        f"Only {skip_controls.count()} skip/nav controls found (expected >= 2)"
    )

    # Audio element exists
    audio = desktop_page.locator("audio")
    assert audio.count() > 0, "No <audio> element found on podcast page"

    # Audio has a valid source
    audio_src = audio.first.evaluate("""el => {
        const source = el.querySelector('source');
        return source ? source.src : el.src;
    }""")
    assert audio_src and len(audio_src) > 10, (
        f"Audio element has no valid source: {audio_src}"
    )


def test_podcast_page_loads_on_mobile(mobile_page: Page):
    """Podcast page loads within acceptable time on mobile viewport."""
    start = time.time()
    resp = mobile_page.goto(
        f"{BASE_URL}/podcasts/", wait_until="domcontentloaded"
    )
    domcontent_time = time.time() - start

    assert resp and resp.status == 200, (
        f"/podcasts/ returned HTTP {resp.status if resp else 'no response'} on mobile"
    )

    # Wait for player widgets to initialize
    mobile_page.wait_for_timeout(3000)

    # Audio player or episode content should be present on mobile
    audio = mobile_page.locator("audio")
    players = mobile_page.locator("[class*='player'], [class*='audio']")
    episodes = mobile_page.locator("a[href*='PatreonPodcastsGenerator']")

    assert audio.count() > 0 or players.count() > 0 or episodes.count() >= 3, (
        "Podcast page has no audio content on mobile viewport"
    )

    # DOMContentLoaded should be under 15s even on mobile
    assert domcontent_time < 15, (
        f"Podcast page DOMContentLoaded took {domcontent_time:.1f}s on mobile (expected < 15s)"
    )
