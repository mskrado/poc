import pytest

from agent_fsm.context import AgentContext
from agent_fsm.orchestrator import DocumentProcessingAgent
from agent_fsm.states import AgentState
from agent_fsm.transitions import InvalidTransitionError, transition
from agent_fsm.tools import tools_for_state


class TestTransitions:
    def test_happy_path_transitions(self):
        ctx = AgentContext(document_id="t1")
        for target in (
            AgentState.EXTRACTING,
            AgentState.VALIDATING,
            AgentState.ROUTING,
            AgentState.DONE,
        ):
            ctx = transition(
                ctx,
                target,
                trigger="test",
                model_output="ok",
                tools_available=tools_for_state(ctx.state),
            )
        assert ctx.state == AgentState.DONE
        assert len(ctx.audit_log) == 4

    def test_ghost_state_rejected(self):
        ctx = AgentContext(document_id="t2", state=AgentState.EXTRACTING)
        with pytest.raises(InvalidTransitionError):
            transition(
                ctx,
                AgentState.ROUTING,
                trigger="skip_validation",
                model_output="bad",
                tools_available=tools_for_state(ctx.state),
            )

    def test_retry_limit_enforced(self):
        ctx = AgentContext(document_id="t3", state=AgentState.VALIDATING)
        ctx = transition(
            ctx,
            AgentState.EXTRACTING,
            trigger="retry1",
            model_output="retry",
            tools_available=tools_for_state(ctx.state),
        )
        ctx.state = AgentState.VALIDATING
        ctx = transition(
            ctx,
            AgentState.EXTRACTING,
            trigger="retry2",
            model_output="retry",
            tools_available=tools_for_state(ctx.state),
        )
        ctx.state = AgentState.VALIDATING
        with pytest.raises(InvalidTransitionError):
            transition(
                ctx,
                AgentState.EXTRACTING,
                trigger="retry3",
                model_output="retry",
                tools_available=tools_for_state(ctx.state),
            )

    def test_turn_ceiling_forces_escalation(self):
        ctx = AgentContext(document_id="t4", max_turns=3, state=AgentState.ROUTING)
        ctx.turns = 2
        ctx = transition(
            ctx,
            AgentState.ESCALATING,
            trigger="policy",
            model_output="escalate",
            tools_available=tools_for_state(ctx.state),
        )
        assert ctx.state == AgentState.ESCALATING


class TestStateScopedTools:
    def test_extracting_does_not_see_routing_tools(self):
        tools = tools_for_state(AgentState.EXTRACTING)
        assert "extract_fields" in tools
        assert "route_to_queue" not in tools
        assert "mark_complete" not in tools


class TestOrchestrator:
    def test_happy_path_completes(self):
        agent = DocumentProcessingAgent()
        document = {
            "parties": ["A", "B"],
            "termination_clause": "30 days notice",
            "extraction_confidence": 0.95,
        }
        step = 0

        def model_fn(ctx, tools, doc):
            nonlocal step
            sequence = [
                type("D", (), {"target_state": AgentState.EXTRACTING, "model_output": "e", "trigger": "t"})(),
                type("D", (), {"target_state": AgentState.VALIDATING, "model_output": "v", "trigger": "t"})(),
                type("D", (), {"target_state": AgentState.ROUTING, "model_output": "r", "trigger": "t"})(),
                type("D", (), {"target_state": AgentState.DONE, "model_output": "d", "trigger": "t"})(),
            ]
            decision = sequence[step]
            step += 1
            return decision

        result = agent.run("doc-1", document, model_fn)
        assert result.context.state == AgentState.DONE
        assert "completed automatically" in result.reviewer_summary.lower()

    def test_ghost_state_enters_error(self):
        agent = DocumentProcessingAgent()
        document = {"parties": ["A"], "termination_clause": "x", "extraction_confidence": 0.9}
        step = 0

        def model_fn(ctx, tools, doc):
            nonlocal step
            sequence = [
                type("D", (), {"target_state": AgentState.EXTRACTING, "model_output": "e", "trigger": "t"})(),
                type("D", (), {"target_state": AgentState.ROUTING, "model_output": "ghost", "trigger": "t"})(),
            ]
            decision = sequence[step]
            step += 1
            return decision

        result = agent.run("doc-2", document, model_fn)
        assert result.context.state == AgentState.ERROR
        assert "Ghost state blocked" in result.context.escalation_reason

    def test_low_confidence_escalates_with_plain_english_summary(self):
        agent = DocumentProcessingAgent()
        document = {
            "parties": ["A"],
            "termination_clause": "TBD",
            "extraction_confidence": 0.6,
        }
        step = 0

        def model_fn(ctx, tools, doc):
            nonlocal step
            sequence = [
                type("D", (), {"target_state": AgentState.EXTRACTING, "model_output": "e", "trigger": "t"})(),
                type("D", (), {"target_state": AgentState.VALIDATING, "model_output": "v", "trigger": "t"})(),
                type("D", (), {"target_state": AgentState.ROUTING, "model_output": "r", "trigger": "t"})(),
                type(
                    "D",
                    (),
                    {
                        "target_state": AgentState.ESCALATING,
                        "model_output": "low",
                        "trigger": "policy",
                        "escalation_reason": "Low confidence on termination clause",
                    },
                )(),
            ]
            decision = sequence[step]
            step += 1
            return decision

        result = agent.run("doc-3", document, model_fn)
        assert result.context.state == AgentState.DONE
        assert "human" in result.reviewer_summary.lower() or "escalated" in result.reviewer_summary.lower()
