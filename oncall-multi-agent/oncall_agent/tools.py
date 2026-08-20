from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IncidentFixture:
    incident_id: str
    severity: int
    affected_service: str
    title: str
    metrics: dict[str, float]
    logs: list[str]
    # Expected routing for the eval harness
    expected_outcome: str
    notes: str = ""


# Synthetic telemetry keyed by service — mock Datadog.
SERVICE_METRICS: dict[str, dict[str, float]] = {
    "api-gateway": {"error_rate": 0.02, "p99_ms": 180, "disk_pct": 62},
    "app-worker": {"error_rate": 0.01, "queue_depth": 12, "disk_pct": 97},
    "cache-sidecar": {"error_rate": 0.08, "memory_pct": 94, "hit_ratio": 0.41},
    "migration-service": {"error_rate": 0.15, "lock_wait_ms": 45000, "disk_pct": 55},
    "log-shipper": {"error_rate": 0.03, "disk_pct": 98, "lag_s": 120},
}


@dataclass
class ToolBus:
    """Mock integrations: PagerDuty, Datadog, Slack, runbook execute."""

    resolved_incidents: list[str] = field(default_factory=list)
    escalations: list[str] = field(default_factory=list)
    slack_messages: list[str] = field(default_factory=list)
    metric_overrides: dict[str, dict[str, float]] = field(default_factory=dict)

    def pagerduty_get_incident(self, fixture: IncidentFixture) -> dict:
        return {
            "id": fixture.incident_id,
            "severity": fixture.severity,
            "service": fixture.affected_service,
            "title": fixture.title,
        }

    def datadog_query_metrics(self, service: str) -> dict[str, float]:
        base = dict(SERVICE_METRICS.get(service, {"error_rate": 0.0}))
        base.update(self.metric_overrides.get(service, {}))
        return base

    def datadog_get_logs(self, fixture: IncidentFixture) -> list[str]:
        return list(fixture.logs)

    def slack_notify(self, channel: str, message: str) -> None:
        self.slack_messages.append(f"#{channel}: {message}")

    def escalate_to_human(self, incident_id: str, reason: str) -> None:
        self.escalations.append(f"{incident_id}: {reason}")

    def resolve_incident(self, incident_id: str) -> None:
        self.resolved_incidents.append(incident_id)

    def simulate_metric_recovery(self, service: str, *, recovered: bool) -> None:
        """After a successful runbook, optionally flip metrics to healthy."""
        if recovered:
            self.metric_overrides[service] = {
                "error_rate": 0.0,
                "disk_pct": 55,
                "memory_pct": 60,
                "lock_wait_ms": 0,
            }
