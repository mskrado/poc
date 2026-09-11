"""Tiered routing: cheapest framework first, escalate on anything short of full success.

The article's deployed system tries Browser-Use, escalates to Playwright-MCP on the first
failure, and pages a human after the second. A partial success counts as a failure here:
"got to checkout but never clicked confirm" still leaves work on the table.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Sequence

from browser_benchmark.config import (
    DEFAULT_SEED,
    RouterConfig,
    load_framework_config,
    load_router_config,
)
from browser_benchmark.frameworks import get_adapter
from browser_benchmark.frameworks.base import FrameworkAdapter
from browser_benchmark.models import Resolution, RouterAttempt, RoutedTask, Task
from browser_benchmark.orchestrator import select_tasks


def _build_tier_adapters(
    router: RouterConfig,
    tasks: Sequence[Task],
    *,
    mode: str,
    seed: int,
    config_root: Path | None,
) -> list[tuple[str, FrameworkAdapter, float]]:
    tiers: list[tuple[str, FrameworkAdapter, float]] = []
    for name in router.tiers:
        config = load_framework_config(name, config_root)
        adapter = get_adapter(
            config,
            mode=mode,
            seed=seed,
            correlation=router.difficulty_correlation,
        )
        adapter.prepare(tasks)
        tiers.append((name, adapter, config.cost_per_task_usd))
    return tiers


async def route_task(
    task: Task,
    tiers: Sequence[tuple[str, FrameworkAdapter, float]],
    router: RouterConfig,
) -> RoutedTask:
    routed = RoutedTask(task_id=task.id, category=task.category)
    for name, adapter, cost in tiers:
        result = await adapter.run_task(task)
        routed.attempts.append(
            RouterAttempt(
                framework=name,
                outcome=result.outcome,
                duration_seconds=result.duration_seconds,
                actions=result.actions,
                reason=result.reason,
                cost_usd=cost,
            )
        )
        if not router.should_escalate(result.outcome):
            routed.resolution = Resolution.AUTOMATED
            routed.automated_by = name
            return routed
    routed.resolution = Resolution.HUMAN
    return routed


async def route_suite(
    tasks: Sequence[Task] | None = None,
    *,
    mode: str = "mock",
    seed: int = DEFAULT_SEED,
    config_root: Path | None = None,
) -> list[RoutedTask]:
    router = load_router_config(config_root)
    suite = select_tasks(tasks, config_root=config_root)
    tiers = _build_tier_adapters(router, suite, mode=mode, seed=seed, config_root=config_root)
    routed = await asyncio.gather(*(route_task(task, tiers, router) for task in suite))
    return list(routed)


def summarize_routing(
    routed: Sequence[RoutedTask], router: RouterConfig | None = None, config_root: Path | None = None
) -> dict:
    router = router or load_router_config(config_root)
    total = len(routed)
    automated = [r for r in routed if r.resolution is Resolution.AUTOMATED]
    human = [r for r in routed if r.resolution is Resolution.HUMAN]

    by_tier: dict[str, int] = {name: 0 for name in router.tiers}
    for task in automated:
        if task.automated_by:
            by_tier[task.automated_by] = by_tier.get(task.automated_by, 0) + 1

    agent_cost = sum(r.agent_cost_usd for r in routed)
    human_cost = len(human) * router.human_cost_usd
    automated_rate = 0.0 if total == 0 else len(automated) / total

    # What the same suite would cost if every task went straight to the strongest
    # single framework instead of being tiered.
    single_best = max(
        (load_framework_config(name, config_root) for name in router.tiers),
        key=lambda c: c.reference.overall_success_rate,
    )
    single_best_cost = single_best.cost_per_task_usd * total

    return {
        "tasks": total,
        "automated": len(automated),
        "human_assisted": len(human),
        "automated_rate": round(automated_rate, 4),
        "human_assisted_rate": round(1 - automated_rate, 4),
        "resolved_by_tier": by_tier,
        "escalations": sum(r.escalations for r in routed),
        "agent_cost_usd": round(agent_cost, 2),
        "human_cost_usd": round(human_cost, 2),
        "total_cost_usd": round(agent_cost + human_cost, 2),
        "single_tier_baseline": {
            "framework": single_best.name,
            "agent_cost_usd": round(single_best_cost, 2),
        },
        "mean_wall_clock_seconds": round(
            0.0 if total == 0 else sum(r.duration_seconds for r in routed) / total, 1
        ),
        "human_minutes": round(len(human) * router.human_minutes, 1),
        "reference": {
            "automated_rate": router.reference_automated_rate,
            "human_assisted_rate": router.reference_human_rate,
        },
    }
