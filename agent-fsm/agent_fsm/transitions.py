from agent_fsm.context import AgentContext, TransitionRecord
from agent_fsm.states import AgentState


TRANSITIONS: dict[AgentState, frozenset[AgentState]] = {
    AgentState.INIT: frozenset({AgentState.EXTRACTING, AgentState.ERROR}),
    AgentState.EXTRACTING: frozenset({AgentState.VALIDATING, AgentState.ERROR}),
    AgentState.VALIDATING: frozenset(
        {AgentState.ROUTING, AgentState.EXTRACTING, AgentState.ERROR}
    ),
    AgentState.ROUTING: frozenset({AgentState.DONE, AgentState.ESCALATING}),
    AgentState.ESCALATING: frozenset({AgentState.DONE}),
    AgentState.DONE: frozenset(),
    AgentState.ERROR: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when model output maps to a transition not in the whitelist."""

    def __init__(self, current: AgentState, target: AgentState) -> None:
        super().__init__(f"Invalid transition: {current.name} -> {target.name}")
        self.current = current
        self.target = target


def allowed_targets(state: AgentState) -> frozenset[AgentState]:
    return TRANSITIONS.get(state, frozenset())


def transition(ctx: AgentContext, target: AgentState, *, trigger: str, model_output: str, tools_available: tuple[str, ...]) -> AgentContext:
    """Apply a whitelisted transition and append an audit record."""
    if target not in allowed_targets(ctx.state):
        raise InvalidTransitionError(ctx.state, target)

    if (
        ctx.state == AgentState.VALIDATING
        and target == AgentState.EXTRACTING
    ):
        ctx.extraction_retries += 1
        if ctx.extraction_retries > ctx.max_extraction_retries:
            raise InvalidTransitionError(ctx.state, target)

    record = TransitionRecord(
        turn=ctx.turns + 1,
        from_state=ctx.state,
        to_state=target,
        trigger=trigger,
        model_output=model_output,
        tools_available=tools_available,
    )
    ctx.audit_log.append(record)
    ctx.state = target
    ctx.turns += 1

    if ctx.turns >= ctx.max_turns and ctx.state not in (AgentState.DONE, AgentState.ERROR):
        ctx.escalation_reason = f"Turn ceiling ({ctx.max_turns}) reached"
        ctx.state = AgentState.ESCALATING

    return ctx
