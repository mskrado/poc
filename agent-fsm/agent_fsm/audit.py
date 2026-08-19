from agent_fsm.context import AgentContext
from agent_fsm.states import AgentState


def summarize_for_reviewer(ctx: AgentContext) -> str:
    """Plain-English escalation summary for human reviewers."""
    if ctx.state == AgentState.DONE and not ctx.escalation_reason:
        return (
            f"Document {ctx.document_id} completed automatically in {ctx.turns} turn(s) "
            f"with {ctx.confidence:.0%} confidence."
        )

    attempts = ctx.extraction_retries + (1 if ctx.extracted else 0)
    parts = [
        f"The agent processed document {ctx.document_id} over {ctx.turns} turn(s).",
    ]

    if ctx.extraction_retries:
        parts.append(
            f"It re-ran extraction {ctx.extraction_retries} time(s) after validation failures."
        )
    elif attempts:
        parts.append("It completed extraction once.")

    if ctx.validation_errors:
        parts.append(
            "Validation issues: " + "; ".join(ctx.validation_errors) + "."
        )

    if ctx.confidence < 0.85:
        parts.append(
            f"Confidence on key fields was low ({ctx.confidence:.0%})."
        )

    if ctx.escalation_reason:
        parts.append(ctx.escalation_reason + ".")

    if ctx.state == AgentState.ESCALATING:
        parts.append("The task was escalated to a human reviewer.")
    elif ctx.state == AgentState.ERROR:
        parts.append("The agent entered ERROR and stopped.")
    elif ctx.state == AgentState.DONE and ctx.escalation_reason:
        parts.append("A human completed the review after escalation.")

    return " ".join(parts)
