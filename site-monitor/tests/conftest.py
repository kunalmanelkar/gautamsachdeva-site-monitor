"""Shared fixtures for site monitoring tests."""

import ssl
import socket
import urllib.request
from urllib.error import URLError, HTTPError

import pytest

BASE_URL = "https://gautamsachdeva.com"

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 720},
    "mobile": {"width": 390, "height": 844},
    "tablet": {"width": 810, "height": 1080},
}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Override default browser context args with longer timeout."""
    return {
        **browser_context_args,
        "ignore_https_errors": False,
    }


@pytest.fixture()
def desktop_page(page):
    """Page with desktop viewport."""
    page.set_viewport_size(VIEWPORTS["desktop"])
    page.set_default_timeout(30_000)
    page.set_default_navigation_timeout(60_000)
    return page


@pytest.fixture()
def mobile_page(page):
    """Page with mobile (iPhone 14) viewport."""
    page.set_viewport_size(VIEWPORTS["mobile"])
    page.set_default_timeout(30_000)
    page.set_default_navigation_timeout(60_000)
    return page


@pytest.fixture()
def tablet_page(page):
    """Page with tablet viewport."""
    page.set_viewport_size(VIEWPORTS["tablet"])
    page.set_default_timeout(30_000)
    page.set_default_navigation_timeout(60_000)
    return page


def check_link_status(url: str, timeout: int = 15) -> int:
    """Check HTTP status of a URL via HEAD request.

    Returns the HTTP status code, or -1 for connection errors.
    Skips mailto:, tel:, and javascript: links by returning 0.
    """
    if not url or url.startswith(("mailto:", "tel:", "javascript:", "#")):
        return 0

    try:
        req = urllib.request.Request(url, method="HEAD", headers={
            "User-Agent": "Mozilla/5.0 (compatible; SiteMonitor/1.0)"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except HTTPError as e:
        return e.code
    except (URLError, socket.timeout, OSError):
        # Retry with GET — some servers reject HEAD
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SiteMonitor/1.0)"
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except HTTPError as e:
            return e.code
        except (URLError, socket.timeout, OSError):
            return -1


def get_ssl_expiry_days(hostname: str = "gautamsachdeva.com") -> int:
    """Return the number of days until the SSL certificate expires."""
    from datetime import datetime, timezone

    ctx = ssl.create_default_context()
    with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
        s.settimeout(10)
        s.connect((hostname, 443))
        cert = s.getpeername() and s.getpeercert()

    expiry_str = cert["notAfter"]  # e.g. 'Apr  5 23:59:59 2025 GMT'
    expiry_dt = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z").replace(
        tzinfo=timezone.utc
    )
    return (expiry_dt - datetime.now(timezone.utc)).days
