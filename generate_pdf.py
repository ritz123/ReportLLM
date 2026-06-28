#!/usr/bin/env python3
"""Generate PDF report from MAINTENANCE_FUND_REPORT.md via HTML + Chrome."""

import base64
import subprocess
from pathlib import Path

import markdown

BASE = Path(__file__).parent / "x_analysis"
MD_FILE = BASE / "MAINTENANCE_FUND_REPORT.md"
HTML_FILE = BASE / "MAINTENANCE_FUND_REPORT.html"
PDF_FILE = BASE / "MAINTENANCE_FUND_REPORT.pdf"

CHARTS = [
    ("trend_overview.png", "Trend Overview — Income, Expenses, Balance, Categories"),
    ("utility_trends.png", "Utility & Security Cost Trends"),
]


def img_to_data_uri(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def build_html() -> str:
    md_text = MD_FILE.read_text(encoding="utf-8")
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    chart_html = ""
    for fname, caption in CHARTS:
        p = BASE / fname
        if p.exists():
            chart_html += f"""
            <figure class="chart">
              <img src="{img_to_data_uri(p)}" alt="{caption}">
              <figcaption>{caption}</figcaption>
            </figure>
            """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Maintenance Fund Report</title>
  <style>
    @page {{
      size: A4;
      margin: 18mm 16mm 20mm 16mm;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 10.5pt;
      line-height: 1.45;
      color: #1a1a1a;
      max-width: 100%;
      margin: 0;
      padding: 0;
    }}
    h1 {{
      font-size: 20pt;
      color: #1e3a5f;
      border-bottom: 2px solid #1e3a5f;
      padding-bottom: 6px;
      margin-top: 0;
      page-break-after: avoid;
    }}
    h2 {{
      font-size: 13pt;
      color: #1e3a5f;
      margin-top: 22px;
      border-bottom: 1px solid #ccc;
      padding-bottom: 4px;
      page-break-after: avoid;
    }}
    h3 {{
      font-size: 11pt;
      color: #333;
      margin-top: 16px;
      page-break-after: avoid;
    }}
    p, li {{ margin: 0.4em 0; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0 14px;
      font-size: 9.5pt;
      page-break-inside: avoid;
    }}
    th, td {{
      border: 1px solid #bbb;
      padding: 5px 8px;
      text-align: left;
    }}
    th {{
      background: #e8eef4;
      font-weight: 600;
      color: #1e3a5f;
    }}
    tr:nth-child(even) td {{ background: #f8f9fa; }}
    td:last-child, th:last-child {{ text-align: right; }}
    code, pre {{
      font-family: "Consolas", monospace;
      font-size: 9pt;
      background: #f4f4f4;
    }}
    pre {{
      padding: 8px 10px;
      border-left: 3px solid #1e3a5f;
      white-space: pre-wrap;
      page-break-inside: avoid;
    }}
    hr {{
      border: none;
      border-top: 1px solid #ddd;
      margin: 20px 0;
    }}
    strong {{ color: #1e3a5f; }}
    .charts-section {{
      page-break-before: always;
    }}
    .charts-section h2 {{ margin-top: 0; }}
    figure.chart {{
      margin: 16px 0 24px;
      page-break-inside: avoid;
    }}
    figure.chart img {{
      width: 100%;
      max-width: 100%;
      height: auto;
      border: 1px solid #ddd;
    }}
    figcaption {{
      font-size: 9pt;
      color: #555;
      text-align: center;
      margin-top: 6px;
      font-style: italic;
    }}
    em {{ color: #555; font-size: 9.5pt; }}
  </style>
</head>
<body>
  {body}

  <div class="charts-section">
    <h2>Appendix: Trend Charts</h2>
    {chart_html}
  </div>
</body>
</html>
"""


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = "/usr/bin/google-chrome"
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--print-to-pdf={pdf_path}",
        "--print-to-pdf-no-header",
        f"file://{html_path.resolve()}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Chrome PDF failed: {result.stderr or result.stdout}")
    if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
        raise RuntimeError("PDF was not created or is too small")


def main():
    html = build_html()
    HTML_FILE.write_text(html, encoding="utf-8")
    html_to_pdf(HTML_FILE, PDF_FILE)
    size_kb = PDF_FILE.stat().st_size / 1024
    print(f"PDF written: {PDF_FILE} ({size_kb:.0f} KB)")
    print(f"HTML source: {HTML_FILE}")


if __name__ == "__main__":
    main()
