"""Historical incident replay harness — the eval layer the article wished for day one."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from oncall_agent.graph import OnCallAgent
from oncall_agent.sandbox import RunbookSandbox
from oncall_agent.tools import IncidentFixture, ToolBus


@dataclass
class EvalCaseResult:
    incident_id: str
    expected: str
    actual: str
    passed: bool
    sandbox_blocked: bool
    paged_human: bool
    notes: str


@dataclass
class HarnessReport:
    total: int
    passed: int
    failed: int
    cases: list[EvalCaseResult]

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def load_fixtures(path: Path) -> list[IncidentFixture]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        IncidentFixture(
            incident_id=item["incident_id"],
            severity=item["severity"],
            affected_service=item["affected_service"],
            title=item["title"],
            metrics=item.get("metrics", {}),
            logs=item.get("logs", []),
            expected_outcome=item["expected_outcome"],
            notes=item.get("notes", ""),
        )
        for item in raw
    ]


def run_harness(
    fixtures: list[IncidentFixture],
    *,
    human_confirmed_destructive: bool = False,
) -> HarnessReport:
    cases: list[EvalCaseResult] = []

    for fixture in fixtures:
        tools = ToolBus()
        sandbox = RunbookSandbox(human_confirmed=human_confirmed_destructive)
        # Disk-full style runbooks should recover; migration near-miss should not
        # get a chance to "succeed" after sandbox block.
        agent = OnCallAgent(tools=tools, sandbox=sandbox, assume_runbook_recovers=True)
        result = agent.run(fixture)
        actual = result.state.outcome.value
        passed = actual == fixture.expected_outcome
        cases.append(
            EvalCaseResult(
                incident_id=fixture.incident_id,
                expected=fixture.expected_outcome,
                actual=actual,
                passed=passed,
                sandbox_blocked=bool(result.state.sandbox_blocks),
                paged_human=result.state.paged_human,
                notes=fixture.notes,
            )
        )

    passed = sum(1 for c in cases if c.passed)
    return HarnessReport(
        total=len(cases),
        passed=passed,
        failed=len(cases) - passed,
        cases=cases,
    )


def default_fixtures_path() -> Path:
    return Path(__file__).resolve().parent.parent / "fixtures" / "incidents.json"
