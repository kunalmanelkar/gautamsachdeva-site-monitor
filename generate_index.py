#!/usr/bin/env python3
"""Generate an index.html that links to the latest report and lists past audits.

Usage:
    python generate_index.py                           # scans reports/ directory
    python generate_index.py --reports-dir reports/     # custom dir
    python generate_index.py --output _site/index.html  # custom output

Designed to run after generate_report.py in the GitHub Actions workflow.
"""

import json
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path

DEFAULT_REPORTS_DIR = Path(__file__).parent / "reports"
DEFAULT_OUTPUT = Path(__file__).parent / "_site" / "index.html"


def build_index(reports_dir: Path, output: Path) -> None:
    # Find all dated report files
    reports = sorted(reports_dir.glob("*.html"), reverse=True)
    if not reports:
        print("No reports found.", file=sys.stderr)
        sys.exit(1)

    latest = reports[0]
    latest_date = latest.stem  # e.g. "2026-04-05"

    # Try to extract summary from the matching JSON if it exists
    results_dir = Path(__file__).parent / "results"
    history_rows = []
    for rpt in reports[:60]:
        date_str = rpt.stem
        json_path = results_dir / f"{date_str}.json"
        passed = failed = skipped = total = 0
        if json_path.exists():
            try:
                with open(json_path) as f:
                    d = json.load(f)
                s = d.get("summary", {})
                passed = s.get("passed", 0)
                failed = s.get("failed", 0)
                skipped = s.get("skipped", 0)
                total = s.get("total", 0)
            except (json.JSONDecodeError, KeyError):
                pass

        # Format date nicely
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            nice_date = dt.strftime("%B %d, %Y")
            day_name = dt.strftime("%A")
        except ValueError:
            nice_date = date_str
            day_name = ""

        if failed > 0:
            status_cls = "fail"
            status_text = f"{failed} issue{'s' if failed != 1 else ''}"
        elif total > 0:
            status_cls = "pass"
            status_text = "all clear"
        else:
            status_cls = "neutral"
            status_text = "no data"

        is_latest = rpt == latest
        history_rows.append(f"""
        <a href="{rpt.name}" class="history-row{' latest' if is_latest else ''}">
          <div class="history-date">
            <span class="history-day">{escape(nice_date)}</span>
            <span class="history-weekday">{escape(day_name)}</span>
          </div>
          <div class="history-stats">
            <span class="stat-pill pass-pill">{passed} passed</span>
            <span class="stat-pill {status_cls}-pill">{escape(status_text)}</span>
            {f'<span class="stat-pill skip-pill">{skipped} skipped</span>' if skipped else ''}
          </div>
          {'<span class="latest-tag">Latest</span>' if is_latest else ''}
        </a>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url={latest.name}">
<title>Site Audit \u2014 gautamsachdeva.com</title>
<style>
  :root {{
    --font: Inter, Roboto, 'Helvetica Neue', Arial, sans-serif;
    --pass: #065F46; --pass-bg: #ECFDF5;
    --fail: #991B1B; --fail-bg: #FEF2F2;
    --accent: #6366F1; --accent-light: #EEF2FF;
    --text1: #111827; --text2: #4B5563; --text3: #9CA3AF;
    --surface: #FFFFFF; --bg: #F9FAFB; --border: #E5E7EB;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: var(--font); background: var(--bg); color: var(--text1);
    -webkit-font-smoothing: antialiased; line-height: 1.5;
  }}
  .container {{ max-width: 640px; margin: 0 auto; padding: 40px 20px; }}
  h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
  .subtitle {{ font-size: 14px; color: var(--text3); margin-bottom: 32px; }}
  .subtitle a {{ color: var(--accent); text-decoration: none; }}
  .subtitle a:hover {{ text-decoration: underline; }}
  .redirect-note {{
    background: var(--accent-light); border: 1px solid #C7D2FE;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 28px;
    font-size: 14px; color: #3730A3;
  }}
  .redirect-note a {{ color: #4338CA; font-weight: 600; }}
  h2 {{
    font-size: 13px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .8px; color: var(--text3); margin-bottom: 12px;
  }}
  .history {{ display: flex; flex-direction: column; gap: 8px; }}
  .history-row {{
    display: flex; align-items: center; gap: 12px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 18px;
    text-decoration: none; color: inherit;
    transition: border-color .15s, box-shadow .15s;
  }}
  .history-row:hover {{ border-color: #C5CAD1; box-shadow: 0 2px 8px rgba(0,0,0,.04); }}
  .history-row.latest {{ border-color: var(--accent); border-width: 2px; }}
  .history-date {{ flex: 1; }}
  .history-day {{ font-size: 15px; font-weight: 600; display: block; }}
  .history-weekday {{ font-size: 12px; color: var(--text3); }}
  .history-stats {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .stat-pill {{
    font-size: 11px; font-weight: 600; padding: 3px 8px;
    border-radius: 100px; white-space: nowrap;
  }}
  .pass-pill {{ background: var(--pass-bg); color: var(--pass); }}
  .fail-pill {{ background: var(--fail-bg); color: var(--fail); }}
  .skip-pill {{ background: #F3F4F6; color: var(--text3); }}
  .neutral-pill {{ background: #F3F4F6; color: var(--text3); }}
  .latest-tag {{
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .5px; padding: 3px 8px; border-radius: 100px;
    background: var(--accent); color: #FFF; flex-shrink: 0;
  }}
  @media (max-width: 500px) {{
    .history-row {{ flex-wrap: wrap; gap: 8px; }}
    .history-stats {{ width: 100%; }}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Site Audit Reports</h1>
  <p class="subtitle">
    Automated monitoring for
    <a href="https://gautamsachdeva.com" target="_blank">gautamsachdeva.com</a>
  </p>

  <div class="redirect-note">
    Redirecting to the latest report\u2026
    <a href="{latest.name}">Click here</a> if it doesn't redirect.
  </div>

  <h2>Audit History</h2>
  <div class="history">
    {"".join(history_rows)}
  </div>
</div>
</body>
</html>"""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(f"Index: {output}  ({len(reports)} reports)")


def main():
    import argparse
    p = argparse.ArgumentParser(description="Generate audit index page.")
    p.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    p.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT))
    args = p.parse_args()
    build_index(Path(args.reports_dir), Path(args.output))


if __name__ == "__main__":
    main()
