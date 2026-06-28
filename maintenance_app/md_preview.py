"""Discover and render markdown report files."""

import html as html_module
import base64
import re
from datetime import datetime
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

# Directories to scan for *.md reports (non-recursive per dir, plus reports/ subdirs)
SCAN_DIRS = [
    ROOT,
    ROOT / "x_analysis",
    APP_DIR / "reports",
]

SKIP_DIR_NAMES = {".venv", "markitdown", "node_modules", "__pycache__"}
CHART_DIR = ROOT / "x_analysis"
CHART_FILES = [
    ("trend_overview.png", "Trend Overview"),
    ("utility_trends.png", "Utility & Security Cost Trends"),
]

PREVIEW_CSS = """
.md-preview { line-height: 1.55; font-size: 0.95rem; }
.md-preview h1 { font-size: 1.5rem; color: #1e3a5f; border-bottom: 2px solid #1e3a5f; padding-bottom: 6px; margin: 0 0 1rem; }
.md-preview h2 { font-size: 1.15rem; color: #1e3a5f; margin: 1.5rem 0 0.6rem; border-bottom: 1px solid #dde3ec; padding-bottom: 4px; }
.md-preview h3 { font-size: 1rem; color: #333; margin: 1.2rem 0 0.5rem; }
.md-preview p, .md-preview li { margin: 0.4em 0; }
.md-preview ul, .md-preview ol { padding-left: 1.4rem; }
.md-preview table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.85rem; }
.md-preview th, .md-preview td { border: 1px solid #bbb; padding: 5px 8px; text-align: left; }
.md-preview th { background: #e8eef4; color: #1e3a5f; }
.md-preview tr:nth-child(even) td { background: #f8f9fa; }
.md-preview code { background: #f0f4f8; padding: 1px 5px; border-radius: 3px; font-size: 0.88em; }
.md-preview pre { background: #f4f4f4; padding: 10px; border-left: 3px solid #1e3a5f; overflow-x: auto; font-size: 0.85rem; }
.md-preview blockquote { border-left: 3px solid #ccc; margin: 0.8rem 0; padding-left: 12px; color: #555; }
.md-preview hr { border: none; border-top: 1px solid #ddd; margin: 1.5rem 0; }
.md-preview .chart-figure { margin: 1.2rem 0; text-align: center; }
.md-preview .chart-figure img { max-width: 100%; border: 1px solid #ddd; border-radius: 6px; }
.md-preview .chart-figure figcaption { font-size: 0.85rem; color: #555; margin-top: 6px; font-style: italic; }
.md-preview-meta { font-size: 0.8rem; color: #5c6b7f; margin-bottom: 1rem; }
"""


def _is_report_path(path: Path) -> bool:
    if path.suffix.lower() != ".md":
        return False
    if any(part in SKIP_DIR_NAMES or part.startswith(".") for part in path.parts):
        return False
    # skip dependency / project readme noise outside report dirs
    name = path.name.upper()
    if path.parent == ROOT and name in ("README.MD",):
        return False
    return path.is_file()


def list_reports() -> list[dict]:
    found: dict[str, dict] = {}

    for base in SCAN_DIRS:
        if not base.exists():
            continue
        candidates = list(base.glob("*.md"))
        reports_sub = base / "reports"
        if reports_sub.is_dir():
            candidates.extend(reports_sub.glob("*.md"))
        for path in sorted(candidates):
            if not _is_report_path(path):
                continue
            rel = path.relative_to(ROOT).as_posix()
            stat = path.stat()
            found[rel] = {
                "id": rel,
                "name": path.name,
                "path": rel,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }

    return sorted(found.values(), key=lambda x: x["path"])


def resolve_report(report_id: str) -> Path:
    if not report_id or ".." in report_id or report_id.startswith("/"):
        raise ValueError("Invalid report path")
    path = (ROOT / report_id).resolve()
    root_resolved = ROOT.resolve()
    if not str(path).startswith(str(root_resolved)):
        raise ValueError("Report path outside project root")
    if not _is_report_path(path):
        raise ValueError("Report not found or not allowed")
    allowed = {r["id"] for r in list_reports()}
    if report_id not in allowed:
        raise ValueError("Report not in allowed list")
    return path


