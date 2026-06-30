"""Descriptive stats, Z-score, one-sample t-test, linear regression."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median, pstdev, stdev


@dataclass
class Descriptive:
    n: int
    mean: float
    median: float
    stdev: float        # sample stdev (n-1); 0 when n < 2
    min: float
    max: float
    sum: float


def describe(values: list[float]) -> Descriptive:
    if not values:
        return Descriptive(0, 0, 0, 0, 0, 0, 0)
    return Descriptive(
        n=len(values),
        mean=mean(values),
        median=median(values),
        stdev=stdev(values) if len(values) > 1 else 0.0,
        min=min(values),
        max=max(values),
        sum=sum(values),
    )


def zscores(values: list[float]) -> list[float]:
    d = describe(values)
    if d.stdev == 0:
        return [0.0 for _ in values]
    return [(v - d.mean) / d.stdev for v in values]


@dataclass
class TTestResult:
    n: int
    mean: float
    stdev: float
    t_statistic: float
    p_value: float
    ci95_low: float
    ci95_high: float
    significant: bool


def one_sample_ttest(values: list[float], popmean: float = 0.0, alpha: float = 0.05) -> TTestResult:
    """Two-sided one-sample t-test against ``popmean``.

    Uses scipy if available; otherwise falls back to manual computation with a
    Student-t CDF approximation. ``significant`` is True when p < alpha.
    """
    n = len(values)
    if n < 2:
        return TTestResult(n, mean(values) if values else 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, False)
    m = mean(values)
    sd = stdev(values)
    se = sd / (n ** 0.5)
    if se == 0:
        # All values equal — perfect departure or perfect match
        t = float("inf") if m != popmean else 0.0
        p = 0.0 if m != popmean else 1.0
        return TTestResult(n, m, sd, t, p, m, m, p < alpha)
    t = (m - popmean) / se
    try:
        from scipy import stats as sp_stats  # type: ignore
        p = float(sp_stats.t.sf(abs(t), df=n - 1) * 2)
        tcrit = float(sp_stats.t.ppf(1 - alpha / 2, df=n - 1))
    except Exception:
        # crude normal approximation when scipy is unavailable
        from math import erf, sqrt
        p = 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))
        tcrit = 1.96  # large-n fallback
    ci_low = m - tcrit * se
    ci_high = m + tcrit * se
    return TTestResult(n, m, sd, t, p, ci_low, ci_high, p < alpha)


@dataclass
class RegressionResult:
    n: int
    slope: float
    intercept: float
    r_squared: float
    p_value: float


def linregress(xs: list[float], ys: list[float]) -> RegressionResult:
    n = len(xs)
    if n < 2 or n != len(ys):
        return RegressionResult(n, 0.0, ys[0] if ys else 0.0, 0.0, 1.0)
    try:
        from scipy import stats as sp_stats  # type: ignore
        r = sp_stats.linregress(xs, ys)
        return RegressionResult(n, float(r.slope), float(r.intercept), float(r.rvalue) ** 2, float(r.pvalue))
    except Exception:
        mx = sum(xs) / n
        my = sum(ys) / n
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        slope = sxy / sxx if sxx else 0.0
        intercept = my - slope * mx
        r2 = (sxy ** 2) / (sxx * syy) if sxx and syy else 0.0
        return RegressionResult(n, slope, intercept, r2, 1.0)
