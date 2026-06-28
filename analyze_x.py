#!/usr/bin/env python3
"""Parse X.md society maintenance ledger and produce trend analysis + charts."""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

MD_PATH = Path(__file__).parent / "X.md"
OUT_DIR = Path(__file__).parent / "x_analysis"
OUT_DIR.mkdir(exist_ok=True)

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

SKIP_SECTIONS = {"amc", "sheet19", "copy of aug 2023", "sheet19_conflict72661679"}


def parse_float(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "-"):
        return None
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_section_header(title: str):
    """Return (year, month_num, label) from section title like 'OCT 2021' or 'Jan 2022'."""
    title = title.strip()
    m = re.match(r"^([A-Za-z]+)\s+(\d{4})$", title)
    if not m:
        return None
    mon_str, year = m.group(1).lower(), int(m.group(2))
    mon = MONTH_MAP.get(mon_str)
    if not mon:
        return None
    label = datetime(year, mon, 1).strftime("%Y-%m")
    return year, mon, label


def parse_row(line: str):
    """Parse markdown table row into cells."""
    if not line.startswith("|"):
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def categorize_expense(desc: str) -> str:
    d = desc.lower()
    if any(k in d for k in ("bescom", "electric", "elec bill", "ebill", "eb line", "eb ")):
        return "Electricity"
    if any(k in d for k in ("water", "bwssb")):
        return "Water"
    if any(k in d for k in ("tara", "security", "mahindra")):
        return "Security / Staff"
    if "garbage" in d or "garabage" in d:
        return "Garbage"
    if "diesel" in d or "diseal" in d:
        return "Diesel / Generator"
    if any(k in d for k in ("lift", "elevator", "amc", "genset", "generator service")):
        return "Lift / AMC"
    if any(k in d for k in ("paint", "lumin", "carpenter", "plumber", "electrician", "gate", "roof", "terrace", "tile", "glass", "gowtham", "gautam")):
        return "Repairs / Capital"
    if any(k in d for k in ("society formation", "bank account", "biometric", "name board", "cctv")):
        return "One-time / Setup"
    if any(k in d for k in ("gardener", "tree", "plant")):
        return "Gardening"
    if any(k in d for k in ("broom", "mop", "clean", "lizol", "shampoo", "phenyl", "phynel", "sanitizer", "bleach", "colin", "hit", "cockroach", "rat")):
        return "Cleaning Supplies"
    return "Other / Misc"


def find_resident_total_row(cells):
    """Find total collections from residents."""
    for i, c in enumerate(cells):
        if c.strip().lower() == "total" and i + 1 < len(cells):
            val = parse_float(cells[i + 1])
            if val and val >= 1000:
                return val
    # Also check pattern: last columns
    for c in reversed(cells):
        v = parse_float(c)
        if v and v >= 10000:
            return v
    return None


def extract_balance(cells):
    for i, c in enumerate(cells):
        cl = c.strip().lower()
        if cl in ("balance", "balance carry forwarded", "bank balance"):
            for j in range(i + 1, len(cells)):
                v = parse_float(cells[j])
                if v is not None:
                    return v
    return None


def closing_balance(month: dict) -> float | None:
    """Prefer bank balance (authoritative); fall back to fund balance."""
    if month.get("bank_balance") is not None:
        return month["bank_balance"]
    return month.get("balance")


