"""Naive 'reasoning-first' loop — full tool list, silent retries, no FSM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from agent_fsm.tools import TOOLS_BY_STATE


ALL_TOOLS = sorted({tool for tools in TOOLS_BY_STATE.values() for tool in tools})


@dataclass
class NaiveRunResult:
    steps: int
    tokens_burned: int
    finished: bool
    final_output: Optional[str]
    ghost_state_retries: int
    notes: list[str] = field(default_factory=list)


ModelOutput = Callable[[int, tuple[str, ...], dict[str, Any]], Optional[str]]


class NaiveReasoningAgent:
    """
    Framework-style agent: same tools every step, re-prompt on bad output.

    Mirrors the failure modes the article warns about:
    - leaky tool permissions
    - ghost states silently retried
    - no turn ceiling by default
    """

    def __init__(self, *, max_steps: Optional[int] = None) -> None:
        self.max_steps = max_steps

    def run(self, document: dict[str, Any], model_fn: ModelOutput) -> NaiveRunResult:
        steps = 0
        tokens = 0
        ghost_retries = 0
        notes: list[str] = []
        final_output: Optional[str] = None
        finished = False

        while not finished:
            steps += 1
            tokens += 1200  # simulated prompt + tool schema cost every step

            if self.max_steps is not None and steps > self.max_steps:
                notes.append(f"Stopped after {self.max_steps} steps with no resolution")
                break

            output = model_fn(steps, tuple(ALL_TOOLS), document)
            if output is None:
                ghost_retries += 1
                notes.append(f"Step {steps}: unparseable output — re-prompting silently")
                tokens += 800
                continue

            if output == "DONE":
                finished = True
                final_output = output
            elif output == "ERROR":
                finished = True
                final_output = output
            else:
                notes.append(f"Step {steps}: model emitted '{output}' — continuing loop")

        return NaiveRunResult(
            steps=steps,
            tokens_burned=tokens,
            finished=finished,
            final_output=final_output,
            ghost_state_retries=ghost_retries,
            notes=notes,
        )
