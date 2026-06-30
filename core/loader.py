"""Load and normalise an internal-accounting JSON export.

Expected shape (see internal-accounting/core/models.py):
{
  "products": [Product, ...],
  "actuals":  [Actual, ...],
  "cvp":      CVPScenario | null
}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load(source: str | Path | dict) -> dict:
    if isinstance(source, dict):
        data = source
    else:
        path = Path(source)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    products = data.get("products") or []
    actuals = data.get("actuals") or []
    cvp = data.get("cvp")
    products_by_id = {p["id"]: p for p in products}
    return {"products": products, "actuals": actuals, "cvp": cvp,
            "products_by_id": products_by_id}


def actuals_for(data: dict, product_id: str) -> list[dict]:
    return [a for a in data["actuals"] if a["product_id"] == product_id]
