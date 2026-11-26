"""Stdlib-only statistics: Welch CI, bootstrap CI, CUPED, power/MDE."""
import math
import random
from statistics import NormalDist, fmean, variance


# --- Student t quantile via regularised incomplete beta (no SciPy) ---------
def _betacf(a, b, x, itmax=300, eps=3e-14):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c
        c = c if abs(c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c
        c = c if abs(c) > 1e-300 else 1e-300
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def t_cdf(t, df):
    x = df / (df + t * t)
    tail = 0.5 * _betai(df / 2.0, 0.5, x)
    return 1.0 - tail if t > 0 else tail


def t_ppf(p, df):
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --- Estimators --------------------------------------------------------------
def welch_ci(treat, control, alpha=0.05):
    """Difference in means (treat - control) with a Welch t interval.

    Returns dict: diff, se, df, ci_low, ci_high, p_value.
    """
    nt, nc = len(treat), len(control)
    if nt < 2 or nc < 2:
        raise ValueError("need at least 2 units per arm")
    mt, mc = fmean(treat), fmean(control)
    vt, vc = variance(treat), variance(control)
    se = math.sqrt(vt / nt + vc / nc)
    df = (vt / nt + vc / nc) ** 2 / ((vt / nt) ** 2 / (nt - 1) + (vc / nc) ** 2 / (nc - 1))
    q = t_ppf(1 - alpha / 2, df)
    diff = mt - mc
    p = 2 * (1 - t_cdf(abs(diff) / se, df)) if se > 0 else 0.0
    return {"diff": diff, "se": se, "df": df, "ci_low": diff - q * se, "ci_high": diff + q * se, "p_value": p}


def bootstrap_ratio_ci(treat, control, n_boot=2000, alpha=0.05, seed=0):
    """Percentile bootstrap CI for relative lift mean(treat)/mean(control) - 1.

    Resamples whole units (routes or sessions), which keeps within-unit
    correlation intact. Seeded, so it reproduces exactly.
    """
    rng = random.Random(seed)
    point = fmean(treat) / fmean(control) - 1
    stats = []
    for _ in range(n_boot):
        t = [treat[rng.randrange(len(treat))] for _ in treat]
        c = [control[rng.randrange(len(control))] for _ in control]
        stats.append(fmean(t) / fmean(c) - 1)
    stats.sort()
    lo = stats[int(math.floor(alpha / 2 * n_boot))]
    hi = stats[int(math.ceil((1 - alpha / 2) * n_boot)) - 1]
    return {"lift": point, "ci_low": lo, "ci_high": hi}


def cuped_adjust(y, x):
    """CUPED: y - theta * (x - mean(x)), theta = cov(x, y) / var(x).

    x is the same unit's pre-period metric. Pool both arms when you call it so
    theta is not fitted per arm.
    """
    mx, my = fmean(x), fmean(y)
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / (len(x) - 1)
    theta = cov / variance(x)
    return [b - theta * (a - mx) for a, b in zip(x, y)], theta


# --- Power --------------------------------------------------------------------
def mde(sd, n_treat, n_control, alpha=0.05, power=0.8):
    """Minimum detectable absolute effect for a two-sided test (normal approx)."""
    z = NormalDist()
    return (z.inv_cdf(1 - alpha / 2) + z.inv_cdf(power)) * sd * math.sqrt(1 / n_treat + 1 / n_control)


def n_per_arm(sd, effect, alpha=0.05, power=0.8):
    """Units needed per arm (equal split) to detect an absolute `effect`."""
    z = NormalDist()
    k = z.inv_cdf(1 - alpha / 2) + z.inv_cdf(power)
    return math.ceil(2 * (k * sd / effect) ** 2)
