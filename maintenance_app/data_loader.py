"""Load and summarize maintenance fund data from X.md or uploaded sessions."""

import csv
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analyze_x import parse_md, compute_observations  # noqa: E402
from session_store import get_dataset as _get_session_dataset, set_default_session  # noqa: E402

MD_PATH = ROOT / "X.md"
JSON_PATH = ROOT / "x_analysis" / "analysis.json"


def months_to_dataset(months: list, observations: list | None = None) -> dict:
    if observations is None:
        observations = compute_observations(months)
    all_cats = defaultdict(float)
    for m in months:
        for cat, val in m["categories"].items():
            all_cats[cat] += val
    return {
        "months_parsed": len(months),
        "date_range": f"{months[0]['label']} to {months[-1]['label']}" if months else "",
        "observations": observations,
        "category_totals": dict(all_cats),
        "monthly": [
            {
                "label": m["label"],
                "title": m["title"],
                "income": m["total_income"],
                "expense": m["total_expense"],
                "balance": m["bank_balance"] if m["bank_balance"] is not None else m["balance"],
                "categories": m["categories"],
            }
            for m in months
        ],
    }


def load_default(refresh: bool = False) -> dict:
    if refresh or not JSON_PATH.exists():
        months = parse_md(MD_PATH)
        payload = months_to_dataset(months)
        payload["source_file"] = "X.md"
        JSON_PATH.parent.mkdir(exist_ok=True)
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        payload.setdefault("source_file", "X.md")
    set_default_session(payload, "X.md")
    return payload


def get_dataset(refresh: bool = False, session_id: str | None = None) -> dict:
    if refresh and not session_id:
        return load_default(refresh=True)
    try:
        return _get_session_dataset(session_id)
    except KeyError:
        return load_default(refresh=refresh)


def build_summary(data: dict) -> dict:
    monthly = data["monthly"]
    cats = data["category_totals"]
    total_spend = sum(cats.values())
    incomes = [m["income"] or 0 for m in monthly]
    expenses = [m["expense"] or 0 for m in monthly]
    balances = [m["balance"] for m in monthly if m["balance"] is not None]

    deficits = sum(1 for m in monthly if (m["income"] or 0) < (m["expense"] or 0))
    avg_income = sum(incomes) / len(incomes) if incomes else 0
    avg_expense = sum(expenses) / len(expenses) if expenses else 0

    top_cats = sorted(cats.items(), key=lambda x: -x[1])[:5]
    peak_bal = max(balances) if balances else 0
    latest_bal = balances[-1] if balances else 0
    source = data.get("source_file", "ledger")

    return {
        "title": "Residential Society Maintenance Fund — Summary",
        "period": data.get("date_range", ""),
        "months": data.get("months_parsed", 0),
        "source_file": source,
        "avg_monthly_income": round(avg_income),
        "avg_monthly_expense": round(avg_expense),
        "total_spend": round(total_spend),
        "deficit_months": deficits,
        "peak_balance": round(peak_bal),
        "latest_balance": round(latest_bal),
        "top_categories": [{"name": k, "amount": round(v), "pct": round(100 * v / total_spend, 1)} for k, v in top_cats],
        "observations": data.get("observations", []),
        "markdown": _summary_markdown(data, avg_income, avg_expense, total_spend, deficits, peak_bal, latest_bal, top_cats, source),
    }


