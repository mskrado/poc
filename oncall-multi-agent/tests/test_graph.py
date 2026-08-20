from oncall_agent.graph import OnCallAgent
from oncall_agent.sandbox import RunbookSandbox
from oncall_agent.state import IncidentOutcome
from oncall_agent.tools import IncidentFixture, ToolBus


def _agent(**kwargs) -> OnCallAgent:
    return OnCallAgent(
        tools=ToolBus(),
        sandbox=RunbookSandbox(human_confirmed=False),
        **kwargs,
    )


class TestSeverityGate:
    def test_sev1_always_escalates(self):
        fixture = IncidentFixture(
            incident_id="S1",
            severity=1,
            affected_service="api-gateway",
            title="Outage",
            metrics={"error_rate": 0.5},
            logs=["5xx"],
            expected_outcome="escalated",
        )
        result = _agent().run(fixture)
        assert result.state.outcome == IncidentOutcome.ESCALATED
        assert result.state.paged_human
        assert any("severity gate" in t.lower() for t in result.state.reasoning_trace)

    def test_sev2_always_escalates(self):
        fixture = IncidentFixture(
            incident_id="S2",
            severity=2,
            affected_service="api-gateway",
            title="Degradation",
            metrics={"error_rate": 0.1},
            logs=["latency"],
            expected_outcome="escalated",
        )
        result = _agent().run(fixture)
        assert result.state.outcome == IncidentOutcome.ESCALATED


class TestAutoResolve:
    def test_disk_full_resolves(self):
        fixture = IncidentFixture(
            incident_id="D1",
            severity=3,
            affected_service="app-worker",
            title="Disk full ENOSPC",
            metrics={"disk_pct": 97, "error_rate": 0.02},
            logs=["ENOSPC: no space left on device"],
            expected_outcome="resolved",
        )
        result = _agent().run(fixture)
        assert result.state.outcome == IncidentOutcome.RESOLVED
        assert result.state.runbook_match == "disk-full-cleanup"
        assert "AUTO-RESOLVED" in result.slack_thread


class TestNearDisaster:
    def test_migration_runbook_blocked_by_sandbox(self):
        fixture = IncidentFixture(
            incident_id="M1",
            severity=3,
            affected_service="migration-service",
            title="Stuck migration lock",
            metrics={"lock_wait_ms": 45000},
            logs=["migration lock", "restart the migration service"],
            expected_outcome="escalated",
        )
        # human_confirmed=True would still block postgresql-primary (not allowlisted)
        result = _agent().run(fixture)
        assert result.state.outcome == IncidentOutcome.ESCALATED
        assert result.state.sandbox_blocks
        assert any("postgresql-primary" in b for b in result.state.sandbox_blocks)
