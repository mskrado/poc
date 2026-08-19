from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    USER_SPEECH_END = "user_speech_end"
    ASSISTANT_AUDIO_START = "assistant_audio_start"
    INTERRUPTION = "interruption"
    ERROR = "error"
    CALL_END = "call_end"


class ErrorClass(str, Enum):
    INTERRUPTION_LOOP = "interruption_loop"
    VAD_MISCONFIG = "vad_misconfiguration"
    RATE_LIMIT = "rate_limit"
    DROPPED_CALL = "dropped_call"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PatientRecord:
    name: str
    phone: str
    persona: str
    appointment: str


@dataclass(frozen=True)
class TurnEvent:
    event_type: EventType
    timestamp_ms: float
    turn_id: str
    call_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnLatency:
    turn_id: str
    call_id: str
    latency_ms: float


@dataclass
class CallRecord:
    call_id: str
    stack: str
    patient: PatientRecord
    events: list[TurnEvent] = field(default_factory=list)
    turn_latencies: list[TurnLatency] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: ErrorClass | None = None
    error_detail: str = ""
    success: bool = True


@dataclass
class StackRunResult:
    stack: str
    calls: list[CallRecord] = field(default_factory=list)

    @property
    def total_calls(self) -> int:
        return len(self.calls)

    @property
    def successful_calls(self) -> int:
        return sum(1 for c in self.calls if c.success)

    @property
    def error_rate(self) -> float:
        if not self.calls:
            return 0.0
        return 1.0 - (self.successful_calls / self.total_calls)


@dataclass
class StackReference:
    p95_turn_latency_ms: float
    cost_per_minute: float
    error_rate: float


@dataclass
class StackConfig:
    stack: str
    enabled: bool
    description: str
    raw: dict[str, Any]
    reference: StackReference | None = None
    concurrency: int = 10

    @property
    def pricing(self) -> dict[str, float]:
        pricing = self.raw.get("pricing", {})
        return {k: float(v) for k, v in pricing.items()}

    def cost_per_minute(self) -> float:
        if self.reference:
            return self.reference.cost_per_minute
        return sum(self.pricing.values())
