"""One-page readout: markdown table + a matplotlib chart in the Rex palette. Arms are never blended."""
from __future__ import annotations
import csv
from pathlib import Path

BG, PANEL, GREEN, MAGENTA, AMBER, CYAN, FG = "#0B0F10", "#12191B", "#33FF88", "#FF3EA5", "#FFC247", "#6FE0FF", "#D7E2E4"
ARM_NAME = {"A": "Arm A greenfield", "B": "Arm B mature fix"}


def load(path: Path) -> list[dict]:
    with Path(path).open() as f:
        return list(csv.DictReader(f))


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def summarize(rows: list[dict]) -> list[dict]:
    out = []
    for arm in ("A", "B"):
        cell = {"arm": arm}
        for cond in ("ai", "no_ai"):
            rs = [r for r in rows if r["arm"] == arm and r["condition"] == cond]
            cell[cond] = {"n": len(rs), "solved": sum(int(r["solved"]) for r in rs),
                          "wall_s": _mean([float(r["wall_s"]) for r in rs]),
                          "felt_pct": _mean([float(r["felt_pct"]) for r in rs if r["felt_pct"] != ""])}
        a, b = cell["ai"]["wall_s"], cell["no_ai"]["wall_s"]
        cell["measured_pct"] = round((a / b - 1) * 100, 1) if a and b else None
        out.append(cell)
    return out


def _fmt(x, unit=""):
    return "n/a" if x is None else f"{x:.1f}{unit}"


def markdown(rows: list[dict], title: str = "copilot-two-arm readout") -> str:
    s = summarize(rows)
    lines = [f"# {title}", "", f"Runs: {len(rows)}. Measured change = mean AI wall time / mean no-AI wall time - 1, "
             "computed per arm only when both arms have runs. Negative = faster with AI.", "",
             "| Arm | AI runs (solved) | AI mean wall s | No-AI runs (solved) | No-AI mean wall s | Measured change | AI felt change |",
             "|---|---|---|---|---|---|---|"]
    for c in s:
        ai, no = c["ai"], c["no_ai"]
        lines.append(f"| {ARM_NAME[c['arm']]} | {ai['n']} ({ai['solved']}) | {_fmt(ai['wall_s'])} | {no['n']} ({no['solved']}) | "
                     f"{_fmt(no['wall_s'])} | {_fmt(c['measured_pct'], '%')} | {_fmt(ai['felt_pct'], '%')} |")
    lines += ["", "## Runs", "", "| run | arm | condition | who | tool | wall s | forecast % | felt % | tests | notes |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['run_id']} | {r['arm']} | {r['condition']} | {r['who']} | {r['tool'] or '-'} | {r['wall_s']} | "
                     f"{r['forecast_pct']} | {r['felt_pct']} | {r['tests_passed']}/{r['tests_total']} | {r['notes']} |")
    hw = sorted({r["hardware"] for r in rows}); py = sorted({r["python"] for r in rows})
    lines += ["", f"Hardware: {'; '.join(hw)}. Python: {', '.join(py)}.", "",
              "This is a local measurement. It is not a replication of Peng et al. 2023 or METR 2025."]
    return "\n".join(lines) + "\n"


def chart(rows: list[dict], out: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "monospace", "text.color": FG, "axes.labelcolor": FG,
                         "xtick.color": FG, "ytick.color": FG})
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=BG)
    ax.set_facecolor(PANEL)
    labels, vals, colors = [], [], []
    for r in rows:
        labels.append(f"{r['arm']} {r['condition']} {r['run_id']}")
        vals.append(float(r["wall_s"]))
        colors.append(GREEN if r["condition"] == "ai" else CYAN)
    secs = max(vals + [0]) < 120
    if not secs:
        vals = [v / 60 for v in vals]
    unit = "s" if secs else "min"
    y = range(len(rows))
    ax.barh(list(y), vals, color=colors)
    for i, r in enumerate(rows):
        mark = "PASS" if r["solved"] == "1" else f"FAIL {r['tests_passed']}/{r['tests_total']}"
        ax.text(vals[i], i, f"  {vals[i]:.1f} {unit}  {mark}  felt {r['felt_pct']}%", va="center", color=AMBER, fontsize=8)
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel(f"wall-clock {'seconds' if secs else 'minutes'} (measured)")
    ax.set_xlim(0, max(vals + [1]) * 1.9)
    ax.invert_yaxis()
    for s in ax.spines.values():
        s.set_color(PANEL)
    ax.set_title("copilot-two-arm: measured time per run (green = AI, cyan = no AI)", color=MAGENTA, fontsize=10, loc="left")
    fig.tight_layout()
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=BG); plt.close(fig)
    return out
