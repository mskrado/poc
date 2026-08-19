from __future__ import annotations

from voice_benchmark.models import CallRecord, StackConfig


def estimate_call_cost(call: CallRecord, config: StackConfig) -> float:
    minutes = max(call.duration_seconds, 1.0) / 60.0
    return minutes * config.cost_per_minute()


def aggregate_cost(calls: list[CallRecord], config: StackConfig) -> dict[str, float]:
    if not calls:
        return {"total_cost_usd": 0.0, "cost_per_minute": config.cost_per_minute()}
    total = sum(estimate_call_cost(c, config) for c in calls)
    total_minutes = sum(max(c.duration_seconds, 1.0) for c in calls) / 60.0
    avg_per_min = total / total_minutes if total_minutes else config.cost_per_minute()
    return {
        "total_cost_usd": round(total, 4),
        "cost_per_minute": round(avg_per_min, 4),
    }
