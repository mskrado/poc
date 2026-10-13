"""Noah's rule, in code: on a person-facing step a low score can only route
to a human reviewer. There is no code path that rejects."""
import inspect
import itertools

import pytest

from gate import policy
from gate.types import Action, GateDecision, GateSignalType

SCORES = [i / 100 for i in range(0, 101)]
THRESHOLDS = [0.5, 0.8, 0.95]


def test_action_enum_has_no_rejection():
    banned = ("REJECT", "DENY", "DECLINE", "DISQUALIFY", "FAIL")
    for a in Action:
        assert not any(b in a.name for b in banned), a


def test_person_facing_low_score_only_routes_to_human():
    for s, t in itertools.product(SCORES, THRESHOLDS):
        expected = Action.CONTINUE if s >= t else Action.ROUTE_HUMAN
        assert policy.decide_person_facing(s, t) is expected
        assert policy.decide_stop(s, t, person_facing=True) is expected
        assert policy.decide_label(s, t, person_facing=True) is expected
        for choice in ("small_model", "frontier", "human", "anything_else"):
            a = policy.decide_route(choice, s, t, person_facing=True)
            if s < t:
                assert a is Action.ROUTE_HUMAN


def test_person_facing_never_stops_the_persons_process():
    # a STOP on a person-facing step is a silent rejection, so it must be impossible
    for s, t in itertools.product(SCORES, THRESHOLDS):
        assert policy.decide_stop(s, t, person_facing=True) is not Action.STOP


def test_gate_decision_refuses_non_human_action_on_low_person_facing_score():
    with pytest.raises(ValueError):
        GateDecision("hiring_screen", GateSignalType.STOP, "false", 0.1, 0.8, Action.STOP, True)
    with pytest.raises(ValueError):
        GateDecision("hiring_screen", GateSignalType.ROUTE, "frontier", 0.1, 0.8, Action.ROUTE_FRONTIER, True)
    ok = GateDecision("hiring_screen", GateSignalType.STOP, "false", 0.1, 0.8, Action.ROUTE_HUMAN, True)
    assert ok.action is Action.ROUTE_HUMAN


def test_no_reject_string_in_policy_source():
    src = inspect.getsource(policy).lower()
    for word in ("reject", "deny", "decline"):
        # the word may appear in comments explaining the rule, never as a returned value
        assert f'"{word}' not in src and f"'{word}" not in src