def reconcile_monthly_income(months: list[dict], tolerance: float = 100.0) -> list[dict]:
    """
    Fix collections/income using the ledger identity:
        closing = opening + income - expense  =>  income = closing - opening + expense

    Bank balance (when present) and left-side expense totals are treated as authoritative.
    When parsed collections already reconcile with fund balance, they are kept (cash+bank split).
    """
    prev_bank = None
    prev_fund = None

    for month in months:
        expense = month.get("total_expense")
        if expense is None:
            continue

        parsed = month.get("total_income")
        bank_close = month.get("bank_balance")
        fund_close = month.get("balance")

        fund_open = month.get("opening_balance")
        if fund_open is None:
            fund_open = prev_fund
        bank_open = prev_bank if prev_bank is not None else 0.0

        candidates: list[tuple[str, float]] = []
        if bank_close is not None:
            candidates.append(("bank", round(bank_close - bank_open + expense, 2)))
        if fund_close is not None and fund_open is not None:
            candidates.append(("fund", round(fund_close - fund_open + expense, 2)))

        wrongly_expense = parsed is not None and abs(parsed - expense) < 1

        if parsed is not None and not wrongly_expense:
            if any(abs(parsed - val) <= tolerance for _, val in candidates):
                month["income_source"] = "parsed"
            elif candidates:
                # Parsed collections don't reconcile — trust balance + expense (bank first).
                kind, val = candidates[0]
                month["total_income_parsed"] = parsed
                month["total_income"] = val
                month["income_source"] = f"inferred_{kind}"
        elif candidates:
            kind, val = candidates[0]
            if wrongly_expense:
                month["total_income_parsed"] = parsed
            if val > 0:
                month["total_income"] = val
                month["income_source"] = f"inferred_{kind}"
        elif parsed is not None:
            month["income_source"] = "parsed"

        if bank_close is not None:
            prev_bank = bank_close
        if fund_close is not None:
            prev_fund = fund_close

    return months


def finalize_months(months: list[dict]) -> list[dict]:
    """Sort, dedupe by month label, and reconcile income from balance + expense."""
    by_label = {m["label"]: m for m in months}
    ordered = sorted(by_label.values(), key=lambda x: x["label"])
    return reconcile_monthly_income(ordered)


def parse_month_sheet(title: str, rows: list[list[str]]):
    """Parse one monthly sheet from row data (markdown table rows or Excel rows)."""
    title = title.strip().lstrip("#").strip()
    if title.lower() in SKIP_SECTIONS or title.lower().startswith("sheet"):
        return None

    parsed = parse_section_header(title)
    if not parsed:
        return None
    year, mon, label = parsed
    dt = datetime(year, mon, 1)

    expenses = []
    total_expense = None
    total_income = None
    balance = None
    bank_balance = None
    opening_balance = None

    for raw_row in rows:
        cells = [c.strip() for c in raw_row if c is not None]
        if not cells or len(cells) < 2:
            continue
        if cells[0].startswith("---"):
            continue

        col0 = cells[0].strip()
        col0l = col0.lower()
        val1 = parse_float(cells[1]) if len(cells) > 1 else None

        if "balance" in col0l and "previous" in col0l:
            m = re.search(r"(-?\d+(?:\.\d+)?)", col0)
            if m:
                opening_balance = float(m.group(1))
        if col0l in ("bank balance", "bank balance last month"):
            opening_balance = parse_float(cells[1])
        if col0l == "balance carry forwarded" and val1 is not None and opening_balance is None:
            opening_balance = val1

        if col0l == "total" and val1 is not None:
            total_expense = val1

        row_text = " ".join(c.lower() for c in cells)
        if "bank balance" in row_text:
            for i, c in enumerate(cells):
                if c.strip().lower() == "bank balance" and i + 1 < len(cells):
                    bank_balance = parse_float(cells[i + 1])

        bal = extract_balance(cells)
        if bal is not None and "bank balance" not in row_text and col0l != "bank balance":
            balance = bal

        if val1 and val1 > 0 and col0l not in (
            "total", "nan", "balance", "bank balance", "bank balance last month",
            "balance carry forwarded", "cash", "date",
        ):
            if not re.match(r"^\d{3}\s*-\s*", col0):
                if "interest credit" not in col0l and col0l != "date":
                    expenses.append({"desc": col0, "amount": val1, "category": categorize_expense(col0)})

        for i, c in enumerate(cells):
            if re.match(r"^\d{3}\s*-\s*", c.strip()):
                continue
            if c.strip().lower() == "total":
                v = parse_float(cells[i + 1]) if i + 1 < len(cells) else None
                # Collections total is on the right (resident) side — not the left expense Total row.
                if v and v >= 5000 and i > 0:
                    total_income = v

    exp_sum = sum(e["amount"] for e in expenses)
    if total_expense is None:
        total_expense = exp_sum if exp_sum else None

    cat_totals = defaultdict(float)
    for e in expenses:
        cat_totals[e["category"]] += e["amount"]

    return {
        "label": label,
        "title": title,
        "date": dt.isoformat(),
        "year": year,
        "month": mon,
        "total_expense": total_expense,
        "total_income": total_income,
        "balance": balance,
        "bank_balance": bank_balance,
        "opening_balance": opening_balance,
        "expense_count": len(expenses),
        "categories": dict(cat_totals),
        "expenses": expenses,
    }


