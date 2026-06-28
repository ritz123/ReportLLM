"""Generate matplotlib plots from structured specs."""

import base64
import io
from collections import defaultdict
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np

METRIC_ALIASES = {
    "income": "income",
    "collections": "income",
    "expense": "expense",
    "expenses": "expense",
    "balance": "balance",
    "bank balance": "balance",
    "surplus": "_surplus",
    "deficit": "_surplus",
    "net": "_surplus",
}


def _filter_months(monthly: list, date_from: str | None, date_to: str | None) -> list:
    out = monthly
    if date_from:
        out = [m for m in out if m["label"] >= date_from]
    if date_to:
        out = [m for m in out if m["label"] <= date_to]
    return out


def _group_key(label: str, group_by: str) -> str:
    y, mo = label.split("-")
    if group_by == "year":
        return y
    if group_by == "quarter":
        return f"{y}-Q{(int(mo) - 1) // 3 + 1}"
    return label


def _aggregate(months: list, group_by: str) -> list[dict]:
    if group_by == "month":
        return months
    buckets: dict[str, dict] = {}
    for m in months:
        key = _group_key(m["label"], group_by)
        if key not in buckets:
            buckets[key] = {"label": key, "income": 0, "expense": 0, "balance": 0, "categories": defaultdict(float)}
        b = buckets[key]
        b["income"] += m.get("income") or 0
        b["expense"] += m.get("expense") or 0
        if m.get("balance") is not None:
            b["balance"] = m["balance"]
        for cat, val in (m.get("categories") or {}).items():
            b["categories"][cat] += val
    return sorted(buckets.values(), key=lambda x: x["label"])


def _resolve_metric(months: list, metric: str) -> list[float]:
    key = METRIC_ALIASES.get(metric.lower().strip(), metric)
    if key == "_surplus":
        return [(m.get("income") or 0) - (m.get("expense") or 0) for m in months]
    if key in ("income", "expense", "balance"):
        return [m.get(key) or 0 for m in months]
    return [m.get("categories", {}).get(metric, 0) for m in months]


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def generate_plot(spec: dict, data: dict) -> dict:
    monthly = data["monthly"]
    plot_type = spec.get("type", "line")
    title = spec.get("title", "Maintenance Fund Chart")
    metrics = spec.get("metrics") or ["income", "expense"]
    date_from = spec.get("date_from")
    date_to = spec.get("date_to")
    group_by = spec.get("group_by", "month")

    months = _filter_months(monthly, date_from, date_to)
    if not months:
        raise ValueError("No data in the selected date range")

    fig, ax = plt.subplots(figsize=(10, 5))

    if plot_type == "pie":
        cat_totals = defaultdict(float)
        for m in months:
            for cat, val in (m.get("categories") or {}).items():
                if not metrics or cat in metrics:
                    cat_totals[cat] += val
        if metrics:
            cat_totals = {k: cat_totals[k] for k in metrics if k in cat_totals}
        labels = list(cat_totals.keys())
        values = list(cat_totals.values())
        if not values:
            raise ValueError("No category data for pie chart")
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
        ax.set_title(title)

    elif plot_type == "stacked_bar":
        labels_x = [m["label"] for m in months]
        bottom = np.zeros(len(months))
        colors = plt.cm.Set3(np.linspace(0, 1, len(metrics)))
        for i, metric in enumerate(metrics):
            vals = _resolve_metric(months, metric)
            ax.bar(range(len(months)), vals, bottom=bottom, label=metric, color=colors[i])
            bottom += np.array(vals)
        ax.set_xticks(range(0, len(months), max(1, len(months) // 12)))
        ax.set_xticklabels([labels_x[i] for i in range(0, len(months), max(1, len(months) // 12))], rotation=45, ha="right")
        ax.set_title(title)
        ax.legend(fontsize=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x/1000:.0f}K"))

    else:
        agg = _aggregate(months, group_by)
        labels_x = [m["label"] for m in agg]
        if plot_type == "bar":
            x = np.arange(len(labels_x))
            width = 0.8 / max(len(metrics), 1)
            for i, metric in enumerate(metrics):
                vals = _resolve_metric(agg, metric)
                offset = (i - len(metrics) / 2 + 0.5) * width
                ax.bar(x + offset, vals, width, label=metric)
            ax.set_xticks(x)
            ax.set_xticklabels(labels_x, rotation=45, ha="right", fontsize=8)
            ax.legend(fontsize=8)
        else:
            for metric in metrics:
                vals = _resolve_metric(agg, metric)
                ax.plot(range(len(labels_x)), vals, marker="o", markersize=3, label=metric)
            ax.set_xticks(range(0, len(labels_x), max(1, len(labels_x) // 12)))
            ax.set_xticklabels(
                [labels_x[i] for i in range(0, len(labels_x), max(1, len(labels_x) // 12))],
                rotation=45,
                ha="right",
                fontsize=8,
            )
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
        ax.set_title(title)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x/1000:.0f}K"))

    fig.tight_layout()
    image_b64 = _fig_to_base64(fig)

    period = f"{months[0]['label']} – {months[-1]['label']}"
    return {
        "title": title,
        "caption": f"{title} · {period} · {plot_type}",
        "image_base64": image_b64,
        "spec": spec,
    }
