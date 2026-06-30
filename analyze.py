"""CLI: read an internal-accounting JSON export, write a single HTML report."""
from __future__ import annotations

import argparse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core import loader, report


def build_html(input_path: Path, output_path: Path) -> None:
    data = loader.load(input_path)
    bundle = report.build(data)
    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["yen"] = report.yen
    env.filters["signed_yen"] = report.signed_yen
    env.filters["pct"] = report.pct
    env.filters["round3"] = lambda v: f"{float(v):.3f}"
    tpl = env.get_template("standalone.html")
    output_path.write_text(tpl.render(b=bundle), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="internal-accounting JSON export")
    ap.add_argument("--out", type=Path, default=Path("report.html"))
    args = ap.parse_args()
    build_html(args.input, args.out)
    print(f"[OK] wrote {args.out}")


if __name__ == "__main__":
    main()
