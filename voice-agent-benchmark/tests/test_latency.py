import pytest

from voice_benchmark.metrics.latency import aggregate_latencies, compute_turn_latencies, percentile
from voice_benchmark.models import CallRecord, EventType, PatientRecord, TurnEvent


def test_compute_turn_latency():
    events = [
        TurnEvent(EventType.USER_SPEECH_END, 1000, "t0", "c1"),
        TurnEvent(EventType.ASSISTANT_AUDIO_START, 1380, "t0", "c1"),
        TurnEvent(EventType.USER_SPEECH_END, 5000, "t1", "c1"),
        TurnEvent(EventType.ASSISTANT_AUDIO_START, 5600, "t1", "c1"),
    ]
    latencies = compute_turn_latencies(events)
    assert len(latencies) == 2
    assert latencies[0].latency_ms == 380
    assert latencies[1].latency_ms == 600


def test_percentile():
    assert percentile([100, 200, 300, 400, 500], 95) == pytest.approx(480.0)


def test_aggregate_latencies():
    patient = PatientRecord("A", "+1", "cooperative", "2026-01-01 09:00")
    call = CallRecord(
        call_id="c1",
        stack="mock",
        patient=patient,
        events=[
            TurnEvent(EventType.USER_SPEECH_END, 0, "t0", "c1"),
            TurnEvent(EventType.ASSISTANT_AUDIO_START, 400, "t0", "c1"),
        ],
    )
    from voice_benchmark.metrics.latency import enrich_call_record

    enrich_call_record(call)
    agg = aggregate_latencies([call])
    assert agg["p95_turn_latency_ms"] == 400
