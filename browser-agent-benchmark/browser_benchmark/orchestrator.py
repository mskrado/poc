"""Batch runner over tasks x frameworks."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Sequence

from browser_benchmark.config import (
    DEFAULT_SEED,
    load_framework_config,
    load_router_config,
    load_tasks,
)
from browser_benchmark.frameworks import get_adapter
from browser_benchmark.models import Category, FrameworkRunResult, Task


def select_tasks(
    tasks: Sequence[Task] | None = None,
    *,
    categories: Sequence[str] | None = None,
    task_ids: Sequence[str] | None = None,
    config_root: Path | None = None,
) -> list[Task]:
    selected = list(tasks) if tasks is not None else load_tasks(config_root)
    if categories:
        wanted = {Category(c) for c in categories}
        selected = [t for t in selected if t.category in wanted]
    if task_ids:
        ids = set(task_ids)
        selected = [t for t in selected if t.id in ids]
    return selected


def default_correlation(config_root: Path | None = None) -> float:
    """Shared-difficulty setting lives with the router config; the mock model reads it."""
    return load_router_config(config_root).difficulty_correlation


async def run_framework(
    framework: str,
    tasks: Sequence[Task] | None = None,
    *,
    mode: str = "mock",
    seed: int = DEFAULT_SEED,
    correlation: float | None = None,
    config_root: Path | None = None,
) -> FrameworkRunResult:
    config = load_framework_config(framework, config_root)
    suite = select_tasks(tasks, config_root=config_root)
    adapter = get_adapter(
        config,
        mode=mode,
        seed=seed,
        correlation=default_correlation(config_root) if correlation is None else correlation,
    )
    return await adapter.run_suite(suite)


async def compare_frameworks(
    frameworks: Sequence[str],
    tasks: Sequence[Task] | None = None,
    *,
    mode: str = "mock",
    seed: int = DEFAULT_SEED,
    correlation: float | None = None,
    config_root: Path | None = None,
) -> list[FrameworkRunResult]:
    suite = select_tasks(tasks, config_root=config_root)
    resolved = default_correlation(config_root) if correlation is None else correlation
    runs = await asyncio.gather(
        *(
            run_framework(
                name,
                suite,
                mode=mode,
                seed=seed,
                correlation=resolved,
                config_root=config_root,
            )
            for name in frameworks
        )
    )
    return list(runs)
