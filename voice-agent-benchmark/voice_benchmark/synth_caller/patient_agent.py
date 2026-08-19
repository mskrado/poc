from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from voice_benchmark.models import PatientRecord


@dataclass(frozen=True)
class PatientReply:
    text: str
    end_call: bool = False
    interrupt: bool = False


# Rule-based scripted responses for dry-run / tests (no LLM required).
PERSONA_SCRIPT: dict[str, list[PatientReply]] = {
    "cooperative": [
        PatientReply("Hello?"),
        PatientReply("Yes, that's correct — I'll be there."),
        PatientReply("No questions, thank you."),
        PatientReply("Goodbye!", end_call=True),
    ],
    "rescheduler": [
        PatientReply("Hi, this is Maria."),
        PatientReply("Actually I need to reschedule. Do you have Thursday at 10?"),
        PatientReply("Thursday 10am works, thanks."),
        PatientReply("Bye.", end_call=True),
    ],
    "confused": [
        PatientReply("Hello?"),
        PatientReply("Wait, which date did you say?"),
        PatientReply("Oh — March 13th at 11, got it."),
        PatientReply("Okay, thanks.", end_call=True),
    ],
    "wants_human": [
        PatientReply("Hello?"),
        PatientReply("I'd rather talk to a real person please.", interrupt=True),
        PatientReply("Please connect me to someone.", end_call=True),
    ],
}


class PatientAgent:
    """Simulated callee ('SynthCaller') for benchmark conversations."""

    def __init__(self, scenario: dict[str, Any] | None = None):
        self._scenario = scenario or {}
        self._turn_index: dict[str, int] = {}

    def reset(self, call_id: str) -> None:
        self._turn_index[call_id] = 0

    def respond(self, patient: PatientRecord, call_id: str, agent_prompt: str = "") -> PatientReply:
        persona = patient.persona
        script = PERSONA_SCRIPT.get(persona)
        if not script:
            default = self._scenario.get("patient_behavior", {}).get("default_persona", "cooperative")
            script = PERSONA_SCRIPT.get(default, PERSONA_SCRIPT["cooperative"])

        idx = self._turn_index.get(call_id, 0)
        reply = script[min(idx, len(script) - 1)]
        self._turn_index[call_id] = idx + 1
        return reply

    @staticmethod
    def list_personas(scenario: dict[str, Any] | None = None) -> list[str]:
        if scenario and "patient_behavior" in scenario:
            personas = scenario["patient_behavior"].get("personas", {})
            if personas:
                return list(personas.keys())
        return list(PERSONA_SCRIPT.keys())
