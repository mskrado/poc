"""Code decides what happens next. The model only supplies a score."""
from __future__ import annotations

from .types import Action

ROUTE_MAP = {
    "small_model": Action.ROUTE_SMALL,
    "frontier": Action.ROUTE_FRONTIER,
    "human": Action.ROUTE_HUMAN,
}


def decide_stop(p_ok: float, threshold: float, person_facing: bool) -> Action:
    """Stop gate. p_ok = probability the step is fine to continue."""
    if p_ok >= threshold:
        return Action.CONTINUE
    # Low score. On a person-facing step we never halt the person's process
    # (a halt is a silent rejection); we hand the file to a human reviewer.
    return Action.ROUTE_HUMAN if person_facing else Action.STOP


def decide_route(choice: str, p_choice: float, threshold: float, person_facing: bool) -> Action:
    """Router gate. Low confidence always goes to a human, never to a reject."""
    if p_choice < threshold:
        return Action.ROUTE_HUMAN
    return ROUTE_MAP.get(choice, Action.ROUTE_HUMAN)


def decide_label(p_choice: float, threshold: float, person_facing: bool) -> Action:
    """Label gate (e.g. triage category): proceed with the label or ask a human."""
    return Action.CONTINUE if p_choice >= threshold else Action.ROUTE_HUMAN


def decide_person_facing(score: float, threshold: float) -> Action:
    """The only decision function allowed on steps that judge a person
    (hiring, credit, eligibility). Returns CONTINUE or ROUTE_HUMAN. Nothing else."""
    return Action.CONTINUE if score >= threshold else Action.ROUTE_HUMAN