def _summary_markdown(data, avg_income, avg_expense, total_spend, deficits, peak_bal, latest_bal, top_cats, source):
    lines = [
        f"# Maintenance Fund Summary\n",
        f"**Source:** {source}",
        f"**Period:** {data.get('date_range', 'N/A')} ({data.get('months_parsed', 0)} months)\n",
        f"\n## Key Metrics\n",
        f"- Average monthly collections: **₹{avg_income:,.0f}**",
        f"- Average monthly expenses: **₹{avg_expense:,.0f}**",
        f"- Total spend (all time): **₹{total_spend:,.0f}**",
        f"- Months with deficit: **{deficits}**",
        f"- Peak bank balance: **₹{peak_bal:,.0f}**",
        f"- Latest balance: **₹{latest_bal:,.0f}**",
        f"\n## Top Expense Categories\n",
    ]
    for name, amt in top_cats:
        pct = 100 * amt / total_spend if total_spend else 0
        lines.append(f"- {name}: ₹{amt:,.0f} ({pct:.1f}%)")
    lines.append("\n## Notable Observations\n")
    for obs in data.get("observations", []):
        lines.append(f"- {obs}")
    return "\n".join(lines)


def context_for_ai(data: dict, report_summary: str = "") -> str:
    monthly = data["monthly"]
    cats = data["category_totals"]
    sample = monthly[:3] + monthly[-3:] if len(monthly) > 6 else monthly
    report_ctx = f"\nCurrent report summary excerpt:\n{report_summary[:2000]}\n" if report_summary else ""

    return f"""You are an analyst for a residential society maintenance fund in Bangalore (8 units).
Source file: {data.get('source_file', 'ledger')}
Date range: {data.get('date_range')}. Months: {data.get('months_parsed')}.
{report_ctx}
Category totals (INR): {json.dumps({k: round(v) for k, v in cats.items()})}

Monthly fields per record: label (YYYY-MM), income, expense, balance, categories (dict).

Sample months: {json.dumps(sample, default=str)}

Available plot metrics:
- income, expense, balance (monthly totals)
- categories: {list(cats.keys())}

When the user asks for a chart/plot/graph, include a fenced JSON block:

```plot
{{"type": "line|bar|pie|stacked_bar", "title": "...", "metrics": ["income"] or ["Electricity","Water"], "date_from": "2021-10", "date_to": "2026-06", "group_by": "month|quarter|year"}}
```

When the user asks to update/add to the report (analysis, section, observation, executive summary text), you MUST include a fenced block:

```report
{{"action": "add_section", "title": "Section Title", "content": "Markdown or plain text for the report"}}
```

Other report actions (use the same ```report``` fence):
- {{"action": "add_observation", "content": "bullet point text"}}
- {{"action": "add_text", "content": "paragraph to append"}}

Always use ```report``` (not bare ```json```) for report updates so they are applied automatically.
You may include both plot and report blocks in one response.
If no plot or report update needed, answer normally.
Use INR (₹) formatting. Be concise and specific to this society's data."""


def cleaned_dataset_payload(data: dict) -> dict:
    """Structured dataset for export (parsed ledger, normalized fields)."""
    return {
        "source_file": data.get("source_file", ""),
        "date_range": data.get("date_range", ""),
        "months_parsed": data.get("months_parsed", 0),
        "observations": data.get("observations", []),
        "category_totals": data.get("category_totals", {}),
        "monthly": data.get("monthly", []),
    }


def export_cleaned_json(data: dict) -> str:
    return json.dumps(cleaned_dataset_payload(data), indent=2, ensure_ascii=False)


def export_cleaned_csv(data: dict) -> str:
    """One row per month; category columns sorted alphabetically."""
    payload = cleaned_dataset_payload(data)
    monthly = payload["monthly"]
    categories = sorted(payload["category_totals"].keys())
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["label", "title", "income", "expense", "balance", *categories])
    for month in monthly:
        cats = month.get("categories") or {}
        writer.writerow(
            [
                month.get("label", ""),
                month.get("title", ""),
                month.get("income", ""),
                month.get("expense", ""),
                month.get("balance", ""),
                *[cats.get(cat, "") for cat in categories],
            ]
        )
    return out.getvalue()


def export_data_filename(data: dict, ext: str) -> str:
    source = (data.get("source_file") or "ledger").replace("/", "_").replace("\\", "_")
    stem = source.rsplit(".", 1)[0] if "." in source else source
    return f"cleaned_data_{stem}.{ext}"
