"""Calibrated replay of the article's published results.

This is not a measurement. Each framework's per-category success rate is pinned to the
number it published, and the model decides *which* tasks land in the full / partial / fail
buckets:

* every task gets a difficulty draw from a stable hash of (seed, task id)
* each framework blends that shared draw with its own private draw, controlled by
  `difficulty_correlation` — so hard tasks tend to be hard for everyone, which is what
  makes the tiered router's escalation numbers believable
* tasks tagged `mfa` always fail: all three frameworks in the article lost to mid-stream
  TOTP and SMS verification

Changing the seed reshuffles which tasks fail without moving the published rates.
"""

from __future__ import annotations

import hashlib
from typing import Sequence

from browser_benchmark.config import DEFAULT_SEED, tasks_by_category
from browser_benchmark.frameworks.base import FrameworkAdapter
from browser_benchmark.models import Category, FrameworkConfig, Outcome, RunResult, Task

MFA_REASON = "mfa_human_handoff"
TAG_BOOST = 3.0
FAILED_ATTEMPT_DURATION_MULTIPLIER = 1.3


def stable_uniform(*parts: object) -> float:
    """Deterministic [0, 1) draw from the string form of its arguments."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def round_half_up(value: float) -> int:
    return int(value + 0.5)


def difficulty(task: Task, framework: str, seed: int, correlation: float) -> float:
    """Blend a shared difficulty draw with a framework-private one.

    The mixture (rather than an average) keeps each framework's marginal draw uniform
    while still correlating failures across frameworks.
    """
    shared = stable_uniform(seed, "shared", task.id)
    private = stable_uniform(seed, "private", framework, task.id)
    selector = stable_uniform(seed, "selector", framework, task.id)
    return shared if selector < correlation else private


def allocate_outcomes(
    tasks: Sequence[Task],
    config: FrameworkConfig,
    *,
    seed: int,
    correlation: float,
) -> dict[str, Outcome]:
    """Place each task in full / partial / fail so category rates match the article."""
    plan: dict[str, Outcome] = {}
    for category, group in tasks_by_category(list(tasks)).items():
        if not group:
            continue
        handoffs = [t for t in group if t.requires_human_handoff]
        pool = sorted(
            (t for t in group if not t.requires_human_handoff),
            key=lambda t: (difficulty(t, config.name, seed, correlation), t.id),
        )
        total = len(group)
        n_full = min(len(pool), round_half_up(config.reference.rate_for(category) * total))
        n_partial = min(
            len(pool) - n_full,
            round_half_up(config.reference.partial_bonus * total),
        )
        for index, task in enumerate(pool):
            if index < n_full:
                plan[task.id] = Outcome.FULL
            elif index < n_full + n_partial:
                plan[task.id] = Outcome.PARTIAL
            else:
                plan[task.id] = Outcome.FAIL
        for task in handoffs:
            plan[task.id] = Outcome.FAIL
    return plan


def pick_mode(modes: dict[str, dict], task: Task, draw: float) -> tuple[str, str]:
    """Weighted choice of a failure or partial-success mode, boosted by task tags."""
    if not modes:
        return "", ""
    task_tags = set(task.tags)
    weighted: list[tuple[str, float, str]] = []
    for name, spec in modes.items():
        weight = float(spec.get("weight", 1.0))
        if task_tags & set(spec.get("tags", [])):
            weight *= TAG_BOOST
        weighted.append((name, weight, str(spec.get("description", ""))))

    total = sum(w for _, w, _ in weighted)
    if total <= 0:
        name, _, description = weighted[0]
        return name, description
    threshold = draw * total
    cumulative = 0.0
    for name, weight, description in weighted:
        cumulative += weight
        if threshold < cumulative:
            return name, description
    name, _, description = weighted[-1]
    return name, description


class MockAdapter(FrameworkAdapter):
    """Dry-run adapter: no browser, no API keys, article-calibrated outcomes."""

    def __init__(
        self,
        config: FrameworkConfig,
        *,
        seed: int = DEFAULT_SEED,
        correlation: float = 0.0,
    ) -> None:
        super().__init__(config, seed=seed, correlation=correlation)
        self._plan: dict[str, Outcome] = {}

    def prepare(self, tasks: Sequence[Task]) -> None:
        self._plan = allocate_outcomes(
            tasks, self.config, seed=self.seed, correlation=self.correlation
        )

    def outcome_for(self, task: Task) -> Outcome:
        if task.id not in self._plan:
            self.prepare([task])
        return self._plan[task.id]

    async def run_task(self, task: Task) -> RunResult:
        outcome = self.outcome_for(task)
        reference = self.config.reference

        spread = stable_uniform(self.seed, "duration", self.config.name, task.id)
        duration = reference.mean_duration_seconds * (0.65 + 0.7 * spread)
        if outcome is Outcome.FAIL:
            duration *= FAILED_ATTEMPT_DURATION_MULTIPLIER

        action_spread = stable_uniform(self.seed, "actions", self.config.name, task.id)
        actions = max(3, round(reference.mean_actions * (0.7 + 0.6 * action_spread)))

        reason, note = self._explain(task, outcome)
        return RunResult(
            task_id=task.id,
            category=task.category,
            framework=self.config.name,
            outcome=outcome,
            duration_seconds=round(duration, 1),
            actions=actions,
            reason=reason,
            note=note,
        )

    def _explain(self, task: Task, outcome: Outcome) -> tuple[str, str]:
        if outcome is Outcome.FULL:
            return "", ""
        if task.requires_human_handoff:
            return MFA_REASON, "Out-of-band verification code; no framework can proceed unattended."
        draw = stable_uniform(self.seed, "reason", self.config.name, task.id)
        modes = self.config.failure_modes if outcome is Outcome.FAIL else self.config.partial_modes
        return pick_mode(modes, task, draw)


def category_plan(
    tasks: Sequence[Task], config: FrameworkConfig, *, seed: int, correlation: float
) -> dict[Category, dict[Outcome, int]]:
    """Bucket counts per category — useful for asserting calibration in tests."""
    plan = allocate_outcomes(tasks, config, seed=seed, correlation=correlation)
    counts: dict[Category, dict[Outcome, int]] = {}
    for task in tasks:
        bucket = counts.setdefault(task.category, {o: 0 for o in Outcome})
        bucket[plan[task.id]] += 1
    return counts
