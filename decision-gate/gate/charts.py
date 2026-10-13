"""Charts in the Builder Lab terminal palette. Numbers come from summary.json only."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

BG, PANEL, GREEN, MAGENTA, AMBER, CYAN = "#0B0F10", "#12191B", "#33FF88", "#FF3EA5", "#FFC247", "#6FE0FF"
FG = "#D8E1E3"
plt.rcParams.update({
    "font.family": "monospace", "font.monospace": ["DejaVu Sans Mono"], "figure.facecolor": BG,
    "axes.facecolor": PANEL, "axes.edgecolor": "#2A3538", "axes.labelcolor": FG, "text.color": FG,
    "xtick.color": FG, "ytick.color": FG, "axes.titlecolor": FG, "savefig.facecolor": BG,
    "axes.grid": True, "grid.color": "#22302F", "grid.linestyle": ":",
})


def _foot(fig, text):
    fig.text(0.01, 0.01, text, fontsize=7.5, color="#7E8C8F", ha="left", va="bottom")


def tokens_time(s, path):
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.2))
    metrics = [("input_tokens_per_ticket", "input tokens / ticket"),
               ("output_tokens_per_ticket", "output tokens / ticket"),
               ("wall_ms_per_ticket", "wall time / ticket (s)")]
    for ax, (k, title) in zip(axes, metrics):
        vals = [s["chat"][k], s["gate"][k]]
        if k == "wall_ms_per_ticket":
            vals = [v / 1000 for v in vals]
        bars = ax.bar(["chat", "gate"], vals, color=[MAGENTA, GREEN], width=0.55)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.1f}" if v < 100 else f"{v:,.0f}",
                    ha="center", va="bottom", fontsize=10, color=FG)
        ax.set_title(title, fontsize=10)
        ax.set_ylim(0, max(vals) * 1.2)
        ax.grid(axis="x", visible=False)
    fig.suptitle(f"$ triage {s['tickets']} Bitext tickets: chat paragraph vs decision gate", color=GREEN,
                 fontsize=12, x=0.01, ha="left")
    _foot(fig, f"chat={s['run']['chat_model']}  gate={s['run']['gate_model']} via /v1/systemone  "
               f"| CPU only, 8 vCPU | measured")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def cost_accuracy(s, path):
    fm = s["frontier_modelled"]
    lc = s["local_cost_modelled"]
    items = [
        ("local chat", lc["chat_total_usd"], MAGENTA, f"acc {s['chat']['category_accuracy']:.0%} (measured)", False),
        ("local gate", lc["gate_total_usd"], GREEN, f"acc {s['gate']['category_accuracy']:.0%} (measured)", False),
    ]
    routed_n = fm["tickets_routed_to_frontier_by_gate"]
    if routed_n:
        for m, v in fm["gate_routed_to_frontier_usd"].items():
            items.append((f"gate + {routed_n} routed\n-> {m}", lc["gate_total_usd"] + v, CYAN, "frontier part modelled", True))
    else:
        items[1] = (items[1][0], items[1][1], GREEN, items[1][3] + " | 0 tickets routed to frontier", False)
    for m, v in fm["all_tickets_to_frontier_usd"].items():
        items.append((f"all -> {m}", v, AMBER, "modelled | accuracy not measured", True))
    fig, ax = plt.subplots(figsize=(11, 5.6))
    y = list(range(len(items)))[::-1]
    for yi, (lab, v, col, note, hatch) in zip(y, items):
        ax.barh(yi, v, color=col if not hatch else PANEL, edgecolor=col, hatch="///" if hatch else None, linewidth=1.5)
        ax.text(v, yi, f"  ${v:.4f}  {note}", va="center", fontsize=8.5, color=col)
    ax.set_yticks(y, [i[0] for i in items], fontsize=8.5)
    ax.set_xlabel(f"USD for {s['tickets']} tickets")
    ax.set_xlim(0, max(i[1] for i in items) * 1.75)
    ax.grid(axis="y", visible=False)
    ax.set_title("$ cost per run: local (compute modelled from instance price) vs frontier (MODELLED from list prices)",
                 fontsize=9.5, loc="left", color=GREEN)
    _foot(fig, f"local = wall time x {lc['instance']['name']} @ ${lc['instance']['usd_per_hour']}/h | frontier = "
               f"list prices fetched {s['prices']['fetch_date']}, chat-mode token counts as stand-in")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def gate_flow(s, path):
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.set_xlim(0, 110); ax.set_ylim(0, 56); ax.axis("off")
    ax.set_facecolor(BG)

    def box(x, y, w, h, text, col, fs=8.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc=PANEL, ec=col, lw=1.6))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=col)

    def arrow(x1, y1, x2, y2, label="", col=FG):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, color=col, lw=1.2))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, label, fontsize=7.5, color=col, ha="center")

    t = s["assumptions"]["threshold"].split(":")[0]
    ax.text(1, 53, "$ agent loop with stop + scope gates", color=GREEN, fontsize=11)
    box(2, 38, 16, 8, "tool call", CYAN)
    box(26, 38, 22, 8, f"stop gate\nP(usable) >= {t}?", GREEN)
    box(56, 38, 20, 8, "scope check\nP(in task) >= " + t + "?", GREEN)
    box(84, 38, 22, 8, "agent step\n(chat model)", CYAN)
    box(40, 24, 26, 7, "STOP + flag human", MAGENTA)
    arrow(18, 42, 26, 42)
    arrow(48, 42, 56, 42, "yes", GREEN)
    arrow(76, 42, 84, 42, "yes", GREEN)
    arrow(37, 38, 48, 31, "no", MAGENTA)
    arrow(66, 38, 58, 31, "no", MAGENTA)
    ax.add_patch(FancyArrowPatch((95, 46.5), (10, 46.5), connectionstyle="arc3,rad=0.18", arrowstyle="-|>",
                                 mutation_scale=12, color="#5E6B6E", lw=1))
    ax.text(52, 52.5, "next step", fontsize=7.5, color="#7E8C8F", ha="center")

    ax.text(1, 21, "$ ticket router (person-facing: low score -> human, never reject)", color=GREEN, fontsize=11)
    box(2, 4, 16, 8, "ticket", CYAN)
    box(26, 4, 24, 8, "router gate\nchoice + P(choice)", GREEN)
    box(60, 9.5, 14, 5, "small_model", CYAN, 8)
    box(77, 9.5, 12, 5, "frontier", AMBER, 8)
    box(92, 9.5, 14, 5, "human", MAGENTA, 8)
    box(66, 1, 34, 5, f"P < {t}  ->  human reviewer", MAGENTA, 8)
    arrow(18, 8, 26, 8)
    arrow(50, 9.5, 60, 12, "", GREEN)
    ax.add_patch(FancyArrowPatch((50, 10.5), (83, 14.5), connectionstyle="arc3,rad=-0.25", arrowstyle="-|>",
                                 mutation_scale=12, color=GREEN, lw=1.2))
    ax.add_patch(FancyArrowPatch((50, 11.5), (99, 14.5), connectionstyle="arc3,rad=-0.3", arrowstyle="-|>",
                                 mutation_scale=12, color=GREEN, lw=1.2))
    ax.text(53, 17.5, f"P(choice) >= {t}: go to the chosen handler", fontsize=7.5, color=GREEN)
    arrow(50, 6, 66, 3.5, "", MAGENTA)
    _foot(fig, "gate_signal_type is stop|route only. A score decides what code does next; it never certifies a claim.")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def make_all(summary, rows, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    tokens_time(summary, out / "01_tokens_time_chat_vs_gate.png")
    cost_accuracy(summary, out / "02_cost_vs_accuracy_frontier_modelled.png")
    gate_flow(summary, out / "03_gate_state_machine.png")
