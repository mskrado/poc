from __future__ import annotations

import json
from pathlib import Path

from voice_benchmark.config import load_stack_config
from voice_benchmark.metrics.cost import aggregate_cost
from voice_benchmark.metrics.latency import aggregate_latencies
from voice_benchmark.models import StackRunResult


def summarize_run(result: StackRunResult, config_root: Path | None = None) -> dict:
    stack_config = load_stack_config(result.stack, config_root)
    latency = aggregate_latencies(result.calls)
    cost = aggregate_cost(result.calls, stack_config)
    ref = stack_config.reference
    return {
        "stack": result.stack,
        "calls": result.total_calls,
        "successful_calls": result.successful_calls,
        "error_rate": round(result.error_rate, 4),
        **latency,
        **cost,
        "reference": {
            "p95_turn_latency_ms": ref.p95_turn_latency_ms if ref else None,
            "cost_per_minute": ref.cost_per_minute if ref else None,
            "error_rate": ref.error_rate if ref else None,
        },
    }


def format_comparison_table(summaries: list[dict]) -> str:
    headers = ["Stack", "p95 latency", "$/min", "error rate", "calls"]
    rows = []
    for s in summaries:
        rows.append(
            [
                s["stack"],
                f"{s['p95_turn_latency_ms']:.0f}ms",
                f"${s['cost_per_minute']:.2f}",
                f"{s['error_rate'] * 100:.1f}%",
                str(s["calls"]),
            ]
        )

    col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
    lines = []
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep = "-|-".join("-" * w for w in col_widths)
    lines.extend([header_line, sep])
    for row in rows:
        lines.append(" | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))))
    return "\n".join(lines)


def write_report(
    summaries: list[dict],
    output_dir: Path,
    *,
    prefix: str = "benchmark",
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"

    json_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")

    md_lines = [
        "# Voice Agent Benchmark Report",
        "",
        "```",
        format_comparison_table(summaries),
        "```",
        "",
        "## Details",
        "",
    ]
    for summary in summaries:
        md_lines.append(f"### {summary['stack']}")
        md_lines.append("")
        md_lines.append("```json")
        md_lines.append(json.dumps(summary, indent=2))
        md_lines.append("```")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path, md_path