def parse_md(path: Path):
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"\n## ", text)
    months = []

    for sec in sections:
        if not sec.strip():
            continue
        lines = sec.strip().split("\n")
        title = lines[0].strip().lstrip("#").strip()
        rows = []
        for line in lines[1:]:
            cells = parse_row(line)
            if cells:
                rows.append(cells)
        month = parse_month_sheet(title, rows)
        if month:
            months.append(month)

    return finalize_months(months)


def plot_trends(months):
    labels = [m["label"] for m in months]
    dates = [datetime.fromisoformat(m["date"]) for m in months]

    expenses = [m["total_expense"] or 0 for m in months]
    income = [m["total_income"] or 0 for m in months]
    bank = [m["bank_balance"] if m["bank_balance"] is not None else m["balance"] for m in months]

    # Filter to months with at least some data
    valid_idx = [i for i, m in enumerate(months) if (m["total_expense"] or m["total_income"] or m["bank_balance"] or m["balance"])]

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle("Residential Society Maintenance Fund — Trends (Oct 2021 – Present)", fontsize=14, fontweight="bold")

    # 1. Income vs Expenses
    ax = axes[0, 0]
    x = np.arange(len(labels))
    w = 0.35
    ax.bar(x - w/2, income, w, label="Collections (Income)", color="#2ecc71", alpha=0.85)
    ax.bar(x + w/2, expenses, w, label="Expenses", color="#e74c3c", alpha=0.85)
    ax.set_title("Monthly Income vs Expenses")
    ax.set_ylabel("Amount (₹)")
    ax.legend(fontsize=8)
    ax.set_xticks(x[::3])
    ax.set_xticklabels([labels[i] for i in range(0, len(labels), 3)], rotation=45, ha="right", fontsize=7)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x/1000:.0f}K"))

    # 2. Bank balance trend
    ax = axes[0, 1]
    bank_vals = [b if b is not None else np.nan for b in bank]
    ax.plot(dates, bank_vals, "o-", color="#3498db", linewidth=2, markersize=4)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.fill_between(dates, bank_vals, 0, where=[(v or 0) >= 0 for v in bank_vals], alpha=0.15, color="#3498db")
    ax.fill_between(dates, bank_vals, 0, where=[(v or 0) < 0 for v in bank_vals], alpha=0.15, color="#e74c3c")
    ax.set_title("Fund Balance Over Time")
    ax.set_ylabel("Balance (₹)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=7)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x/1000:.0f}K"))

    # 3. Expense category stacked area (aggregate by year-quarter for readability)
    ax = axes[1, 0]
    all_cats = sorted({c for m in months for c in m["categories"]})
    cat_colors = plt.cm.Set3(np.linspace(0, 1, len(all_cats)))
    bottom = np.zeros(len(months))
    for ci, cat in enumerate(all_cats):
        vals = [m["categories"].get(cat, 0) for m in months]
        ax.bar(range(len(months)), vals, bottom=bottom, label=cat, color=cat_colors[ci], width=1.0)
        bottom += np.array(vals)
    ax.set_title("Expense Breakdown by Category")
    ax.set_ylabel("Amount (₹)")
    ax.set_xticks(range(0, len(months), 3))
    ax.set_xticklabels([labels[i] for i in range(0, len(months), 3)], rotation=45, ha="right", fontsize=7)
    ax.legend(fontsize=6, loc="upper left", ncol=2)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x/1000:.0f}K"))

    # 4. Net surplus/deficit per month
    ax = axes[1, 1]
    net = [(m["total_income"] or 0) - (m["total_expense"] or 0) for m in months]
    colors = ["#2ecc71" if n >= 0 else "#e74c3c" for n in net]
    ax.bar(range(len(months)), net, color=colors, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Monthly Surplus / Deficit (Income − Expenses)")
    ax.set_ylabel("Net (₹)")
    ax.set_xticks(range(0, len(months), 3))
    ax.set_xticklabels([labels[i] for i in range(0, len(months), 3)], rotation=45, ha="right", fontsize=7)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x/1000:.0f}K"))

    plt.tight_layout()
    chart_path = OUT_DIR / "trend_overview.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()

    # Utility bill trends
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    elec = [m["categories"].get("Electricity", 0) for m in months]
    water = [m["categories"].get("Water", 0) for m in months]
    security = [m["categories"].get("Security / Staff", 0) for m in months]

    ax = axes[0]
    ax.plot(dates, elec, "o-", label="Electricity (BESCOM)", color="#f39c12", markersize=3)
    ax.plot(dates, water, "s-", label="Water (BWSSB)", color="#3498db", markersize=3)
    ax.set_title("Utility Bill Trends")
    ax.set_ylabel("Amount (₹)")
    ax.legend(fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=7)

    ax = axes[1]
    ax.plot(dates, security, "o-", label="Security / Tara Salary", color="#9b59b6", markersize=3)
    ax.set_title("Security Staff Cost Trend")
    ax.set_ylabel("Amount (₹)")
    ax.legend(fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=7)

    plt.tight_layout()
    util_path = OUT_DIR / "utility_trends.png"
    fig.savefig(util_path, dpi=150, bbox_inches="tight")
    plt.close()

    return chart_path, util_path


