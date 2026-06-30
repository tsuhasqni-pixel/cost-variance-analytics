"""Individuals & Moving-Range (I-MR) control chart.

For each (product, category) series of variances over time, compute the centre
line (mean), moving range (|x_t − x_{t-1}|), and the standard SPC limits::

    UCL_I = X̄ + E2 × MR̄          E2 = 2.66 (for n=2 MR)
    LCL_I = X̄ − E2 × MR̄
    UCL_R = D4 × MR̄                D4 = 3.267 (for n=2)
    LCL_R = D3 × MR̄                D3 = 0

X̄-R charts are also available for product-level subgrouping when n ≥ 2 readings
per period exist, but the typical variance dataset has one reading per period
per product, so I-MR is the usual chart.
"""
from __future__ import annotations

E2 = 2.66
D4 = 3.267
D3 = 0.0


def i_mr(values: list[float]) -> dict:
    """Compute centre lines and UCL/LCL for the I and MR charts."""
    n = len(values)
    if n == 0:
        return {"n": 0}
    mean_x = sum(values) / n
    mrs = [abs(values[i] - values[i - 1]) for i in range(1, n)]
    mr_bar = (sum(mrs) / len(mrs)) if mrs else 0.0
    return {
        "n": n,
        "values": list(values),
        "mr_values": mrs,
        "mean": mean_x,
        "mr_bar": mr_bar,
        "ucl_i": mean_x + E2 * mr_bar,
        "lcl_i": mean_x - E2 * mr_bar,
        "ucl_r": D4 * mr_bar,
        "lcl_r": D3 * mr_bar,
        "out_of_control_indices": [i for i, v in enumerate(values)
                                   if v > mean_x + E2 * mr_bar or v < mean_x - E2 * mr_bar],
    }
