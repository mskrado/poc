"""Orion's rule, in code: every gate label is a stop or route signal, never a fact check."""
import csv
import json
from pathlib import Path

import pytest

from gate import gates
from gate.types import Action, GateDecision, GateSignalType

ROOT = Path(__file__).resolve().parents[1]


def test_signal_type_enum_is_stop_or_route_only():
    assert {s.value for s in GateSignalType} == {"stop", "route"}


def test_gate_decision_requires_typed_signal():
    with pytest.raises(TypeError):
        GateDecision("x", "verified", "true", 0.9, 0.8, Action.CONTINUE, False)  # type: ignore[arg-type]


def test_no_verification_fields():
    names = set(GateDecision.__dataclass_fields__)
    for bad in ("verified", "is_true", "fact_check", "grounded", "claim_ok"):
        assert bad not in names


class FakeClient:
    def __init__(self, answers):
        self.answers = answers

    def systemone(self, model, state, questions):
        return {"answers": self.answers(questions), "usage": {"input_tokens": 10, "output_tokens": 1}}, 5.0


def _fake(questions):
    out = {}
    for k, q in questions.items():
        if q["type"] == "noul":
            out[k] = {"type": "noul", "noul": 0.3}
        else:
            opts = list(q["criteria"])
            probs = {o: (0.6 if i == 0 else 0.4 / (len(opts) - 1)) for i, o in enumerate(opts)}
            out[k] = {"type": "choice", "choice": opts[0], "probabilities": probs, "confidence": 0.2}
    return out


def test_every_gate_returns_stop_or_route(monkeypatch):
    monkeypatch.setattr(gates, "client", FakeClient(_fake))
    ds = [gates.stop_gate("t", "tool()", "{}"), gates.scope_gate("t", "s"),
          *gates.memory_gates("t", "m"), *gates.triage_gate("ticket", {"A": "a", "B": "b"}),
          gates.intent_gate("ticket", "A", ["x", "y"])]
    for d in ds:
        assert d.signal_type in (GateSignalType.STOP, GateSignalType.ROUTE)
    # low scores on the person-facing triage gates go to a human
    assert all(d.action is Action.ROUTE_HUMAN for d in ds[4:6])
    # low score on a non-person agent step stops the loop
    assert ds[0].action is Action.STOP


@pytest.mark.skipif(not (ROOT / "results" / "results.csv").exists(), reason="run first")
def test_results_file_signal_types():
    with open(ROOT / "results" / "results.csv") as f:
        rows = list(csv.DictReader(f))
    assert rows
    for r in rows:
        assert r["gate_signal_type"] in ("stop", "route", ""), r
        if r["mode"] in ("gate", "code_check"):
            assert r["gate_signal_type"] in ("stop", "route")
        assert r["action"] in ("", "continue", "stop", "route_small", "route_frontier", "route_human")
        # the score never counts as catching a false claim
        assert r["caught_by"] != "score" 
    s = json.loads((ROOT / "results" / "summary.json").read_text())
    assert s["orion_review"]["grounding_check_present"] is False
