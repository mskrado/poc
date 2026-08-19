from __future__ import annotations

from voice_benchmark.models import CallRecord, PatientRecord, StackConfig
from voice_benchmark.stacks.base import StackAdapter
from voice_benchmark.stacks.mock import MockStackAdapter, ReferenceStackAdapter


class VapiStackAdapter(StackAdapter):
    name = "vapi"

    async def place_call(self, patient: PatientRecord, call_index: int) -> CallRecord:
        missing = self.missing_credentials()
        if missing:
            raise RuntimeError(
                f"Vapi adapter requires env vars: {', '.join(missing)}. "
                "Use --mode mock for dry-run, or set credentials."
            )
        # Live integration point: POST {api_base}/call/phone with assistant + customer.number
        raise NotImplementedError(
            "Live Vapi calling is not wired in this POC. "
            "Use `voice-benchmark run --stack mock --mode mock` or implement place_call with httpx."
        )


class RetellStackAdapter(StackAdapter):
    name = "retell"

    async def place_call(self, patient: PatientRecord, call_index: int) -> CallRecord:
        missing = self.missing_credentials()
        if missing:
            raise RuntimeError(
                f"Retell adapter requires env vars: {', '.join(missing)}. "
                "Use --mode mock for dry-run."
            )
        raise NotImplementedError("Live Retell calling not wired — use mock mode.")


class PipecatStackAdapter(StackAdapter):
    name = "pipecat"

    async def place_call(self, patient: PatientRecord, call_index: int) -> CallRecord:
        raise NotImplementedError(
            "Pipecat self-hosted runner not bundled — use mock mode or add your pipeline entrypoint."
        )


class OpenAIRealtimeStackAdapter(StackAdapter):
    name = "openai_realtime"

    async def place_call(self, patient: PatientRecord, call_index: int) -> CallRecord:
        missing = self.missing_credentials()
        if missing:
            raise RuntimeError(
                f"OpenAI Realtime adapter requires env vars: {', '.join(missing)}. "
                "Use --mode mock for dry-run."
            )
        raise NotImplementedError("Live Twilio+Realtime stack not wired — use mock mode.")


def get_adapter(
    config: StackConfig,
    *,
    mode: str = "mock",
    scenario: dict | None = None,
) -> StackAdapter:
    if mode == "mock":
        if config.stack == "mock":
            return MockStackAdapter(config, scenario=scenario)
        return ReferenceStackAdapter(config, scenario=scenario)

    adapters = {
        "vapi": VapiStackAdapter,
        "retell": RetellStackAdapter,
        "pipecat": PipecatStackAdapter,
        "openai_realtime": OpenAIRealtimeStackAdapter,
    }
    cls = adapters.get(config.stack)
    if cls is None:
        raise ValueError(f"Unknown stack: {config.stack}")
    return cls(config)
