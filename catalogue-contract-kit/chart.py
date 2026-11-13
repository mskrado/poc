"""One chart from results/results.csv: per check, stores passing on both runs, out of 20."""
import csv
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rexcat.run import CHECK_COLUMNS

BG, PANEL, GREEN, MAGENTA, AMBER, CYAN = "#0B0F10", "#12191B", "#33FF88", "#FF3EA5", "#FFC247", "#6FE0FF"
LABELS = {"robots_ai": "(a) robots.txt lets 5 AI agents in",
          "product_text_html": "(b) product text in raw HTML",
          "price_html": "(c) price in raw HTML",
          "schema_complete": "(d) Product JSON-LD complete",
          "category_lists_5": "(e) category page lists >=5",
          "served_unfamiliar": "(f) served to unfamiliar crawler"}

OUT = Path(__file__).resolve().parent / "results"
rows = list(csv.DictReader(open(OUT / "results.csv")))
runs = {}
for r in rows:
    runs.setdefault(r["store"], {})[r["run"]] = r
n = len(runs)
ts = {k: sorted(r["timestamp_utc"] for r in rows if r["run"] == k) for k in ("1", "2")}

counts = {}
for c in CHECK_COLUMNS:
    k = Counter()
    for s in runs.values():
        a, b = s["1"][c], s["2"][c]
        k["changed" if a != b else a] += 1
    counts[c] = k

plt.rcParams["font.family"] = "monospace"
fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150)
fig.patch.set_facecolor(BG)
ax.set_facecolor(PANEL)
order = CHECK_COLUMNS[::-1]
y = range(len(order))
segs = [("pass", GREEN, "pass on both runs"), ("fail", MAGENTA, "fail on both runs"),
        ("changed", AMBER, "changed between runs"), ("could-not-judge", CYAN, "could not judge (store unreadable or no page found)")]
left = [0] * len(order)
for key, col, lab in segs:
    vals = [counts[c][key] for c in order]
    ax.barh(list(y), vals, left=left, color=col, height=0.62, label=lab, edgecolor=PANEL)
    for i, v in enumerate(vals):
        if v:
            ax.text(left[i] + v / 2, i, str(v), ha="center", va="center", color=BG, fontsize=10, fontweight="bold")
    left = [l + v for l, v in zip(left, vals)]
ax.set_yticks(list(y))
ax.set_yticklabels([LABELS[c] for c in order], color="#E6F2EE", fontsize=10)
ax.set_xlim(0, n)
ax.set_xticks(range(0, n + 1, 5))
ax.tick_params(colors="#9FB3AD")
ax.set_xlabel(f"stores (n={n})", color="#9FB3AD")
for s in ax.spines.values():
    s.set_visible(False)
ax.grid(axis="x", color="#22302F", linewidth=0.8)
ax.set_axisbelow(True)
ax.set_title(f"Catalogue contract checks: stores passing on both runs, out of {n}", color="#E6F2EE",
             fontsize=12.5, loc="left", pad=14)
ax.legend(loc="upper center", bbox_to_anchor=(0.42, -0.13), ncol=4, frameon=False, fontsize=8.5,
          labelcolor="#E6F2EE")
d = ts["1"][0][:10]
fig.text(0.01, 0.015, f"Source: Rex Circuit run, {d}: run 1 {ts['1'][0][11:16]}-{ts['1'][-1][11:16]} UTC, "
         f"run 2 {ts['2'][0][11:16]}-{ts['2'][-1][11:16]} UTC. n={n} public apparel stores, one product + one category page each.",
         color="#9FB3AD", fontsize=7.8)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(OUT / "rex-catalogue-checks-chart.png", facecolor=BG)
print({c: dict(counts[c]) for c in CHECK_COLUMNS})
