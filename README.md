# Site Health Monitor — gautamsachdeva.com

Automated Playwright test suite (74 checks) that monitors [gautamsachdeva.com](https://gautamsachdeva.com) for regressions, broken links, missing content, SSL issues, and more.  Results are turned into a self-contained HTML audit report that volunteers can open in any browser to track their manual checks.

## Quick start

```bash
# Create venv and install
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium

# Run the tests
cd site-monitor && pytest -v && cd ..

# Generate the audit report
python generate_report.py          # -> report.html
open report.html                   # open in browser
```

## Volunteer workflow

1. Someone runs the tests (or GitHub Actions runs them daily).
2. `python generate_report.py` produces `report.html`.
3. Share `report.html` with the volunteer (email, Slack, etc.).
4. The volunteer opens it in their browser and works through each task:
   - **Automated checks** are pre-verified — shown as a collapsed summary.
   - **Manual checks** are interactive checkboxes with "How to check this" instructions.
   - There's a notes field per section for anything to flag.
5. Progress is auto-saved in the browser (localStorage).
6. The volunteer clicks **Download Report** to save a timestamped copy with their notes baked in.

## Project structure

```
generate_report.py      # Generates report.html from test results
report.html             # Generated — the audit report volunteers use
site-monitor/
  conftest.py           # Root conftest — copies results to dated files
  pytest.ini            # pytest configuration
  requirements.txt      # Pinned test-only deps (used by CI)
  UPTIMEROBOT_SETUP.md  # UptimeRobot integration guide
  results/              # JSON test reports (latest + dated)
  screenshots/          # Failure screenshots from Playwright
  tests/
    conftest.py         # Shared fixtures (viewport helpers, link checker, SSL)
    test_homepage.py
    test_navigation.py
    test_content_pages.py
    test_podcast_players.py
    test_payment_pages.py
    test_forms.py
    test_external_links.py
    test_technical.py
```

## GitHub Actions

The included workflow (`.github/workflows/site-monitor.yml`) runs the test suite daily at 8 AM UTC, commits results, and uploads failure screenshots as artifacts.
