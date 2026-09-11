import asyncio

from browser_benchmark.config import DEFAULT_SEED, load_router_config, load_tasks
from browser_benchmark.models import Outcome, Resolution
from browser_benchmark.router import route_suite, summarize_routing


def _route(seed=DEFAULT_SEED):
    return asyncio.run(route_suite(mode="mock", seed=seed))


def test_default_seed_lands_on_the_articles_production_split():
    summary = summarize_routing(_route())
    assert abs(summary["automated_rate"] - summary["reference"]["automated_rate"]) <= 0.02
    assert summary["automated"] + summary["human_assisted"] == 30


def test_automated_rate_stays_in_a_believable_band_across_seeds():
    for seed in (1, 7, 42, 2026, 90210):
        summary = summarize_routing(_route(seed))
        assert 0.60 <= summary["automated_rate"] <= 0.85, seed


def test_escalation_order_and_stopping_rule():
    router = load_router_config()
    for task in _route():
        frameworks = [a.framework for a in task.attempts]
        assert frameworks == list(router.tiers[: len(frameworks)])
        # Every attempt before the last one must have been escalation-worthy.
        for attempt in task.attempts[:-1]:
            assert router.should_escalate(attempt.outcome)
        last = task.attempts[-1]
        if task.resolution is Resolution.AUTOMATED:
            assert last.outcome is Outcome.FULL
            assert task.automated_by == last.framework
        else:
            assert len(task.attempts) == len(router.tiers)
            assert router.should_escalate(last.outcome)


def test_partial_success_escalates_rather_than_counting_as_done():
    escalated_partials = [
        task
        for task in _route()
        if any(a.outcome is Outcome.PARTIAL for a in task.attempts[:-1])
    ]
    assert escalated_partials, "expected at least one partial success to trigger escalation"


def test_mfa_tasks_always_reach_a_human():
    handoffs = {t.id for t in load_tasks() if t.requires_human_handoff}
    for task in _route():
        if task.task_id in handoffs:
            assert task.resolution is Resolution.HUMAN
            assert all(a.reason == "mfa_human_handoff" for a in task.attempts)


def test_cheapest_tier_carries_most_of_the_load():
    summary = summarize_routing(_route())
    by_tier = summary["resolved_by_tier"]
    assert by_tier["browser_use"] > by_tier["playwright_mcp"]


def test_cost_accounting_includes_the_human_tier():
    summary = summarize_routing(_route())
    router = load_router_config()
    assert summary["human_cost_usd"] == round(summary["human_assisted"] * router.human_cost_usd, 2)
    assert summary["total_cost_usd"] == round(
        summary["agent_cost_usd"] + summary["human_cost_usd"], 2
    )
    # Escalation means the tiered path costs more in agent spend than one framework alone.
    assert summary["agent_cost_usd"] > summary["single_tier_baseline"]["agent_cost_usd"] * 0.5
