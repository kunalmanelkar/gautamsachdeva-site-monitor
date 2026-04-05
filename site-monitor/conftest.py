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
    # pytest-json-report writes results/latest.json relative to CWD,
    # which is the project root when running `pytest site-monitor/`.
    # Check both locations for robustness.
    candidates = [
        Path.cwd() / "results" / "latest.json",           # CWD (project root)
        Path(__file__).parent / "results" / "latest.json", # site-monitor/results/
    ]
    for latest in candidates:
        if latest.exists():
            results_dir = latest.parent
            date_str = datetime.now().strftime("%Y-%m-%d")
            dated_file = results_dir / f"{date_str}.json"
            shutil.copy2(latest, dated_file)
            break
