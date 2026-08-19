from agent_fsm.states import AgentState


TOOLS_BY_STATE: dict[AgentState, tuple[str, ...]] = {
    AgentState.INIT: ("load_document",),
    AgentState.EXTRACTING: ("extract_fields",),
    AgentState.VALIDATING: ("validate_schema", "check_confidence"),
    AgentState.ROUTING: ("route_to_queue", "mark_complete"),
    AgentState.ESCALATING: ("enqueue_human_review",),
    AgentState.DONE: (),
    AgentState.ERROR: ("emit_error_metric",),
}


def tools_for_state(state: AgentState) -> tuple[str, ...]:
    return TOOLS_BY_STATE.get(state, ())