def compute_observations(months):
    obs = []
    valid = [m for m in months if m["total_expense"] and m["total_income"]]

    if not valid:
        return obs

    # Avg metrics
    avg_exp = np.mean([m["total_expense"] for m in valid])
    avg_inc = np.mean([m["total_income"] for m in valid])
    obs.append(f"Average monthly expenses: ₹{avg_exp:,.0f}; average collections: ₹{avg_inc:,.0f}")

  # Deficit months
    deficits = [m for m in valid if m["total_income"] < m["total_expense"]]
    obs.append(f"{len(deficits)}/{len(valid)} months ran a deficit ({100*len(deficits)/len(valid):.0f}%)")

    # Biggest expense months
    top_exp = sorted(valid, key=lambda m: m["total_expense"], reverse=True)[:5]
    obs.append("Highest expense months: " + ", ".join(f"{m['title']} (₹{m['total_expense']:,.0f})" for m in top_exp))

    # Electricity trend
    early = [m for m in months if m["label"] <= "2022-06"]
    late = [m for m in months if m["label"] >= "2024-01"]
    early_elec = np.mean([m["categories"].get("Electricity", 0) for m in early if m["categories"].get("Electricity")])
    late_elec = np.mean([m["categories"].get("Electricity", 0) for m in late if m["categories"].get("Electricity")])
    if early_elec and late_elec:
        pct = 100 * (late_elec - early_elec) / early_elec
        obs.append(f"Electricity bills dropped sharply: avg ₹{early_elec:,.0f} (2021–mid-2022) → ₹{late_elec:,.0f} (2024+), {pct:+.0f}% change")

    # Maintenance fee evolution
    early_inc = [m["total_income"] for m in months if "2021" in m["label"] or m["label"].startswith("2022-0")]
    late_inc = [m["total_income"] for m in months if m["label"] >= "2024-01" and m["total_income"]]
    if early_inc and late_inc:
        obs.append(f"Monthly collections changed from ~₹{np.mean(early_inc):,.0f} (2021–early 2022) to ~₹{np.mean(late_inc):,.0f} (2024+) — fees stabilized at ₹3,500/unit with occasional partial payments")

    # Bank balance
    bank_months = [m for m in months if m["bank_balance"] is not None]
    if bank_months:
        peak = max(bank_months, key=lambda m: m["bank_balance"])
        latest = bank_months[-1]
        obs.append(f"Peak bank balance: ₹{peak['bank_balance']:,.0f} ({peak['title']}); latest recorded: ₹{latest['bank_balance']:,.0f} ({latest['title']})")

    # Capital spikes
    capital_months = [(m["title"], sum(v for k, v in m["categories"].items() if k in ("Repairs / Capital", "One-time / Setup", "Lift / AMC")))
                      for m in months]
    capital_spikes = sorted(capital_months, key=lambda x: x[1], reverse=True)[:3]
    obs.append("Major capital/one-time spend months: " + ", ".join(f"{t} (₹{v:,.0f})" for t, v in capital_spikes if v > 5000))

    # Negative balance periods
    neg = [m for m in months if (m["balance"] is not None and m["balance"] < 0) or (m["bank_balance"] is not None and m["bank_balance"] < 0)]
    if neg:
        obs.append(f"Fund went negative in {len(neg)} month(s): " + ", ".join(m["title"] for m in neg[:5]))

    # Aug 2022 anomaly - low collections
    aug22 = next((m for m in months if m["label"] == "2022-08"), None)
    if aug22 and aug22["total_income"] and aug22["total_income"] < 45000:
        obs.append(f"Aug 2022 anomaly: collections dropped to ₹{aug22['total_income']:,.0f} (Nishant paid only ₹350) while expenses were low — fund surplus jumped to ₹{aug22['balance']:,.0f}")

    # Dec 2022 bank account opening
    dec22 = next((m for m in months if m["label"] == "2022-12"), None)
    if dec22:
        obs.append("Dec 2022: Society opened bank account (₹10,000) and raised maintenance to ₹6,000/unit — transition from cash to formal banking")

    # May 2023 glass project
    may23 = next((m for m in months if m["label"] == "2023-05"), None)
    if may23:
        obs.append(f"May 2023: Major glass/carpentry project (~₹60K to Gowtham) caused largest single-month expense spike (₹{may23['total_expense']:,.0f})")

    return obs


