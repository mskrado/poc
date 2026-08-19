from __future__ import annotations

import random
import uuid

from voice_benchmark.models import (
    CallRecord,
    ErrorClass,
    EventType,
    PatientRecord,
    StackConfig,
    TurnEvent,
)
from voice_benchmark.stacks.base import StackAdapter
from voice_benchmark.synth_caller.patient_agent import PatientAgent


class MockStackAdapter(StackAdapter):
    """Dry-run simulator calibrated to article reference profiles."""

    name = "mock"

    def __init__(
        self,
        config: StackConfig,
        *,
        scenario: dict | None = None,
        seed: int | None = None,
    ):
        super().__init__(config)
        seed_val = seed if seed is not None else int(config.raw.get("seed", 42))
        self._rng = random.Random(seed_val)
        self._patient = PatientAgent(scenario)

    async def place_call(self, patient: PatientRecord, call_index: int) -> CallRecord:
        call_id = f"mock-{call_index}-{uuid.uuid4().hex[:8]}"
        self._patient.reset(call_id)

        ref = self.config.reference
        base_p95 = ref.p95_turn_latency_ms if ref else 400.0
        error_rate = ref.error_rate if ref else 0.02
        duration = float(self.config.raw.get("duration_seconds", 90))

        if self._rng.random() < error_rate:
            return CallRecord(
                call_id=call_id,
                stack=self.name,
                patient=patient,
                events=[
                    TurnEvent(EventType.ERROR, 1000, "turn-0", call_id),
                    TurnEvent(EventType.CALL_END, 5000, "turn-0", call_id),
                ],
                duration_seconds=5.0,
                error=ErrorClass.UNKNOWN,
                error_detail="simulated failure",
                success=False,
            )

        turns = 4
        events: list[TurnEvent] = []
        t = 0.0
        for turn in range(turns):
            turn_id = f"turn-{turn}"
            reply = self._patient.respond(patient, call_id)

            events.append(TurnEvent(EventType.USER_SPEECH_END, t + 800, turn_id, call_id))
            # Latency drawn around reference p95 with stack-specific jitter
            latency = max(120.0, self._rng.gauss(base_p95 * 0.75, base_p95 * 0.15))
            if reply.interrupt:
                events.append(
                    TurnEvent(
                        EventType.INTERRUPTION,
                        t + 800 + latency * 0.3,
                        turn_id,
                        call_id,
                    )
                )
            events.append(
                TurnEvent(
                    EventType.ASSISTANT_AUDIO_START,
                    t + 800 + latency,
                    turn_id,
                    call_id,
                )
            )
            t += 4000
            if reply.end_call:
                break

        events.append(TurnEvent(EventType.CALL_END, t + 500, f"turn-{turns - 1}", call_id))
        return CallRecord(
            call_id=call_id,
            stack=self.name,
            patient=patient,
            events=events,
            duration_seconds=duration,
            success=True,
        )


class ReferenceStackAdapter(MockStackAdapter):
    """Mock adapter named after a real stack, using that stack's reference profile."""

    def __init__(self, config: StackConfig, *, scenario: dict | None = None):
        super().__init__(config, scenario=scenario, seed=hash(config.stack) % 10000)
