"""CLI: generate a synthetic dataset, run both holdout designs, write results.

    holdout-harness run --seed 20261125 --out results/

Every row and line it writes carries the label "synthetic test data".
"""
import argparse
import csv
import os
import platform
import sys
from collections import defaultdict
from statistics import fmean, stdev

from . import LABEL, __version__
from .bucketing import assign, assign_routes_by_market
from .spillover import cross_bucket_customers, mixed_markets
from .stats import bootstrap_ratio_ci, cuped_adjust, mde, n_per_arm, welch_ci
from .synth import booking_sessions, make_routes, route_panel

FIELDS = ["label", "design", "estimator", "n_treat", "n_control", "unit", "rel_lift",
          "ci_low", "ci_high", "true_rel_lift", "flags", "note"]


def _per_route(rows):
    pre, test, arm = defaultdict(list), defaultdict(list), {}
    for r in rows:
        (test if r["period"] == "test" else pre)[r["route"]].append(r["revenue"])
        arm[r["route"]] = r["arm"]
    routes = sorted(arm)
    return routes, {r: fmean(pre[r]) for r in routes}, {r: fmean(test[r]) for r in routes}, arm


def _row(design, est, nt, nc, unit, lift, lo, hi, true, flags="", note=""):
    return {"label": LABEL, "design": design, "estimator": est, "n_treat": nt, "n_control": nc,
            "unit": unit, "rel_lift": round(lift, 4), "ci_low": "" if lo is None else round(lo, 4),
            "ci_high": "" if hi is None else round(hi, 4), "true_rel_lift": true, "flags": flags,
            "note": note}


