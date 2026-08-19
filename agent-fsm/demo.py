#!/usr/bin/env python3
"""Run side-by-side FSM vs naive agent scenarios from the roiscale article."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from agent_fsm.orchestrator import DocumentProcessingAgent
from agent_fsm.states import AgentState
from agent_naive import NaiveReasoningAgent


@dataclass
class ScriptedDecision:
    target_state: AgentState
    model_output: str
    trigger: str
    escalation_reason: str = ""


FIXTURES: dict[str, dict[str, Any]] = {
    "clean-contract": {
        "parties": ["Acme Corp", "Globex LLC"],
        "termination_clause": "Either party may terminate with 30 days notice.",
        "value_usd": 120_000,
        "extraction_confidence": 0.96,
    },
    "ambiguous-termination": {
        "parties": ["Northwind Traders"],
        "termination_clause": "Termination terms TBD pending legal review.",
        "value_usd": 45_000,
        "extraction_confidence": 0.62,
    },
    "missing-parties": {
        "parties": [],
        "termination_clause": "Standard termination applies.",
        "value_usd": 10_000,
        "extraction_confidence": 0.88,
    },
}


def happy_path_script(step: int) -> ScriptedDecision:
    sequence = [
        ScriptedDecision(AgentState.EXTRACTING, "tool:extract_fields", "init_load"),
        ScriptedDecision(AgentState.VALIDATING, "tool:validate_schema", "extract_complete"),
        ScriptedDecision(AgentState.ROUTING, "validation_passed", "validate_complete"),
        ScriptedDecision(AgentState.DONE, "tool:mark_complete", "route_auto"),
    ]
    return sequence[min(step, len(sequence) - 1)]


def low_confidence_script(step: int) -> ScriptedDecision:
    sequence = [
        ScriptedDecision(AgentState.EXTRACTING, "tool:extract_fields", "init_load"),
        ScriptedDecision(AgentState.VALIDATING, "tool:validate_schema", "extract_complete"),
        ScriptedDecision(AgentState.ROUTING, "validation_passed", "validate_complete"),
        ScriptedDecision(
            AgentState.ESCALATING,
            "confidence_below_threshold",
            "route_policy",
            escalation_reason="Low confidence on termination clause",
        ),
    ]
    return sequence[min(step, len(sequence) - 1)]


def retry_then_error_script(step: int) -> ScriptedDecision:
    # validation fails twice -> retry extraction -> third retry blocked by FSM
    sequence = [
        ScriptedDecision(AgentState.EXTRACTING, "tool:extract_fields", "init_load"),
        ScriptedDecision(AgentState.VALIDATING, "tool:validate_schema", "extract_v1"),
        ScriptedDecision(AgentState.EXTRACTING, "retry_extraction", "validation_failed"),
        ScriptedDecision(AgentState.VALIDATING, "tool:validate_schema", "extract_v2"),
        ScriptedDecision(AgentState.EXTRACTING, "retry_extraction", "validation_failed"),
        ScriptedDecision(AgentState.VALIDATING, "tool:validate_schema", "extract_v3"),
    ]
    return sequence[min(step, len(sequence) - 1)]


def ghost_state_script(step: int) -> ScriptedDecision:
    sequence = [
        ScriptedDecision(AgentState.EXTRACTING, "tool:extract_fields", "init_load"),
        ScriptedDecision(AgentState.ROUTING, "tool:route_to_queue", "skip_validation"),
    ]
    return sequence[min(step, len(sequence) - 1)]


def run_fsm(name: str, fixture_key: str, script_fn) -> dict[str, Any]:
    agent = DocumentProcessingAgent()
    document = FIXTURES[fixture_key]
    step = 0

    def model_fn(ctx, tools, doc):
        nonlocal step
        decision = script_fn(step)
        step += 1
        return decision

    result = agent.run(f"doc-{name}", document, model_fn, max_turns=8)
    ctx = result.context
    return {
        "agent": "explicit_fsm",
        "scenario": name,
        "final_state": ctx.state.name,
        "turns": ctx.turns,
        "extraction_retries": ctx.extraction_retries,
        "confidence": ctx.confidence,
        "reviewer_summary": result.reviewer_summary,
        "audit_trail": [
            {
                "turn": r.turn,
                "from": r.from_state.name,
                "to": r.to_state.name,
                "tools": list(r.tools_available),
                "trigger": r.trigger,
            }
            for r in ctx.audit_log
        ],
    }


def run_naive(name: str, fixture_key: str, *, max_steps: int | None = None) -> dict[str, Any]:
    agent = NaiveReasoningAgent(max_steps=max_steps)
    document = FIXTURES[fixture_key]

    def model_fn(step, tools, doc):
        # Simulates a model that sometimes emits ghost states and never terminates
        if step <= 3:
            return "CALL extract_fields"
        if step <= 6:
            return None  # ghost output -> silent retry
        if step == 7:
            return "CALL route_to_queue"  # wrong phase, keeps looping
        return None

    result = agent.run(document, model_fn)
    return {
        "agent": "naive_loop",
        "scenario": name,
        "steps": result.steps,
        "tokens_burned": result.tokens_burned,
        "finished": result.finished,
        "ghost_state_retries": result.ghost_state_retries,
        "notes": result.notes,
    }


SCENARIOS = {
    "happy-path": ("clean-contract", happy_path_script),
    "low-confidence-escalation": ("ambiguous-termination", low_confidence_script),
    "validation-retry-limit": ("missing-parties", retry_then_error_script),
    "ghost-state-blocked": ("clean-contract", ghost_state_script),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=[*SCENARIOS.keys(), "all", "compare-naive"],
        default="all",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    outputs: list[dict[str, Any]] = []

    if args.scenario == "compare-naive":
        outputs.append(run_naive("runaway-loop", "ambiguous-termination", max_steps=12))
        outputs.append(run_fsm("happy-path", *SCENARIOS["happy-path"]))
    elif args.scenario == "all":
        for name, (fixture_key, script_fn) in SCENARIOS.items():
            outputs.append(run_fsm(name, fixture_key, script_fn))
        outputs.append(run_naive("runaway-loop", "ambiguous-termination", max_steps=12))
    else:
        fixture_key, script_fn = SCENARIOS[args.scenario]
        outputs.append(run_fsm(args.scenario, fixture_key, script_fn))

    if args.json:
        print(json.dumps(outputs, indent=2))
        return

    for item in outputs:
        print(f"\n=== {item['agent']} :: {item.get('scenario')} ===")
        for key, value in item.items():
            if key in ("agent", "scenario"):
                continue
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
