from voice_benchmark.metrics.events import parse_turn_events
from voice_benchmark.models import EventType


def test_parse_vapi_webhook():
    events = parse_turn_events(
        {"type": "speech-end", "timestamp": 1000, "turnId": "t0"},
        call_id="c1",
        stack="vapi",
    )
    assert len(events) == 1
    assert events[0].event_type == EventType.USER_SPEECH_END


def test_parse_generic_event():
    events = parse_turn_events(
        {"event_type": "assistant_audio_start", "timestamp_ms": 500, "turn_id": "t1"},
        call_id="c2",
        stack="mock",
    )
    assert events[0].event_type == EventType.ASSISTANT_AUDIO_START
