#!/usr/bin/env python3
"""Reproduce the article's browser-automation comparison (mock mode, no API keys)."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from browser_benchmark.config import DEFAULT_SEED, load_framework_config, load_router_config, load_tasks
from browser_benchmark.orchestrator import compare_frameworks
from browser_benchmark.report import (
    format_category_matrix,
    format_failure_breakdown,
    format_overall_table,
    format_routed_tasks,
    format_routing_summary,
    write_report,
)
from browser_benchmark.router import route_suite, summarize_routing
from browser_benchmark.scoring import failure_breakdown, summarize_framework

FRAMEWORKS = ["playwright_mcp", "browser_use", "computer_use"]


async def _runs(seed: int):
    return await compare_frameworks(FRAMEWORKS, mode="mock", seed=seed)


async def demo_compare(seed: int) -> None:
    tasks = load_tasks()
    print(f"=== {len(tasks)} workflows x {len(FRAMEWORKS)} frameworks (mock mode, seed {seed}) ===\n")
    runs = await _runs(seed)
    summaries = [summarize_framework(r, load_framework_config(r.framework)) for r in runs]
    print(format_overall_table(summaries))
    print()
    print(format_category_matrix(summaries))
    print(
        "\nStrict success counts only workflows that hit their stated goal unattended. "
        "The partial column adds\n'main goal reached, one step short' - usually the final "
        "confirm button the backing model declined to press."
    )
    payload = {"seed": seed, "frameworks": summaries}
    write_report(payload, Path("reports"), prefix="demo-compare")
    print("\nReport written to reports/demo-compare.json")


async def demo_failures(seed: int) -> None:
    print(f"=== Failure and partial-success modes (mock mode, seed {seed}) ===\n")
    runs = await _runs(seed)
    print(format_failure_breakdown({r.framework: failure_breakdown(r) for r in runs}))
    print(
        "\nEvery framework loses the same two workflows to mid-stream verification: "
        "bank_transfer_schedule and csv_contacts_to_network. Plan for human handoff."
    )


async def demo_route(seed: int) -> None:
    router = load_router_config()
    tiers = " -> ".join(router.tiers) + " -> human"
    print(f"=== Tiered routing: {tiers} (mock mode, seed {seed}) ===\n")
    routed = await route_suite(mode="mock", seed=seed)
    summary = summarize_routing(routed, router)
    print(format_routing_summary(summary))
    print()
    print(format_routed_tasks(routed))
    payload = {"seed": seed, "routing": summary}
    write_report(payload, Path("reports"), prefix="demo-route")
    print("\nReport written to reports/demo-route.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Browser agent benchmark demo")
    parser.add_argument(
        "--scenario",
        choices=["compare", "failures", "route", "all"],
        default="compare",
        help="compare = framework matrix; failures = why runs broke; route = tiered router",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    scenarios = ["compare", "failures", "route"] if args.scenario == "all" else [args.scenario]
    for index, scenario in enumerate(scenarios):
        if index:
            print("\n" + "=" * 78 + "\n")
        asyncio.run({"compare": demo_compare, "failures": demo_failures, "route": demo_route}[scenario](args.seed))


if __name__ == "__main__":
    main()
