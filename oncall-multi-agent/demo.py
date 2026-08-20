#!/usr/bin/env python3
"""Run on-call multi-agent scenarios from the roiscale article."""

from __future__ import annotations

import argparse
import json

from oncall_agent.graph import OnCallAgent
from oncall_agent.harness import default_fixtures_path, load_fixtures, run_harness
from oncall_agent.sandbox import RunbookSandbox
from oncall_agent.tools import IncidentFixture, ToolBus


def print_result(label: str, result) -> None:
    state = result.state
    print(f"\n=== {label} ===")
    print(f"outcome: {state.outcome.value}")
    print(f"paged_human: {state.paged_human}")
    print(f"runbook: {state.runbook_match} (confidence={state.runbook_confidence:.2f})")
    if state.sandbox_blocks:
        print(f"sandbox_blocks: {state.sandbox_blocks}")
    if state.destructive_flags:
        print(f"destructive_flags: {state.destructive_flags}")
    print("--- Slack thread ---")
    print(result.slack_thread)


def run_live_scenarios() -> None:
    scenarios = [
        (
            "disk-full-autoresolve",
            IncidentFixture(
                incident_id="LIVE-1",
                severity=3,
                affected_service="app-worker",
                title="Disk full — ENOSPC",
                metrics={"disk_pct": 97, "error_rate": 0.03},
                logs=["ENOSPC: no space left on device"],
                expected_outcome="resolved",
            ),
        ),
        (
            "sev1-severity-gate",
            IncidentFixture(
                incident_id="LIVE-2",
                severity=1,
                affected_service="api-gateway",
                title="Customer outage",
                metrics={"error_rate": 0.5},
                logs=["5xx spike"],
                expected_outcome="escalated",
            ),
        ),
        (
            "near-disaster-migration",
            IncidentFixture(
                incident_id="LIVE-3",
                severity=3,
                affected_service="migration-service",
                title="Stuck migration lock",
                metrics={"lock_wait_ms": 45000},
                logs=["migration lock", "restart the migration service"],
                expected_outcome="escalated",
            ),
        ),
    ]

    for name, fixture in scenarios:
        agent = OnCallAgent(tools=ToolBus(), sandbox=RunbookSandbox())
        print_result(name, agent.run(fixture))


def run_eval(as_json: bool) -> None:
    fixtures = load_fixtures(default_fixtures_path())
    report = run_harness(fixtures)
    if as_json:
        payload = {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "pass_rate": report.pass_rate,
            "cases": [c.__dict__ for c in report.cases],
        }
        print(json.dumps(payload, indent=2))
        return

    print(f"\n=== Historical incident harness ===")
    print(f"pass_rate: {report.pass_rate:.0%} ({report.passed}/{report.total})")
    for case in report.cases:
        mark = "PASS" if case.passed else "FAIL"
        print(
            f"  [{mark}] {case.incident_id}: expected={case.expected} "
            f"actual={case.actual} sandbox_blocked={case.sandbox_blocked}"
        )
        if case.notes:
            print(f"         note: {case.notes}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=["live", "harness", "all"],
        default="all",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.scenario in ("live", "all"):
        run_live_scenarios()
    if args.scenario in ("harness", "all"):
        run_eval(args.json)


if __name__ == "__main__":
    main()
