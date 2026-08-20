from __future__ import annotations

from dataclasses import dataclass

from oncall_agent.runbooks import Runbook, search_runbooks
from oncall_agent.sandbox import RunbookSandbox
from oncall_agent.state import IncidentOutcome, IncidentState
from oncall_agent.tools import IncidentFixture, ToolBus


@dataclass
class RunResult:
    state: IncidentState
    slack_thread: str


class OnCallAgent:
    """
    Explicit multi-step on-call graph:

        diagnose → (sev gate | runbook search) → execute_runbook → evaluate
                 ↘ escalate ↗

    SEV1/SEV2 always escalate after context gathering (article severity gate).
    """

    CONFIDENCE_THRESHOLD = 0.55
    AUTO_RESOLVE_MIN_SEVERITY = 3  # only SEV3+ may auto-resolve

    def __init__(
        self,
        tools: ToolBus | None = None,
        sandbox: RunbookSandbox | None = None,
        *,
        assume_runbook_recovers: bool = True,
    ) -> None:
        self.tools = tools or ToolBus()
        self.sandbox = sandbox or RunbookSandbox()
        self.assume_runbook_recovers = assume_runbook_recovers

    def run(self, fixture: IncidentFixture) -> RunResult:
        state = IncidentState(
            incident_id=fixture.incident_id,
            severity=fixture.severity,
            affected_service=fixture.affected_service,
            title=fixture.title,
        )
        self._diagnose(state, fixture)

        if self._should_escalate_for_severity(state):
            return self._escalate(
                state,
                reason=f"SEV{state.severity} always pages a human (severity gate)",
            )

        runbook, confidence = search_runbooks(
            state.affected_service, state.title, state.log_summary
        )
        state.runbook_match = runbook.name if runbook else None
        state.runbook_confidence = confidence
        state.trace(
            f"Runbook search: match={state.runbook_match!r} confidence={confidence:.2f}"
        )

        if runbook is None or confidence < self.CONFIDENCE_THRESHOLD:
            return self._escalate(
                state,
                reason="No confident runbook match — escalating with context",
            )

        return self._execute_and_evaluate(state, runbook)

    def _diagnose(self, state: IncidentState, fixture: IncidentFixture) -> None:
        incident = self.tools.pagerduty_get_incident(fixture)
        state.trace(
            f"PagerDuty: id={incident['id']} sev={incident['severity']} "
            f"service={incident['service']}"
        )

        metrics = self.tools.datadog_query_metrics(fixture.affected_service)
        # Prefer fixture metrics when provided so replay harness is deterministic.
        if fixture.metrics:
            metrics = {**metrics, **fixture.metrics}
        state.metrics_summary = ", ".join(f"{k}={v}" for k, v in metrics.items())
        state.trace(f"Datadog metrics: {state.metrics_summary}")

        logs = self.tools.datadog_get_logs(fixture)
        state.log_summary = " | ".join(logs[:5])
        state.trace(f"Datadog logs (sample): {state.log_summary}")

    def _should_escalate_for_severity(self, state: IncidentState) -> bool:
        return state.severity <= 2

    def _execute_and_evaluate(self, state: IncidentState, runbook: Runbook) -> RunResult:
        state.resolution_attempted = True
        state.trace(f"Attempting runbook '{runbook.name}' ({len(runbook.steps)} steps)")

        for step in runbook.steps:
            result = self.sandbox.execute(step)
            if result.is_destructive:
                state.destructive_flags.append(step)
                state.trace(f"Destructive classifier flagged: {step!r}")

            if not result.allowed:
                state.sandbox_blocks.append(result.reason)
                state.trace(f"Sandbox blocked: {result.reason}")
                return self._escalate(
                    state,
                    reason=f"Sandbox blocked runbook step: {result.reason}",
                )

            state.trace(f"Sandbox executed: {step}")

        if self.assume_runbook_recovers:
            self.tools.simulate_metric_recovery(
                state.affected_service, recovered=True
            )

        metrics = self.tools.datadog_query_metrics(state.affected_service)
        recovered = self._metrics_look_healthy(metrics)
        state.trace(f"Post-runbook metrics: {metrics} recovered={recovered}")

        if recovered:
            return self._resolve(state)

        return self._escalate(
            state,
            reason="Runbook ran but triggering metrics did not recover",
        )

    def _metrics_look_healthy(self, metrics: dict[str, float]) -> bool:
        if metrics.get("error_rate", 0) > 0.05:
            return False
        if metrics.get("disk_pct", 0) > 90:
            return False
        if metrics.get("memory_pct", 0) > 90:
            return False
        if metrics.get("lock_wait_ms", 0) > 1000:
            return False
        return True

    def _resolve(self, state: IncidentState) -> RunResult:
        state.outcome = IncidentOutcome.RESOLVED
        self.tools.resolve_incident(state.incident_id)
        summary = self._format_trace(state, header="AUTO-RESOLVED")
        self.tools.slack_notify("incidents", summary)
        state.slack_posts.append(summary)
        state.trace("Resolved PagerDuty incident and posted Slack summary")
        return RunResult(state=state, slack_thread=summary)

    def _escalate(self, state: IncidentState, *, reason: str) -> RunResult:
        state.outcome = IncidentOutcome.ESCALATED
        state.paged_human = True
        self.tools.escalate_to_human(state.incident_id, reason)
        state.trace(f"Escalating: {reason}")
        summary = self._format_trace(state, header="ESCALATED — human context pack")
        self.tools.slack_notify("incidents", summary)
        state.slack_posts.append(summary)
        return RunResult(state=state, slack_thread=summary)

    def _format_trace(self, state: IncidentState, *, header: str) -> str:
        lines = [
            f"[{header}] {state.incident_id} SEV{state.severity} "
            f"service={state.affected_service}",
            f"Title: {state.title}",
            f"Outcome: {state.outcome.value}",
            "Reasoning trace:",
        ]
        for i, step in enumerate(state.reasoning_trace, 1):
            lines.append(f"  {i}. {step}")
        return "\n".join(lines)