def main():
    months = parse_md(MD_PATH)
    chart1, chart2 = plot_trends(months)
    observations = compute_observations(months)

    # Category totals all-time
    all_cats = defaultdict(float)
    for m in months:
        for cat, val in m["categories"].items():
            all_cats[cat] += val

    summary = {
        "months_parsed": len(months),
        "date_range": f"{months[0]['label']} to {months[-1]['label']}",
        "observations": observations,
        "category_totals": dict(sorted(all_cats.items(), key=lambda x: -x[1])),
        "monthly": [{
            "label": m["label"],
            "income": m["total_income"],
            "expense": m["total_expense"],
            "balance": m["bank_balance"] if m["bank_balance"] is not None else m["balance"],
            "categories": m["categories"],
        } for m in months],
    }

    json_path = OUT_DIR / "analysis.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Parsed {len(months)} months ({summary['date_range']})")
    print(f"Charts: {chart1}, {chart2}")
    print(f"JSON: {json_path}")
    print("\n=== KEY OBSERVATIONS ===")
    for i, o in enumerate(observations, 1):
        print(f"{i}. {o}")
    print("\n=== CATEGORY TOTALS (all time) ===")
    for cat, val in summary["category_totals"].items():
        print(f"  {cat}: ₹{val:,.0f}")


if __name__ == "__main__":
    main()
