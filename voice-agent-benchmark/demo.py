#!/usr/bin/env python3
"""Run voice-agent benchmark scenarios from the roiscale article (dry-run by default)."""

from __future__ import annotations

import argparse
import asyncio
import json

from voice_benchmark.config import load_all_stack_configs
from voice_benchmark.orchestrator import compare_stacks, run_benchmark
from voice_benchmark.report import format_comparison_table, summarize_run, write_report


async def _demo_compare(calls: int) -> None:
    stacks = ["vapi", "retell", "pipecat", "openai_realtime"]
    print(f"=== Comparing {len(stacks)} stacks ({calls} calls each, mock mode) ===\n")
    results = await compare_stacks(stacks, calls=calls, mode="mock")
    summaries = [summarize_run(r) for r in results]
    print(format_comparison_table(summaries))
    print("\n--- Reference values from article ---")
    configs = load_all_stack_configs()
    for name in stacks:
        ref = configs[name].reference
        if ref:
            print(
                f"  {name:16} ref p95={ref.p95_turn_latency_ms:.0f}ms  "
                f"${ref.cost_per_minute:.2f}/min  err={ref.error_rate * 100:.1f}%"
            )
    write_report(summaries, __import__("pathlib").Path("reports"), prefix="demo-compare")
    print("\nReport written to reports/demo-compare.json")


async def _demo_single(stack: str, calls: int) -> None:
    print(f"=== Single stack: {stack} ({calls} calls, mock mode) ===\n")
    result = await run_benchmark(stack, calls=calls, mode="mock")
    summary = summarize_run(result)
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice agent benchmark demo")
    parser.add_argument(
        "--scenario",
        choices=["compare", "single", "all"],
        default="compare",
        help="compare = all four article stacks; single = one stack; all = both",
    )
    parser.add_argument("--stack", default="mock", help="Stack for single scenario")
    parser.add_argument("--calls", type=int, default=5, help="Calls per stack")
    args = parser.parse_args()

    if args.scenario in ("compare", "all"):
        asyncio.run(_demo_compare(args.calls))
    if args.scenario in ("single", "all"):
        asyncio.run(_demo_single(args.stack, args.calls))


if __name__ == "__main__":
    main()
