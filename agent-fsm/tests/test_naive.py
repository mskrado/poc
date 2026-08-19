from agent_naive import NaiveReasoningAgent


def test_naive_agent_retries_ghost_outputs_and_never_finishes():
    agent = NaiveReasoningAgent(max_steps=10)
    document = {"parties": ["A"], "termination_clause": "TBD"}

    def model_fn(step, tools, doc):
        if step <= 2:
            return "CALL extract_fields"
        return None

    result = agent.run(document, model_fn)
    assert not result.finished
    assert result.ghost_state_retries >= 7
    assert result.tokens_burned > 8000


def test_naive_agent_passes_full_tool_catalog_every_step():
    agent = NaiveReasoningAgent(max_steps=1)
    seen_tool_counts: list[int] = []

    def model_fn(step, tools, doc):
        seen_tool_counts.append(len(tools))
        return "ERROR"

    agent.run({}, model_fn)
    assert seen_tool_counts[0] >= 6  # all tools from every state combined