def _img_data_uri(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _append_charts(html: str, report_path: Path) -> str:
    """Append analysis charts when previewing the main fund report."""
    if report_path.name != "MAINTENANCE_FUND_REPORT.md":
        return html
    figures = []
    for fname, caption in CHART_FILES:
        img_path = CHART_DIR / fname
        if img_path.exists():
            figures.append(
                f'<figure class="chart-figure"><img src="{_img_data_uri(img_path)}" alt="{caption}">'
                f'<figcaption>{caption}</figcaption></figure>'
            )
    if figures:
        html += '<h2>Appendix: Trend Charts</h2>' + "".join(figures)
    return html


def render_markdown_html(md_text: str, title: str = "Preview") -> str:
    """Render markdown string to HTML body (no file path required)."""
    body = markdown.markdown(md_text or "", extensions=["tables", "fenced_code", "nl2br"])
    return f'<div class="md-preview-meta">{title}</div>{body}'


def render_live_report_html(
    title: str,
    summary_markdown: str,
    blocks: list[dict],
    *,
    source_file: str = "",
    period: str = "",
) -> str:
    """Render the in-app live report (summary + AI blocks) as preview HTML."""
    parts = [f"<h1>{html_module.escape(title)}</h1>"]
    if source_file or period:
        meta_bits = [html_module.escape(b) for b in (source_file, period) if b]
        parts.append(f'<p class="md-preview-meta">{" · ".join(meta_bits)}</p>')
    if summary_markdown:
        parts.append(markdown.markdown(summary_markdown, extensions=["tables", "fenced_code", "nl2br"]))
    for block in blocks:
        btype = block.get("type")
        if btype == "text":
            block_title = block.get("title", "")
            if block_title:
                parts.append(f"<h3>{html_module.escape(block_title)}</h3>")
            content = block.get("content", "")
            if content.strip().startswith(("#", "-", "*", "|")):
                parts.append(markdown.markdown(content, extensions=["tables", "fenced_code", "nl2br"]))
            else:
                parts.append(f"<p>{html_module.escape(content)}</p>")
        elif btype == "plot":
            parts.append(f"<h3>{html_module.escape(block.get('title', 'Chart'))}</h3>")
            b64 = block.get("image_base64", "")
            if b64:
                caption = html_module.escape(block.get("caption", ""))
                parts.append(
                    f'<figure class="chart-figure"><img src="data:image/png;base64,{b64}" alt="chart">'
                    f'<figcaption>{caption}</figcaption></figure>'
                )
    return "".join(parts)


def wrap_export_html(title: str, body_html: str) -> str:
    """Full HTML document for export/download."""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{html_module.escape(title)}</title>
<style>{PREVIEW_CSS}
body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
</style></head><body><div class="md-preview">{body_html}</div></body></html>"""


def render_report(report_id: str) -> dict:
    path = resolve_report(report_id)
    md_text = path.read_text(encoding="utf-8")
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "nl2br"])
    body = _append_charts(body, path)
    stat = path.stat()
    meta = (
        f"Source: {report_id} · {stat.st_size:,} bytes · "
        f"updated {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}"
    )
    return {
        "id": report_id,
        "name": path.name,
        "path": report_id,
        "html": f'<div class="md-preview-meta">{meta}</div>{body}',
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def save_uploaded_report(filename: str, content: bytes) -> str | None:
    """Save uploaded .md to reports/ for preview listing."""
    if not filename.lower().endswith(".md"):
        return None
    safe = re.sub(r"[^\w.\-]", "_", Path(filename).name)
    dest_dir = APP_DIR / "reports"
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / safe
    dest.write_bytes(content)
    return f"maintenance_app/reports/{safe}".replace("\\", "/")
