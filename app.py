"""Flask UI for cost-variance-analytics.

Run:
    python app.py
Open http://127.0.0.1:7863, upload the JSON exported from internal-accounting.
"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

from core import loader, report

app = Flask(__name__, static_folder="static", template_folder="templates")
HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "data" / "import.json"


def _load() -> dict | None:
    if not DATA_FILE.exists():
        return None
    return loader.load(DATA_FILE)


@app.template_filter("yen")
def f_yen(v):
    try:
        return report.yen(v)
    except Exception:
        return v


@app.template_filter("signed_yen")
def f_signed_yen(v):
    try:
        return report.signed_yen(v)
    except Exception:
        return v


@app.template_filter("pct")
def f_pct(v):
    try:
        return report.pct(v)
    except Exception:
        return v


@app.template_filter("round3")
def f_round(v):
    try:
        return f"{float(v):.3f}"
    except Exception:
        return v


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.files.get("file")
        if f:
            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = json.load(f.stream)
            DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return redirect(url_for("dashboard"))
    return render_template("upload.html", loaded=DATA_FILE.exists())


@app.route("/dashboard")
def dashboard():
    data = _load()
    if not data:
        return redirect(url_for("index"))
    bundle = report.build(data)
    return render_template("dashboard.html", b=bundle)


@app.route("/stats")
def stats_page():
    data = _load()
    if not data:
        return redirect(url_for("index"))
    return render_template("stats.html", b=report.build(data))


@app.route("/pareto")
def pareto_page():
    data = _load()
    if not data:
        return redirect(url_for("index"))
    return render_template("pareto.html", b=report.build(data))


@app.route("/control")
def control_page():
    data = _load()
    if not data:
        return redirect(url_for("index"))
    return render_template("control.html", b=report.build(data))


@app.route("/trend")
def trend_page():
    data = _load()
    if not data:
        return redirect(url_for("index"))
    return render_template("trend.html", b=report.build(data))


@app.route("/reset", methods=["POST"])
def reset():
    if DATA_FILE.exists():
        DATA_FILE.unlink()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7863, debug=False)
