# Site Health Monitor — gautamsachdeva.com

Automated Playwright-based test suite that monitors [gautamsachdeva.com](https://gautamsachdeva.com) for regressions, broken links, missing content, SSL issues, and more. Results are displayed in a Streamlit dashboard.

## Quick start

```bash
# Create venv and install
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium

# Run the tests
cd site-monitor && pytest -v

# Launch the dashboard
streamlit run app.py
```

## Project structure

```
app.py                  # Streamlit dashboard
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

The included workflow (`site-monitor.yml`) runs the test suite daily at 8 AM UTC, commits results, and uploads failure screenshots as artifacts. Move it to `.github/workflows/` in your repo to activate it.