def run(seed=20261125, salt="pf-20261121", lift=0.02, macro=0.10, steal=0.04, n_boot=2000):
    out = []
    r2m, base = make_routes(seed)

    # --- Design A: split-route, bucketed by market (clean) ------------------
    arm = assign_routes_by_market(r2m, salt)
    rows = route_panel(seed, r2m, base, arm, lift=lift, macro=macro, steal=steal)
    routes, pre, test, arm = _per_route(rows)
    T = [r for r in routes if arm[r] == "treatment"]
    C = [r for r in routes if arm[r] == "control"]
    flagsA = f"mixed_markets={len(mixed_markets(arm, r2m))}"

    pp = fmean([test[r] for r in T]) / fmean([pre[r] for r in T]) - 1
    out.append(_row("split-route (market-hashed)", "naive pre/post, treated routes only", len(T), 0,
                    "route", pp, None, None, lift, flagsA, "includes the network-wide fare move"))

    w = welch_ci([test[r] for r in T], [test[r] for r in C])
    cm = fmean([test[r] for r in C])
    out.append(_row("split-route (market-hashed)", "holdout diff-in-means, Welch 95% CI", len(T), len(C),
                    "route", w["diff"] / cm, w["ci_low"] / cm, w["ci_high"] / cm, lift, flagsA,
                    "route size dominates variance"))

    # CUPED on log revenue: pre-period route size explains most between-route spread
    import math
    y = [math.log(test[r]) for r in routes]
    x = [math.log(pre[r]) for r in routes]
    adj, theta = cuped_adjust(y, x)
    adj_by = dict(zip(routes, adj))
    wc = welch_ci([adj_by[r] for r in T], [adj_by[r] for r in C])
    out.append(_row("split-route (market-hashed)", "holdout + CUPED (log revenue), Welch 95% CI", len(T), len(C),
                    "route", math.exp(wc["diff"]) - 1, math.exp(wc["ci_low"]) - 1, math.exp(wc["ci_high"]) - 1,
                    lift, flagsA, f"theta={theta:.3f}"))
    resid_sd = stdev(adj)

    # bootstrap on test/pre ratio per route
    ratio = {r: test[r] / pre[r] for r in routes}
    b = bootstrap_ratio_ci([ratio[r] for r in T], [ratio[r] for r in C], n_boot=n_boot, seed=seed)
    out.append(_row("split-route (market-hashed)", "holdout on test/pre ratio, bootstrap 95% CI", len(T), len(C),
                    "route", b["lift"], b["ci_low"], b["ci_high"], lift, flagsA, f"{n_boot} resamples"))

    # --- Design A': same data generator, bucketed by route (leaky) ----------
    arm_bad = {r: assign(r, salt) for r in r2m}
    rows_bad = route_panel(seed, r2m, base, arm_bad, lift=lift, macro=macro, steal=steal)
    routes_b, pre_b, test_b, arm_b = _per_route(rows_bad)
    mixed = mixed_markets(arm_b, r2m)
    Tb = [r for r in routes_b if arm_b[r] == "treatment"]
    Cb = [r for r in routes_b if arm_b[r] == "control"]
    rb = {r: test_b[r] / pre_b[r] for r in routes_b}
    bb = bootstrap_ratio_ci([rb[r] for r in Tb], [rb[r] for r in Cb], n_boot=n_boot, seed=seed)
    out.append(_row("split-route (route-hashed, leaky)", "holdout on test/pre ratio, bootstrap 95% CI",
                    len(Tb), len(Cb), "route", bb["lift"], bb["ci_low"], bb["ci_high"], lift,
                    f"mixed_markets={len(mixed)}", "treated routes take demand from control siblings"))

    # --- Design B: booking cohort, arm hashed per session -------------------
    sess = booking_sessions(seed, salt)
    true_b = round((1.04) * (1 - 0.015) - 1, 4)
    flagged = cross_bucket_customers(sess)
    St = [s["revenue"] for s in sess if s["arm"] == "treatment"]
    Sc = [s["revenue"] for s in sess if s["arm"] == "control"]
    wb = welch_ci(St, Sc)
    cmb = fmean(Sc)
    out.append(_row("booking cohort (session-hashed)", "all sessions, Welch 95% CI", len(St), len(Sc), "session",
                    wb["diff"] / cmb, wb["ci_low"] / cmb, wb["ci_high"] / cmb, true_b,
                    f"cross_bucket_customers={len(flagged)}", "contaminated: some travellers saw both prices"))
    clean = [s for s in sess if s["customer_id"] not in flagged]
    Ct = [s["revenue"] for s in clean if s["arm"] == "treatment"]
    Cc = [s["revenue"] for s in clean if s["arm"] == "control"]
    wcl = welch_ci(Ct, Cc)
    cmc = fmean(Cc)
    out.append(_row("booking cohort (session-hashed)", "flagged customers excluded, Welch 95% CI", len(Ct), len(Cc),
                    "session", wcl["diff"] / cmc, wcl["ci_low"] / cmc, wcl["ci_high"] / cmc, true_b,
                    f"excluded_customers={len(flagged)}", "guard applied"))

    # --- Power ---------------------------------------------------------------
    power = {
        "route_mde_rel_cuped": math.exp(mde(resid_sd, len(T), len(C))) - 1,
        "route_n_per_arm_for_1pct": n_per_arm(resid_sd, math.log(1.01)),
        "session_mde_rel": mde(stdev(Cc), len(Ct), len(Cc)) / cmc,
        "session_n_per_arm_for_1pct": n_per_arm(stdev(Cc), 0.01 * cmc),
    }
    meta = {"routes": len(routes), "markets": len(set(r2m.values())), "sessions": len(sess),
            "mixed_markets_route_hashed": len(mixed), "cross_bucket_customers": len(flagged)}
    return out, power, meta


