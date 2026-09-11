from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from browser_benchmark.models import (
    Category,
    FrameworkConfig,
    FrameworkReference,
    Outcome,
    Task,
)

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")

DEFAULT_SEED = 1337


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):

        def repl(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), match.group(0))

        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return _expand_env(data)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def config_root(root: Path | None = None) -> Path:
    if root is not None:
        return root
    return project_root() / "config"


def fixtures_root(root: Path | None = None) -> Path:
    if root is not None:
        return root
    return project_root() / "fixtures"


def sites_root(root: Path | None = None) -> Path:
    return fixtures_root(root) / "sites"


def load_tasks(root: Path | None = None) -> list[Task]:
    raw = load_yaml(config_root(root) / "tasks.yaml")
    tasks: list[Task] = []
    for entry in raw.get("tasks", []):
        tasks.append(
            Task(
                id=str(entry["id"]),
                category=Category(entry["category"]),
                goal=str(entry["goal"]),
                fixture=str(entry["fixture"]),
                success_criteria=str(entry["success_criteria"]),
                partial_criteria=str(entry.get("partial_criteria", "")),
                tags=tuple(entry.get("tags", [])),
            )
        )
    seen: set[str] = set()
    for task in tasks:
        if task.id in seen:
            raise ValueError(f"duplicate task id in tasks.yaml: {task.id}")
        seen.add(task.id)
    return tasks


def tasks_by_category(tasks: list[Task]) -> dict[Category, list[Task]]:
    grouped: dict[Category, list[Task]] = {c: [] for c in Category}
    for task in tasks:
        grouped[task.category].append(task)
    return grouped


def load_framework_config(name: str, root: Path | None = None) -> FrameworkConfig:
    raw = load_yaml(config_root(root) / "frameworks" / f"{name}.yaml")
    ref_raw = raw["reference"]
    reference = FrameworkReference(
        overall_success_rate=float(ref_raw["overall_success_rate"]),
        partial_bonus=float(ref_raw["partial_bonus"]),
        mean_duration_seconds=float(ref_raw["mean_duration_seconds"]),
        mean_actions=float(ref_raw["mean_actions"]),
        success_rate_by_category={
            k: float(v) for k, v in ref_raw["success_rate_by_category"].items()
        },
    )
    return FrameworkConfig(
        name=str(raw.get("framework", name)),
        enabled=bool(raw.get("enabled", True)),
        description=str(raw.get("description", "")),
        adapter=str(raw.get("adapter", name)),
        observation=str(raw.get("observation", "dom")),
        model=str(raw.get("model", "")),
        max_steps=int(raw.get("max_steps", 25)),
        cost_per_task_usd=float(raw.get("cost_per_task_usd", 0.0)),
        reference=reference,
        failure_modes=dict(raw.get("failure_modes", {})),
        partial_modes=dict(raw.get("partial_modes", {})),
        raw=raw,
    )


def list_framework_names(root: Path | None = None) -> list[str]:
    frameworks_dir = config_root(root) / "frameworks"
    return sorted(p.stem for p in frameworks_dir.glob("*.yaml"))


def load_all_framework_configs(root: Path | None = None) -> dict[str, FrameworkConfig]:
    return {name: load_framework_config(name, root) for name in list_framework_names(root)}


@dataclass(frozen=True)
class RouterConfig:
    tiers: tuple[str, ...]
    escalate_on: tuple[Outcome, ...]
    difficulty_correlation: float
    human_cost_usd: float
    human_minutes: float
    reference_automated_rate: float
    reference_human_rate: float
    raw: dict[str, Any]

    def should_escalate(self, outcome: Outcome) -> bool:
        return outcome in self.escalate_on


def load_router_config(root: Path | None = None) -> RouterConfig:
    raw = load_yaml(config_root(root) / "router.yaml")
    ref = raw.get("reference", {})
    human = raw.get("human_tier", {})
    return RouterConfig(
        tiers=tuple(str(t) for t in raw["tiers"]),
        escalate_on=tuple(Outcome(o) for o in raw.get("escalate_on", ["partial", "fail"])),
        difficulty_correlation=float(raw.get("difficulty_correlation", 0.0)),
        human_cost_usd=float(human.get("cost_usd", 0.0)),
        human_minutes=float(human.get("minutes", 0.0)),
        reference_automated_rate=float(ref.get("automated_rate", 0.0)),
        reference_human_rate=float(ref.get("human_assisted_rate", 0.0)),
        raw=raw,
    )
