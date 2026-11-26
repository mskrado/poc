import math
import random

import pytest
from holdout_harness.stats import (bootstrap_ratio_ci, cuped_adjust, mde, n_per_arm, t_ppf, welch_ci)


@pytest.mark.parametrize("df,expected", [(1, 12.7062), (10, 2.2281), (30, 2.0423), (1000, 1.9623)])
def test_t_quantiles_match_tables(df, expected):
    assert t_ppf(0.975, df) == pytest.approx(expected, abs=1e-3)


def test_welch_known_example():
    a = [27.5, 21.0, 19.0, 23.6, 17.0, 17.9, 16.9, 20.1, 21.9, 22.6, 23.1, 19.6, 19.0, 21.7, 21.4]
    b = [27.1, 22.0, 20.8, 23.4, 23.4, 23.5, 25.8, 22.0, 24.8, 20.2, 21.9, 22.1, 22.9, 20.5, 24.4]
    w = welch_ci(a, b)
    # reference: scipy.stats.ttest_ind(a, b, equal_var=False) -> t=-2.46, p=0.021, df~24.99
    assert w["df"] == pytest.approx(24.99, abs=0.05)
    assert w["p_value"] == pytest.approx(0.021, abs=0.002)
    assert w["ci_low"] < w["diff"] < w["ci_high"] < 0


def test_welch_covers_true_effect_most_of_the_time():
    rng = random.Random(3)
    hits = 0
    for _ in range(200):
        t = [rng.gauss(1.0, 1) for _ in range(50)]
        c = [rng.gauss(0.0, 1) for _ in range(50)]
        w = welch_ci(t, c)
        hits += w["ci_low"] <= 1.0 <= w["ci_high"]
    assert 180 <= hits <= 200  # nominal 95%


def test_bootstrap_is_seeded_and_brackets_point():
    rng = random.Random(5)
    t = [rng.gauss(103, 10) for _ in range(80)]
    c = [rng.gauss(100, 10) for _ in range(80)]
    b1 = bootstrap_ratio_ci(t, c, n_boot=500, seed=9)
    b2 = bootstrap_ratio_ci(t, c, n_boot=500, seed=9)
    assert b1 == b2
    assert b1["ci_low"] < b1["lift"] < b1["ci_high"]


def test_cuped_reduces_variance():
    rng = random.Random(7)
    x = [rng.gauss(10, 3) for _ in range(500)]
    y = [xi + rng.gauss(0, 0.5) for xi in x]
    adj, theta = cuped_adjust(y, x)
    var = lambda v: sum((a - sum(v) / len(v)) ** 2 for a in v) / (len(v) - 1)
    assert theta == pytest.approx(1.0, abs=0.05)
    assert var(adj) < 0.1 * var(y)


def test_power_helpers_agree():
    n = n_per_arm(sd=1.0, effect=0.2)
    assert n == 393  # 2*(2.8016/0.2)^2 rounded up
    assert mde(1.0, n, n) == pytest.approx(0.2, rel=0.01)
