from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

from agent_fsm.audit import summarize_for_reviewer
from agent_fsm.context import AgentContext
from agent_fsm.states import AgentState
from agent_fsm.tools import tools_for_state
from agent_fsm.transitions import InvalidTransitionError, transition


class ModelDecision(Protocol):
    """Simulated LLM output: next state plus side effects on context."""

    target_state: AgentState
    model_output: str
    trigger: str


ModelFn = Callable[[AgentContext, tuple[str, ...], dict[str, Any]], ModelDecision]


@dataclass
class RunResult:
    context: AgentContext
    reviewer_summary: str


class DocumentProcessingAgent:
    """Document processing agent with explicit FSM orchestration."""

    TERMINAL = frozenset({AgentState.DONE, AgentState.ERROR})

    def run(
        self,
        document_id: str,
        document: dict[str, Any],
        model_fn: ModelFn,
        *,
        max_turns: int = 8,
    ) -> RunResult:
        ctx = AgentContext(document_id=document_id, max_turns=max_turns)

        while ctx.state not in self.TERMINAL:
            tools = tools_for_state(ctx.state)
            decision = model_fn(ctx, tools, document)
            self._apply_side_effects(ctx, decision, document)
            try:
                ctx = transition(
                    ctx,
                    decision.target_state,
                    trigger=decision.trigger,
                    model_output=decision.model_output,
                    tools_available=tools,
                )
            except InvalidTransitionError as exc:
                ctx.escalation_reason = (
                    f"Ghost state blocked: {exc.current.name} -> {exc.target.name}"
                )
                ctx.state = AgentState.ERROR
                break

            if ctx.state == AgentState.ESCALATING:
                if not ctx.escalation_reason:
                    ctx.escalation_reason = "Low confidence or routing policy"
                break

        if ctx.state == AgentState.ESCALATING:
            ctx = transition(
                ctx,
                AgentState.DONE,
                trigger="human_queue_resolved",
                model_output="Reviewer accepted escalated document",
                tools_available=tools_for_state(AgentState.ESCALATING),
            )

        return RunResult(context=ctx, reviewer_summary=summarize_for_reviewer(ctx))

    def _apply_side_effects(
        self,
        ctx: AgentContext,
        decision: ModelDecision,
        document: dict[str, Any],
    ) -> None:
        if decision.target_state == AgentState.EXTRACTING and ctx.state in (
            AgentState.INIT,
            AgentState.VALIDATING,
        ):
            ctx.extracted = {
                "parties": document.get("parties", []),
                "termination_clause": document.get("termination_clause", ""),
                "value_usd": document.get("value_usd"),
            }
            ctx.confidence = float(document.get("extraction_confidence", 0.9))

        if decision.target_state == AgentState.VALIDATING:
            errors = []
            if not ctx.extracted or not ctx.extracted.get("parties"):
                errors.append("missing parties")
            if not ctx.extracted or not ctx.extracted.get("termination_clause"):
                errors.append("missing termination clause")
            ctx.validation_errors = errors

        if decision.target_state == AgentState.ROUTING and ctx.validation_errors:
            ctx.confidence = min(ctx.confidence, 0.5)

        if decision.target_state == AgentState.ESCALATING:
            ctx.escalation_reason = getattr(decision, "escalation_reason", "") or ctx.escalation_reason


# Re-export for convenience
__all__ = ["DocumentProcessingAgent", "InvalidTransitionError", "RunResult"]
