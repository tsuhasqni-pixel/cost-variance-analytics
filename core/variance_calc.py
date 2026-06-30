"""Variance computation — mirror of internal-accounting/core/variance.py.

Operates on plain dicts loaded from the JSON export (no dataclasses).
Sign convention: positive = unfavourable.
"""
from __future__ import annotations


def _std_qty_for_output(per_unit: float, std_output: float, actual_output: float) -> float:
    if std_output <= 0:
        return 0.0
    return per_unit / std_output * actual_output


def calc_detailed(product: dict, actual: dict) -> dict:
    cc = product.get("cost_card", {}) or {}
    std_output = float(product.get("std_output", 1))
    out = float(actual.get("actual_output", 1))
    lines = []
    total_actual = 0.0
    total_standard = 0.0

    std_mats = {m["name"]: m for m in cc.get("materials", [])}
    act_mats = {m["name"]: m for m in actual.get("materials", [])}
    for name in dict.fromkeys(list(std_mats) + list(act_mats)):
        s = std_mats.get(name, {"std_price": 0, "std_qty": 0})
        a = act_mats.get(name, {"actual_price": 0, "actual_qty": 0})
        sq = _std_qty_for_output(s["std_qty"], std_output, out)
        price_var = (a["actual_price"] - s["std_price"]) * a["actual_qty"]
        qty_var = (a["actual_qty"] - sq) * s["std_price"]
        lines.append({"name": f"材料価格差異 ({name})", "category": "材料価格", "process": name, "value": price_var})
        lines.append({"name": f"材料数量差異 ({name})", "category": "材料数量", "process": name, "value": qty_var})
        total_actual += a["actual_price"] * a["actual_qty"]
        total_standard += s["std_price"] * sq

    std_labs = {l["process"]: l for l in cc.get("labors", [])}
    act_labs = {l["process"]: l for l in actual.get("labors", [])}
    total_act_hours = 0.0
    total_std_hours = 0.0
    for name in dict.fromkeys(list(std_labs) + list(act_labs)):
        s = std_labs.get(name, {"std_rate": 0, "std_hours": 0})
        a = act_labs.get(name, {"actual_rate": 0, "actual_hours": 0})
        sh = _std_qty_for_output(s["std_hours"], std_output, out)
        rate_var = (a["actual_rate"] - s["std_rate"]) * a["actual_hours"]
        time_var = (a["actual_hours"] - sh) * s["std_rate"]
        lines.append({"name": f"労務賃率差異 ({name})", "category": "労務賃率", "process": name, "value": rate_var})
        lines.append({"name": f"労務時間差異 ({name})", "category": "労務時間", "process": name, "value": time_var})
        total_actual += a["actual_rate"] * a["actual_hours"]
        total_standard += s["std_rate"] * sh
        total_act_hours += a["actual_hours"]
        total_std_hours += sh

    oh = cc.get("overhead", {}) or {}
    act_oh = actual.get("overhead", {}) or {}
    var_rate = oh.get("var_rate", 0)
    fixed_budget = oh.get("fixed_budget", 0)
    normal_hours = oh.get("normal_hours", 0)
    std_fixed_rate = (fixed_budget / normal_hours) if normal_hours else 0
    voh_budget = act_oh.get("actual_variable", 0) - var_rate * total_act_hours
    voh_eff = var_rate * (total_act_hours - total_std_hours)
    foh_budget = act_oh.get("actual_fixed", 0) - fixed_budget
    foh_vol = fixed_budget - std_fixed_rate * total_std_hours
    lines.append({"name": "変動OH予算差異", "category": "変動OH予算", "process": "OH", "value": voh_budget})
    lines.append({"name": "変動OH能率差異", "category": "変動OH能率", "process": "OH", "value": voh_eff})
    lines.append({"name": "固定OH予算差異", "category": "固定OH予算", "process": "OH", "value": foh_budget})
    lines.append({"name": "固定OH操業度差異", "category": "固定OH操業度", "process": "OH", "value": foh_vol})

    total_actual += act_oh.get("actual_variable", 0) + act_oh.get("actual_fixed", 0)
    total_standard += var_rate * total_std_hours + std_fixed_rate * total_std_hours
    return {
        "product_id": product["id"], "period": actual["period"], "mode": "detailed",
        "lines": lines,
        "total_actual": total_actual, "total_standard": total_standard,
        "total_variance": total_actual - total_standard,
    }


def calc_simple(product: dict, actual: dict) -> dict:
    sb = ((product.get("cost_card") or {}).get("simple_budget") or {})
    sa = actual.get("simple") or {}
    lines = []
    if sb.get("material") or sa.get("material"):
        lines.append({"name": "材料費差異", "category": "材料費", "process": "—",
                      "value": (sa.get("material", 0)) - (sb.get("material", 0))})
    if sb.get("labor") or sa.get("labor"):
        lines.append({"name": "労務費差異", "category": "労務費", "process": "—",
                      "value": (sa.get("labor", 0)) - (sb.get("labor", 0))})
    if sb.get("overhead") or sa.get("overhead"):
        lines.append({"name": "経費差異", "category": "経費", "process": "—",
                      "value": (sa.get("overhead", 0)) - (sb.get("overhead", 0))})
    actual_total = sa.get("total") or (sa.get("material", 0) + sa.get("labor", 0) + sa.get("overhead", 0))
    budget_total = sb.get("total") or (sb.get("material", 0) + sb.get("labor", 0) + sb.get("overhead", 0))
    lines.append({"name": "総差異", "category": "総差異", "process": "—",
                  "value": actual_total - budget_total})
    return {
        "product_id": product["id"], "period": actual["period"], "mode": "simple",
        "lines": lines, "total_actual": actual_total, "total_standard": budget_total,
        "total_variance": actual_total - budget_total,
    }


def calc(product: dict, actual: dict) -> dict:
    if product.get("mode") == "simple":
        return calc_simple(product, actual)
    return calc_detailed(product, actual)


def calc_all(data: dict) -> list[dict]:
    """For each (product, actual) pair, compute variance and tag with metadata."""
    reports = []
    for actual in data["actuals"]:
        p = data["products_by_id"].get(actual["product_id"])
        if not p:
            continue
        r = calc(p, actual)
        r["product_name"] = p.get("name", actual["product_id"])
        reports.append(r)
    return reports


def long_form(reports: list[dict]) -> list[dict]:
    """Flatten variance reports into one row per (product, period, category)."""
    rows = []
    for r in reports:
        for line in r["lines"]:
            rows.append({
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "period": r["period"],
                "mode": r["mode"],
                "category": line["category"],
                "process": line.get("process", ""),
                "value": line["value"],
            })
    return rows
