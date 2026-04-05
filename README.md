# Site Health Monitor — gautamsachdeva.com

Automated Playwright test suite (74 checks) that monitors [gautamsachdeva.com](https://gautamsachdeva.com) for regressions, broken links, missing content, SSL issues, and more. Results are turned into a self-contained HTML audit report that volunteers can open in any browser.

## How it works

1. **GitHub Actions runs 74 Playwright tests daily** at 8 AM UTC.
2. Tests results are converted into a **volunteer-friendly HTML report** — plain English errors, "How to check this" instructions, clickable links.
3. The report is **deployed to GitHub Pages** — one permanent URL always shows the latest audit, with a history of past audits.
4. Volunteers open the link, work through manual checks, add notes, and download their completed report.

## Live audit

Once deployed, the latest audit is always at:
```
https://<your-github-username>.github.io/gautamsachdeva-site-monitor/
```

The index page auto-redirects to the latest report and shows a history of all past audits.

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium

# Run the tests
pytest site-monitor/ -v

# Generate the report
python generate_report.py          # -> report.html
open report.html
```

## Project structure

```
generate_report.py      # Generates a single HTML audit report from test results
generate_index.py       # Generates index.html with history of all audits
results/                # JSON test reports (latest + dated archives)
reports/                # Dated HTML reports (committed by CI)
site-monitor/
  pytest.ini            # pytest configuration
  conftest.py           # Root conftest — archives results by date
  tests/
    conftest.py         # Shared fixtures (viewports, link checker, SSL)
    test_homepage.py
    test_navigation.py
    test_content_pages.py
    test_podcast_players.py
    test_payment_pages.py
    test_forms.py
    test_external_links.py
    test_technical.py
```

## GitHub Actions + Pages

The workflow (`.github/workflows/site-monitor.yml`):
1. Runs 74 Playwright tests daily
2. Generates a dated HTML report (`reports/2026-04-05.html`)
3. Generates an index page with audit history
4. Commits results and reports to the repo
5. Deploys to GitHub Pages

To enable: go to repo Settings > Pages > Source > **GitHub Actions**.
