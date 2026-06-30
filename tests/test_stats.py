"""Verify descriptive stats / t-test / regression / control chart / pareto / variance."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import control_chart, pareto, stats, variance_calc


def _approx(a, b, eps=1e-2):
    assert abs(a - b) < eps, f"{a} vs {b}"


def test_describe_known_sample():
    v = [100, 120, -50, 200]  # 4 期分の材料価格差異想定
    d = stats.describe(v)
    assert d.n == 4
    _approx(d.mean, 92.5)
    _approx(d.stdev, 104.363, eps=0.01)   # 標本SD = sqrt(32675/3)
    assert d.min == -50 and d.max == 200


def test_one_sample_ttest_against_zero():
    v = [100, 120, -50, 200]
    t = stats.one_sample_ttest(v, popmean=0)
    _approx(t.t_statistic, 1.7727, eps=0.01)
    assert 0.0 < t.p_value < 0.3
    assert t.ci95_low < t.mean < t.ci95_high


def test_zscores_zero_when_constant():
    z = stats.zscores([10, 10, 10])
    assert all(abs(x) < 1e-9 for x in z)


def test_linregress_slope():
    xs = [0, 1, 2, 3]
    ys = [10, 20, 30, 40]
    r = stats.linregress(xs, ys)
    _approx(r.slope, 10.0)
    _approx(r.intercept, 10.0)
    _approx(r.r_squared, 1.0)


def test_imr_basic():
    v = [10, 12, 11, 13, 9]
    c = control_chart.i_mr(v)
    _approx(c["mean"], 11.0)
    # MR̄ = (2+1+2+4)/4 = 2.25, UCL_I = 11 + 2.66*2.25 = 16.985
    _approx(c["mr_bar"], 2.25)
    _approx(c["ucl_i"], 11 + 2.66 * 2.25, eps=0.01)


def test_pareto_aggregates_and_sorts():
    rows = [
        {"product_id": "A", "product_name": "A", "category": "材料価格", "process": "x", "value": 100},
        {"product_id": "A", "product_name": "A", "category": "材料価格", "process": "x", "value": 200},
        {"product_id": "A", "product_name": "A", "category": "労務時間", "process": "p", "value": 50},
        {"product_id": "B", "product_name": "B", "category": "材料価格", "process": "y", "value": -30},  # ignored
    ]
    items = pareto.pareto(rows)
    assert len(items) == 2
    assert items[0]["category"] == "材料価格" and items[0]["total"] == 300
    assert items[1]["category"] == "労務時間" and items[1]["total"] == 50
    _approx(items[0]["share"], 300 / 350)
    _approx(items[0]["cum_share"], 300 / 350)
    _approx(items[1]["cum_share"], 1.0)


def test_variance_calc_matches_internal_accounting():
    """Same textbook example as internal-accounting tests."""
    product = {
        "id": "P1", "name": "T", "mode": "detailed", "std_output": 1.0,
        "cost_card": {
            "materials": [{"name": "鋼材A", "std_price": 100, "std_qty": 50}],
            "labors": [], "overhead": {"var_rate": 0, "fixed_budget": 0, "normal_hours": 0},
            "simple_budget": {"total": 0, "material": 0, "labor": 0, "overhead": 0},
        },
    }
    actual = {
        "product_id": "P1", "period": "2026-Q1", "actual_output": 1.0,
        "materials": [{"name": "鋼材A", "actual_price": 110, "actual_qty": 55}],
        "labors": [], "overhead": {"actual_variable": 0, "actual_fixed": 0},
        "simple": {"total": 0, "material": 0, "labor": 0, "overhead": 0},
    }
    r = variance_calc.calc(product, actual)
    by_cat = {l["category"]: l["value"] for l in r["lines"]}
    _approx(by_cat["材料価格"], 550)   # (110-100)*55
    _approx(by_cat["材料数量"], 500)   # (55-50)*100


if __name__ == "__main__":
    test_describe_known_sample()
    test_one_sample_ttest_against_zero()
    test_zscores_zero_when_constant()
    test_linregress_slope()
    test_imr_basic()
    test_pareto_aggregates_and_sorts()
    test_variance_calc_matches_internal_accounting()
    print("OK")
