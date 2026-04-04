"""F9: Audio players load, episode search, Patreon links on podcast page."""

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
