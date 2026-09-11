import asyncio

from browser_benchmark.config import DEFAULT_SEED, list_framework_names, load_framework_config, load_tasks
from browser_benchmark.frameworks.mock import allocate_outcomes, round_half_up
from browser_benchmark.models import Outcome
from browser_benchmark.orchestrator import compare_frameworks, run_framework
from browser_benchmark.scoring import category_rollup, failure_breakdown, summarize_framework

FRAMEWORKS = ["playwright_mcp", "browser_use", "computer_use"]


def _summaries(seed=DEFAULT_SEED):
    runs = asyncio.run(compare_frameworks(FRAMEWORKS, mode="mock", seed=seed))
    return {r.framework: summarize_framework(r, load_framework_config(r.framework)) for r in runs}


def test_mock_reproduces_published_category_rates():
    for framework, summary in _summaries().items():
        config = load_framework_config(framework)
        for category, stats in summary["by_category"].items():
            expected = config.reference.success_rate_by_category[category]
            assert stats["full"] == round_half_up(expected * stats["tasks"]), (framework, category)


def test_category_rates_hold_across_seeds():
    for seed in (1, 7, 1337, 90210):
        for framework, summary in _summaries(seed).items():
            config = load_framework_config(framework)
            for category, stats in summary["by_category"].items():
                expected = config.reference.success_rate_by_category[category]
                assert stats["full_rate"] == round(
                    round_half_up(expected * stats["tasks"]) / stats["tasks"], 4
                ), (seed, framework, category)


def test_overall_ordering_matches_the_article():
    summaries = _summaries()
    assert (
        summaries["playwright_mcp"]["full_rate"]
        > summaries["browser_use"]["full_rate"]
        > summaries["computer_use"]["full_rate"]
    )
    for framework, summary in summaries.items():
        reference = load_framework_config(framework).reference.overall_success_rate
        assert abs(summary["full_rate"] - reference) <= 0.03


def test_partial_credit_adds_fifteen_to_twentytwo_points():
    for summary in _summaries().values():
        assert 15 <= summary["partial_bonus_points"] <= 22.5


def test_speed_and_action_profile_matches_the_article():
    summaries = _summaries()
    # Browser-Use is fastest, Computer-Use slowest, and Browser-Use over-clicks.
    assert (
        summaries["browser_use"]["mean_duration_seconds_completed"]
        < summaries["playwright_mcp"]["mean_duration_seconds_completed"]
        < summaries["computer_use"]["mean_duration_seconds_completed"]
    )
    assert summaries["browser_use"]["mean_actions"] > summaries["playwright_mcp"]["mean_actions"]
    for framework, summary in summaries.items():
        reference = load_framework_config(framework).reference
        assert abs(summary["mean_actions"] - reference.mean_actions) <= 1.5


def test_mfa_tasks_fail_for_every_framework():
    tasks = load_tasks()
    handoffs = [t.id for t in tasks if t.requires_human_handoff]
    for name in list_framework_names():
        plan = allocate_outcomes(
            tasks, load_framework_config(name), seed=DEFAULT_SEED, correlation=0.6
        )
        for task_id in handoffs:
            assert plan[task_id] is Outcome.FAIL, (name, task_id)


def test_failure_reasons_are_explained_and_tag_aware():
    run = asyncio.run(run_framework("browser_use", mode="mock"))
    by_id = {r.task_id: r for r in run.results}
    assert by_id["bank_transfer_schedule"].reason == "mfa_human_handoff"

    breakdown = failure_breakdown(run)
    assert breakdown["failure_modes"]
    assert sum(breakdown["failure_modes"].values()) == sum(
        1 for r in run.results if r.outcome is Outcome.FAIL
    )
    for result in run.results:
        if result.outcome is Outcome.FULL:
            assert result.reason == ""
        else:
            assert result.reason


def test_category_rollup_counts_add_up():
    run = asyncio.run(run_framework("computer_use", mode="mock"))
    rollup = category_rollup(run.results)
    assert sum(stats["tasks"] for stats in rollup.values()) == len(run.results)
    for stats in rollup.values():
        assert stats["full"] + stats["partial"] + stats["fail"] == stats["tasks"]
