from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Category(str, Enum):
    TRANSACTIONAL = "transactional"
    DATA_EXTRACTION = "data_extraction"
    MIGRATION_BULK = "migration_bulk"
    FORM_COMPLETION = "form_completion"


class Outcome(str, Enum):
    """Article scoring: full success, main goal reached but one step short, or failure."""

    FULL = "full"
    PARTIAL = "partial"
    FAIL = "fail"


class Resolution(str, Enum):
    AUTOMATED = "automated"
    HUMAN = "human"


# Tasks carrying this tag always end in a human handoff: all three frameworks in the
# article failed on mid-stream TOTP / SMS verification.
HUMAN_HANDOFF_TAG = "mfa"


@dataclass(frozen=True)
class Task:
    id: str
    category: Category
    goal: str
    fixture: str
    success_criteria: str
    partial_criteria: str
    tags: tuple[str, ...] = ()

    @property
    def requires_human_handoff(self) -> bool:
        return HUMAN_HANDOFF_TAG in self.tags


@dataclass(frozen=True)
class FrameworkReference:
    """Published numbers from the article, used to calibrate mock mode."""

    overall_success_rate: float
    partial_bonus: float
    mean_duration_seconds: float
    mean_actions: float
    success_rate_by_category: dict[str, float]

    def rate_for(self, category: Category) -> float:
        return float(self.success_rate_by_category[category.value])


@dataclass(frozen=True)
class FrameworkConfig:
    name: str
    enabled: bool
    description: str
    adapter: str
    observation: str
    model: str
    max_steps: int
    cost_per_task_usd: float
    reference: FrameworkReference
    failure_modes: dict[str, dict[str, Any]] = field(default_factory=dict)
    partial_modes: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def live(self) -> dict[str, Any]:
        return dict(self.raw.get("live", {}))


@dataclass(frozen=True)
class RunResult:
    task_id: str
    category: Category
    framework: str
    outcome: Outcome
    duration_seconds: float
    actions: int
    reason: str = ""
    note: str = ""

    @property
    def is_full(self) -> bool:
        return self.outcome is Outcome.FULL

    @property
    def counts_as_partial_credit(self) -> bool:
        return self.outcome in (Outcome.FULL, Outcome.PARTIAL)


@dataclass
class FrameworkRunResult:
    framework: str
    results: list[RunResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def full_successes(self) -> int:
        return sum(1 for r in self.results if r.is_full)

    @property
    def partial_credit(self) -> int:
        return sum(1 for r in self.results if r.counts_as_partial_credit)


@dataclass(frozen=True)
class RouterAttempt:
    framework: str
    outcome: Outcome
    duration_seconds: float
    actions: int
    reason: str
    cost_usd: float


@dataclass
class RoutedTask:
    task_id: str
    category: Category
    attempts: list[RouterAttempt] = field(default_factory=list)
    resolution: Resolution = Resolution.HUMAN
    automated_by: str | None = None

    @property
    def duration_seconds(self) -> float:
        return sum(a.duration_seconds for a in self.attempts)

    @property
    def agent_cost_usd(self) -> float:
        return sum(a.cost_usd for a in self.attempts)

    @property
    def escalations(self) -> int:
        return max(0, len(self.attempts) - 1)
