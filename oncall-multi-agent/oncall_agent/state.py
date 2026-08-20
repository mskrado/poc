from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


class IncidentOutcome(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class IncidentState:
    """Explicit state shape for the on-call agent graph (article IncidentState)."""

    incident_id: str
    severity: int  # 1 = worst
    affected_service: str
    title: str = ""
    metrics_summary: str = ""
    log_summary: str = ""
    runbook_match: Optional[str] = None
    runbook_confidence: float = 0.0
    resolution_attempted: bool = False
    outcome: IncidentOutcome = IncidentOutcome.PENDING
    reasoning_trace: list[str] = field(default_factory=list)
    sandbox_blocks: list[str] = field(default_factory=list)
    destructive_flags: list[str] = field(default_factory=list)
    slack_posts: list[str] = field(default_factory=list)
    paged_human: bool = False

    def trace(self, message: str) -> None:
        self.reasoning_trace.append(message)


OutcomeLiteral = Literal["resolved", "escalated", "failed", "pending"]
