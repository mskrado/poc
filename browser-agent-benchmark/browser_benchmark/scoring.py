"""Rollups over run results: strict success, partial credit, and where time went."""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

from browser_benchmark.models import (
    Category,
    FrameworkConfig,
    FrameworkRunResult,
    Outcome,
    RunResult,
)


def _rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _mean(values: Sequence[float]) -> float:
    return 0.0 if not values else sum(values) / len(values)


def category_rollup(results: Iterable[RunResult]) -> dict[str, dict]:
    """Per-category full / partial / fail counts and rates."""
    buckets: dict[Category, list[RunResult]] = {}
    for result in results:
        buckets.setdefault(result.category, []).append(result)

    rollup: dict[str, dict] = {}
    for category in Category:
        group = buckets.get(category, [])
        if not group:
            continue
        full = sum(1 for r in group if r.outcome is Outcome.FULL)
        partial = sum(1 for r in group if r.outcome is Outcome.PARTIAL)
        rollup[category.value] = {
            "tasks": len(group),
            "full": full,
            "partial": partial,
            "fail": len(group) - full - partial,
            "full_rate": round(_rate(full, len(group)), 4),
            "partial_credit_rate": round(_rate(full + partial, len(group)), 4),
        }
    return rollup


def summarize_framework(run: FrameworkRunResult, config: FrameworkConfig) -> dict:
    results = run.results
    total = len(results)
    full = run.full_successes
    partial_credit = run.partial_credit
    completed = [r for r in results if r.counts_as_partial_credit]

    rollup = category_rollup(results)
    for category_value, stats in rollup.items():
        stats["reference_full_rate"] = config.reference.success_rate_by_category.get(category_value)

    full_rate = _rate(full, total)
    partial_credit_rate = _rate(partial_credit, total)
    return {
        "framework": run.framework,
        "description": config.description,
        "observation": config.observation,
        "model": config.model,
        "tasks": total,
        "full": full,
        "partial": partial_credit - full,
        "fail": total - partial_credit,
        "full_rate": round(full_rate, 4),
        "partial_credit_rate": round(partial_credit_rate, 4),
        "partial_bonus_points": round((partial_credit_rate - full_rate) * 100, 1),
        "mean_duration_seconds": round(_mean([r.duration_seconds for r in results]), 1),
        "mean_duration_seconds_completed": round(
            _mean([r.duration_seconds for r in completed]), 1
        ),
        "mean_actions": round(_mean([float(r.actions) for r in results]), 1),
        "cost_per_task_usd": config.cost_per_task_usd,
        "total_cost_usd": round(config.cost_per_task_usd * total, 2),
        "by_category": rollup,
        "reference": {
            "overall_success_rate": config.reference.overall_success_rate,
            "partial_bonus": config.reference.partial_bonus,
            "mean_duration_seconds": config.reference.mean_duration_seconds,
            "mean_actions": config.reference.mean_actions,
        },
    }


def failure_breakdown(run: FrameworkRunResult) -> dict[str, dict[str, int]]:
    """Count failure and partial-success modes for one framework."""
    failures: Counter[str] = Counter()
    partials: Counter[str] = Counter()
    for result in run.results:
        if result.outcome is Outcome.FAIL and result.reason:
            failures[result.reason] += 1
        elif result.outcome is Outcome.PARTIAL and result.reason:
            partials[result.reason] += 1
    return {
        "failure_modes": dict(failures.most_common()),
        "partial_modes": dict(partials.most_common()),
    }


def format_duration(seconds: float) -> str:
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes}:{secs:02d}"
