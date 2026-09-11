from browser_benchmark.config import (
    config_root,
    list_framework_names,
    load_framework_config,
    load_router_config,
    load_tasks,
    sites_root,
    tasks_by_category,
)
from browser_benchmark.models import Category

EXPECTED_COUNTS = {
    Category.TRANSACTIONAL: 10,
    Category.DATA_EXTRACTION: 8,
    Category.MIGRATION_BULK: 7,
    Category.FORM_COMPLETION: 5,
}


def test_suite_has_thirty_tasks():
    tasks = load_tasks()
    assert len(tasks) == 30
    assert len({t.id for t in tasks}) == 30


def test_category_counts_match_article():
    grouped = tasks_by_category(load_tasks())
    assert {c: len(g) for c, g in grouped.items()} == EXPECTED_COUNTS


def test_declared_counts_match_task_entries():
    import yaml

    with (config_root() / "tasks.yaml").open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    grouped = tasks_by_category(load_tasks())
    for name, meta in raw["categories"].items():
        assert meta["count"] == len(grouped[Category(name)])


def test_every_task_points_at_a_real_fixture():
    for task in load_tasks():
        assert (sites_root() / task.fixture / "index.html").exists(), task.id
        assert task.goal and task.success_criteria and task.partial_criteria


def test_two_tasks_require_human_handoff():
    handoffs = [t.id for t in load_tasks() if t.requires_human_handoff]
    assert sorted(handoffs) == ["bank_transfer_schedule", "csv_contacts_to_network"]


def test_framework_configs_carry_article_reference_numbers():
    assert set(list_framework_names()) == {"browser_use", "computer_use", "playwright_mcp"}

    playwright = load_framework_config("playwright_mcp")
    assert playwright.observation == "dom"
    assert playwright.reference.overall_success_rate == 0.52
    assert playwright.reference.rate_for(Category.TRANSACTIONAL) == 0.60

    computer_use = load_framework_config("computer_use")
    assert computer_use.observation == "screenshot"
    # The article's one category win for the pixel-based approach.
    assert computer_use.reference.rate_for(Category.FORM_COMPLETION) > playwright.reference.rate_for(
        Category.FORM_COMPLETION
    )


def test_partial_bonus_is_within_the_published_band():
    for name in list_framework_names():
        bonus = load_framework_config(name).reference.partial_bonus
        assert 0.15 <= bonus <= 0.22


def test_router_config():
    router = load_router_config()
    assert router.tiers == ("browser_use", "playwright_mcp")
    assert router.reference_automated_rate == 0.71
    assert 0.0 <= router.difficulty_correlation <= 1.0
