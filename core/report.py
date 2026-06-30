"""Roll up loaded data into a single analysis bundle for templates."""
from __future__ import annotations

from collections import defaultdict

from . import control_chart, pareto, stats, variance_calc


def build(data: dict) -> dict:
    reports = variance_calc.calc_all(data)
    rows = variance_calc.long_form(reports)

    # Group by (product, category) → time series of variance values
    series: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    for r in rows:
        series[(r["product_id"], r["category"])].append((r["period"], r["value"]))
    for k, v in series.items():
        v.sort(key=lambda x: x[0])

    descriptive = []
    for (pid, cat), points in series.items():
        values = [p[1] for p in points]
        d = stats.describe(values)
        t = stats.one_sample_ttest(values, popmean=0.0)
        product_name = next((r["product_name"] for r in rows if r["product_id"] == pid), pid)
        descriptive.append({
            "product_id": pid, "product_name": product_name, "category": cat,
            "n": d.n, "mean": d.mean, "median": d.median, "stdev": d.stdev,
            "min": d.min, "max": d.max, "sum": d.sum,
            "t_stat": t.t_statistic, "p_value": t.p_value,
            "ci95_low": t.ci95_low, "ci95_high": t.ci95_high,
            "significant": t.significant,
        })
    descriptive.sort(key=lambda x: (x["product_name"], x["category"]))

    pareto_items = pareto.pareto(rows)

    control_charts = []
    for (pid, cat), points in series.items():
        if len(points) < 2:
            continue
        product_name = next((r["product_name"] for r in rows if r["product_id"] == pid), pid)
        chart = control_chart.i_mr([p[1] for p in points])
        chart["product_id"] = pid
        chart["product_name"] = product_name
        chart["category"] = cat
        chart["periods"] = [p[0] for p in points]
        control_charts.append(chart)
    control_charts.sort(key=lambda x: (x["product_name"], x["category"]))

    trends = []
    for (pid, cat), points in series.items():
        if len(points) < 2:
            continue
        ys = [p[1] for p in points]
        xs = list(range(len(ys)))
        reg = stats.linregress(xs, ys)
        product_name = next((r["product_name"] for r in rows if r["product_id"] == pid), pid)
        trends.append({
            "product_id": pid, "product_name": product_name, "category": cat,
            "n": reg.n, "slope": reg.slope, "intercept": reg.intercept,
            "r_squared": reg.r_squared, "p_value": reg.p_value,
            "periods": [p[0] for p in points], "values": ys,
        })
    trends.sort(key=lambda x: (x["product_name"], x["category"]))

    # Sensitivity to CVP (rough): assume cm_ratio from saved CVP scenario
    sensitivity = None
    cvp = data.get("cvp")
    if cvp and cvp.get("lines"):
        total_sales = sum((l.get("unit_price", 0) * l.get("quantity", 0)) for l in cvp["lines"])
        total_vc = sum((l.get("unit_variable", 0) * l.get("quantity", 0)) for l in cvp["lines"])
        cm = total_sales - total_vc
        cm_ratio = (cm / total_sales) if total_sales else 0
        unfav_total = sum(r["value"] for r in rows if r["value"] > 0)
        # Naive: 1% unfavourable variance ↑ → operating income ↓ by unfav_total * 1%
        sensitivity = {
            "total_sales": total_sales,
            "cm_ratio": cm_ratio,
            "unfav_total": unfav_total,
            "income_impact_1pct": unfav_total * 0.01,
        }

    return {
        "products": data["products"],
        "actuals": data["actuals"],
        "reports": reports,
        "rows": rows,
        "descriptive": descriptive,
        "pareto": pareto_items,
        "control_charts": control_charts,
        "trends": trends,
        "sensitivity": sensitivity,
    }


def yen(v) -> str:
    n = float(v or 0)
    sign = "-" if n < 0 else ""
    return f"{sign}¥{abs(n):,.0f}"


def signed_yen(v) -> str:
    n = float(v or 0)
    if n > 0:
        return f"+¥{n:,.0f}"
    if n < 0:
        return f"-¥{-n:,.0f}"
    return "¥0"


def pct(v) -> str:
    return f"{float(v or 0) * 100:,.2f}%"
