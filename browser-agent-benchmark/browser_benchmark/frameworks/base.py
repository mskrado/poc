from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Sequence

from browser_benchmark.config import DEFAULT_SEED
from browser_benchmark.models import FrameworkConfig, FrameworkRunResult, RunResult, Task


class LiveModeUnavailable(RuntimeError):
    """Raised when a live adapter is requested but only the hook points exist."""


class FrameworkAdapter(ABC):
    """One browser automation framework under test.

    `prepare` receives the whole suite before any task runs. Mock mode needs the cohort
    to place a framework's published success rate across its category; live adapters can
    ignore it.
    """

    def __init__(
        self,
        config: FrameworkConfig,
        *,
        seed: int = DEFAULT_SEED,
        correlation: float = 0.0,
    ) -> None:
        self.config = config
        self.seed = seed
        self.correlation = correlation

    @property
    def name(self) -> str:
        return self.config.name

    def prepare(self, tasks: Sequence[Task]) -> None:
        """Hook called once with the full task cohort before the first run."""

    @abstractmethod
    async def run_task(self, task: Task) -> RunResult:
        """Run one workflow and score it against the task's success criteria."""

    async def run_suite(self, tasks: Sequence[Task]) -> FrameworkRunResult:
        self.prepare(tasks)
        results = await asyncio.gather(*(self.run_task(task) for task in tasks))
        return FrameworkRunResult(framework=self.name, results=list(results))
