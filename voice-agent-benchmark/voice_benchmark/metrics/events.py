from __future__ import annotations

from voice_benchmark.models import EventType, TurnEvent


def parse_turn_events(payload: dict, *, call_id: str, stack: str) -> list[TurnEvent]:
    """Normalize platform-specific webhook payloads into unified turn events."""
    events: list[TurnEvent] = []

    if stack == "vapi":
        event_type = payload.get("type") or payload.get("message", {}).get("type")
        ts = float(payload.get("timestamp") or payload.get("createdAt") or 0)
        turn_id = str(payload.get("turnId") or payload.get("id") or "turn-0")
        mapping = {
            "speech-update": EventType.USER_SPEECH_END,
            "speech-end": EventType.USER_SPEECH_END,
            "assistant-speech-start": EventType.ASSISTANT_AUDIO_START,
            "call-ended": EventType.CALL_END,
            "error": EventType.ERROR,
        }
        normalized = mapping.get(str(event_type), None)
        if normalized:
            events.append(
                TurnEvent(
                    event_type=normalized,
                    timestamp_ms=ts,
                    turn_id=turn_id,
                    call_id=call_id,
                    metadata={"raw_type": event_type},
                )
            )
        return events

    if stack == "retell":
        event_type = payload.get("event")
        ts = float(payload.get("timestamp_ms", 0))
        turn_id = str(payload.get("turn_id", "turn-0"))
        mapping = {
            "user_speech_end": EventType.USER_SPEECH_END,
            "agent_speech_start": EventType.ASSISTANT_AUDIO_START,
            "call_ended": EventType.CALL_END,
            "error": EventType.ERROR,
        }
        normalized = mapping.get(str(event_type))
        if normalized:
            events.append(
                TurnEvent(
                    event_type=normalized,
                    timestamp_ms=ts,
                    turn_id=turn_id,
                    call_id=call_id,
                )
            )
        return events

    # Generic / mock / pipecat / openai_realtime
    event_type = payload.get("event_type") or payload.get("type")
    if not event_type:
        return events
    try:
        normalized = EventType(str(event_type))
    except ValueError:
        return events
    events.append(
        TurnEvent(
            event_type=normalized,
            timestamp_ms=float(payload.get("timestamp_ms", 0)),
            turn_id=str(payload.get("turn_id", "turn-0")),
            call_id=call_id,
            metadata=dict(payload.get("metadata") or {}),
        )
    )
    return events
