from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from agent_fsm.states import AgentState


@dataclass(frozen=True)
class TransitionRecord:
    """One logged state transition for diagnostics and human review."""

    turn: int
    from_state: AgentState
    to_state: AgentState
    trigger: str
    model_output: str
    tools_available: tuple[str, ...]


@dataclass
class AgentContext:
    """State-aware context that survives failures for post-mortems."""

    document_id: str
    state: AgentState = AgentState.INIT
    extracted: Optional[dict[str, Any]] = None
    validation_errors: list[str] = field(default_factory=list)
    confidence: float = 0.0
    turns: int = 0
    max_turns: int = 8
    extraction_retries: int = 0
    max_extraction_retries: int = 2
    audit_log: list[TransitionRecord] = field(default_factory=list)
    escalation_reason: str = ""
