"""Root conftest — saves dated copies of test results for historical tracking."""

import shutil
from datetime import datetime
from pathlib import Path

import pytest


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """After test run, copy latest.json to a dated file for trend tracking.

    Uses trylast=True to run after pytest-json-report writes the file.
    """
    results_dir = Path(__file__).parent / "results"
    latest = results_dir / "latest.json"
    if latest.exists():
        date_str = datetime.now().strftime("%Y-%m-%d")
        dated_file = results_dir / f"{date_str}.json"
        shutil.copy2(latest, dated_file)
