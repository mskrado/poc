"""Console tables and JSON/Markdown reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from browser_benchmark.models import Category
from browser_benchmark.scoring import format_duration

CATEGORY_LABELS = {
    Category.TRANSACTIONAL.value: "Transactional",
    Category.DATA_EXTRACTION.value: "Data extraction",
    Category.MIGRATION_BULK.value: "Migration/bulk",
    Category.FORM_COMPLETION.value: "Form completion",
}


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    all_rows = [list(headers)] + [list(r) for r in rows]
    widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]
    lines = [" | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("-|-".join("-" * w for w in widths))
    for row in rows:
        lines.append(" | ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(lines)


def format_overall_table(summaries: Sequence[dict]) -> str:
    headers = ["Framework", "Full", "Strict", "With partial", "Mean time", "Actions", "$/task"]
    rows = []
    for s in summaries:
        rows.append(
            [
                s["framework"],
                f"{s['full']}/{s['tasks']}",
                f"{s['full_rate'] * 100:.0f}%",
                f"{s['partial_credit_rate'] * 100:.0f}% (+{s['partial_bonus_points']:.0f}pt)",
                format_duration(s["mean_duration_seconds_completed"]),
                f"{s['mean_actions']:.0f}",
                f"${s['cost_per_task_usd']:.2f}",
            ]
        )
    return render_table(headers, rows)


def format_category_matrix(summaries: Sequence[dict]) -> str:
    """Category x framework success rates, with the article's numbers in parentheses."""
    headers = ["Category", "Tasks"] + [s["framework"] for s in summaries]
    rows = []
    for category_value, label in CATEGORY_LABELS.items():
        first = summaries[0]["by_category"].get(category_value)
        if not first:
            continue
        row = [label, str(first["tasks"])]
        for summary in summaries:
            stats = summary["by_category"][category_value]
            reference = stats.get("reference_full_rate")
            cell = f"{stats['full_rate'] * 100:.0f}%"
            if reference is not None:
                cell += f" (ref {reference * 100:.0f}%)"
            row.append(cell)
        rows.append(row)
    return render_table(headers, rows)


def format_failure_breakdown(breakdowns: dict[str, dict[str, dict[str, int]]]) -> str:
    lines = []
    for framework, modes in breakdowns.items():
        lines.append(f"{framework}")
        failures = modes.get("failure_modes", {})
        partials = modes.get("partial_modes", {})
        if failures:
            lines.append("  failures:")
            for name, count in failures.items():
                lines.append(f"    {count:>2}  {name}")
        if partials:
            lines.append("  partial successes:")
            for name, count in partials.items():
                lines.append(f"    {count:>2}  {name}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_routing_summary(summary: dict) -> str:
    ref = summary["reference"]
    tiers = ", ".join(f"{name}: {count}" for name, count in summary["resolved_by_tier"].items())
    baseline = summary["single_tier_baseline"]
    lines = [
        render_table(
            ["Resolution", "Tasks", "Rate", "Article reference"],
            [
                [
                    "Fully automated",
                    str(summary["automated"]),
                    f"{summary['automated_rate'] * 100:.0f}%",
                    f"{ref['automated_rate'] * 100:.0f}%",
                ],
                [
                    "Human-assisted",
                    str(summary["human_assisted"]),
                    f"{summary['human_assisted_rate'] * 100:.0f}%",
                    f"{ref['human_assisted_rate'] * 100:.0f}%",
                ],
            ],
        ),
        "",
        f"resolved by tier    {tiers}",
        f"escalations         {summary['escalations']}",
        f"agent cost          ${summary['agent_cost_usd']:.2f} "
        f"(all-{baseline['framework']} baseline: ${baseline['agent_cost_usd']:.2f})",
        f"human cost          ${summary['human_cost_usd']:.2f} "
        f"({summary['human_minutes']:.0f} operator minutes)",
        f"total cost          ${summary['total_cost_usd']:.2f}",
        f"mean wall clock     {format_duration(summary['mean_wall_clock_seconds'])} per task",
    ]
    return "\n".join(lines)


def format_routed_tasks(routed: Sequence) -> str:
    headers = ["Task", "Attempts", "Resolution"]
    rows = []
    for task in routed:
        trail = " -> ".join(f"{a.framework}:{a.outcome.value}" for a in task.attempts)
        if task.resolution.value == "human":
            trail += " -> human"
        rows.append([task.task_id, trail, task.resolution.value])
    return render_table(headers, rows)


def write_report(
    payload: dict,
    output_dir: Path,
    *,
    prefix: str = "benchmark",
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = ["# Browser Agent Benchmark Report", ""]
    summaries = payload.get("frameworks")
    if summaries:
        md_lines += [
            "## Overall",
            "",
            "```",
            format_overall_table(summaries),
            "```",
            "",
            "## By category",
            "",
            "```",
            format_category_matrix(summaries),
            "```",
            "",
        ]
    if payload.get("failure_modes"):
        md_lines += [
            "## Failure modes",
            "",
            "```",
            format_failure_breakdown(payload["failure_modes"]),
            "```",
            "",
        ]
    if payload.get("routing"):
        md_lines += [
            "## Tiered routing",
            "",
            "```",
            format_routing_summary(payload["routing"]),
            "```",
            "",
        ]
    md_lines += ["## Raw", "", "```json", json.dumps(payload, indent=2), "```", ""]

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path, md_path
