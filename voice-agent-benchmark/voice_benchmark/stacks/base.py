from __future__ import annotations

from abc import ABC, abstractmethod

from voice_benchmark.models import CallRecord, PatientRecord, StackConfig


class StackAdapter(ABC):
    name: str

    def __init__(self, config: StackConfig):
        self.config = config

    @abstractmethod
    async def place_call(self, patient: PatientRecord, call_index: int) -> CallRecord:
        """Start one outbound call and return a populated CallRecord."""

    def missing_credentials(self) -> list[str]:
        """Return env var names still set to ${...} placeholders."""
        missing: list[str] = []
        for key, value in self.config.raw.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                missing.append(value[2:-1])
        return missing