def write(out, power, meta, outdir, seed, args):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    lines = [f"# holdout-harness {__version__} results ({LABEL})", "",
             f"Every number below is {LABEL}, generated by this harness. None of it is carrier data.", "",
             f"- seed: {seed}  salt: {args.salt}  true lift (synthetic): {args.lift:.2%}  "
             f"network-wide fare move (synthetic): {args.macro:.2%}  spillover steal (synthetic): {args.steal:.2%}",
             f"- python {platform.python_version()} on {platform.platform()}",
             f"- routes: {meta['routes']} in {meta['markets']} markets; sessions: {meta['sessions']}", "",
             "| design | estimator | lift | 95% CI | true | flags |", "|---|---|---|---|---|---|"]
    for r in out:
        ci = f"{r['ci_low']:+.2%} to {r['ci_high']:+.2%}" if r["ci_low"] != "" else "none"
        lines.append(f"| {r['design']} | {r['estimator']} | {r['rel_lift']:+.2%} | {ci} | "
                     f"{float(r['true_rel_lift']):+.2%} | {r['flags']} |")
    lines += ["", "## Power (synthetic test data)",
              f"- route design, CUPED: MDE at 80% power, alpha 0.05 = {power['route_mde_rel_cuped']:.2%}",
              f"- route design, CUPED: routes per arm to detect 1% = {power['route_n_per_arm_for_1pct']}",
              f"- booking cohort: MDE = {power['session_mde_rel']:.2%}",
              f"- booking cohort: sessions per arm to detect 1% = {power['session_n_per_arm_for_1pct']}", ""]
    with open(os.path.join(outdir, "summary.md"), "w") as f:
        f.write("\n".join(lines))
    return "\n".join(lines)


def chart(out, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    bg, panel, green, pink, amber, cyan = "#0B0F10", "#12191B", "#33FF88", "#FF3EA5", "#FFC247", "#6FE0FF"
    plt.rcParams["font.family"] = "monospace"
    labels = ["Pre/post,\ntreated only", "Holdout,\nWelch", "Holdout\n+ CUPED", "Holdout,\nbootstrap",
              "Route-hashed\n(leaky)", "Cohort,\nall sessions", "Cohort,\nguard applied"]
    colors = [pink, cyan, green, green, amber, amber, cyan]
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(panel)
    for i, r in enumerate(out):
        y = r["rel_lift"] * 100
        ax.scatter(i, y, s=70, color=colors[i], zorder=3)
        if r["ci_low"] != "":
            ax.vlines(i, r["ci_low"] * 100, r["ci_high"] * 100, color=colors[i], lw=3, zorder=2)
        ax.hlines(float(r["true_rel_lift"]) * 100, i - 0.35, i + 0.35, color="#8a9a9e", lw=1.2, ls="--")
        ax.annotate(f"{y:+.1f}%", (i, y), textcoords="offset points", xytext=(12, 6), color="#d7e2e4", fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.2", fc=bg, ec="none"), zorder=4)
    ax.axhline(0, color="#3a4548", lw=0.8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, color="#d7e2e4", fontsize=8)
    ax.tick_params(colors="#d7e2e4")
    for s in ax.spines.values():
        s.set_color("#3a4548")
    ax.set_ylabel("Estimated revenue lift, % (95% CI)", color="#d7e2e4")
    ax.set_title("Synthetic test data: one network, seven ways to read the lift (dashed line = true synthetic lift)",
                 color="#ffffff", fontsize=10, loc="left")
    fig.text(0.01, 0.01, f"Source: holdout-harness {__version__}, seed 20261125. Synthetic test data, not carrier data.",
             color="#8a9a9e", fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, facecolor=bg)


def main(argv=None):
    p = argparse.ArgumentParser(prog="holdout-harness", description=f"Holdout harness ({LABEL} demo)")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="generate synthetic data, run both designs, write results")
    r.add_argument("--seed", type=int, default=20261125)
    r.add_argument("--salt", default="pf-20261121")
    r.add_argument("--lift", type=float, default=0.02)
    r.add_argument("--macro", type=float, default=0.10)
    r.add_argument("--steal", type=float, default=0.04)
    r.add_argument("--boot", type=int, default=2000)
    r.add_argument("--out", default="results")
    r.add_argument("--chart", action="store_true", help="also write chart.png (needs matplotlib)")
    a = p.parse_args(argv)
    out, power, meta = run(a.seed, a.salt, a.lift, a.macro, a.steal, a.boot)
    print(write(out, power, meta, a.out, a.seed, a))
    if a.chart:
        chart(out, os.path.join(a.out, "chart.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
