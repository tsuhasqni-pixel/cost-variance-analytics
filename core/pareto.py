"""ABC / Pareto analysis on unfavourable variances."""
from __future__ import annotations


def pareto(rows: list[dict]) -> list[dict]:
    """Aggregate variance rows by (product, category), sort by unfavourable
    magnitude descending, and append cumulative-share percent.

    Only positive values (= unfavourable) are aggregated; favourable cancellations
    are ignored to highlight cost overruns. Returns a list with keys::

        product_id, product_name, category, total, share, cum_share, rank
    """
    agg: dict[tuple[str, str], dict] = {}
    for r in rows:
        if r["value"] <= 0:
            continue
        key = (r["product_id"], r["category"])
        e = agg.setdefault(key, {
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "category": r["category"],
            "total": 0.0,
        })
        e["total"] += r["value"]
    items = sorted(agg.values(), key=lambda x: x["total"], reverse=True)
    grand = sum(x["total"] for x in items) or 1.0
    cum = 0.0
    for i, x in enumerate(items, 1):
        x["share"] = x["total"] / grand
        cum += x["share"]
        x["cum_share"] = cum
        x["rank"] = i
    return items
