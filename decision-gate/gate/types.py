"""Typed gate outputs.

A gate decision is ALWAYS a stop signal or a route signal. It is never a
fact check, verification, or grounding result. There is deliberately no
enum member for "verified", "true", "pass_claim" or similar, and there is
deliberately no action that rejects a person.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GateSignalType(str, Enum):
    STOP = "stop"    # should the loop / step keep going?
    ROUTE = "route"  # where should this item go next?


class Action(str, Enum):
    CONTINUE = "continue"
    STOP = "stop"                     # halt the agent loop and flag a human
    ROUTE_SMALL = "route_small"
    ROUTE_FRONTIER = "route_frontier"
    ROUTE_HUMAN = "route_human"
    # No REJECT / DENY / DECLINE member exists. Do not add one.


@dataclass(frozen=True)
class GateDecision:
    gate: str                       # e.g. "stop_gate", "router_gate"
    signal_type: GateSignalType
    label: str                      # chosen option or "true"/"false"
    score: float                    # probability of the SAFE / chosen answer
    threshold: float
    action: Action
    person_facing: bool
    input_tokens: int = 0
    output_tokens: int = 0
    wall_ms: float = 0.0
    raw: dict = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.signal_type, GateSignalType):
            raise TypeError("signal_type must be GateSignalType (stop|route)")
        if not isinstance(self.action, Action):
            raise TypeError("action must be an Action")
        if self.person_facing and self.score < self.threshold and self.action is not Action.ROUTE_HUMAN:
            raise ValueError(
                "person-facing step with a low score may only route to a human reviewer"
            )
