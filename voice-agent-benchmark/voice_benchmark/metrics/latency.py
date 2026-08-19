from __future__ import annotations

from voice_benchmark.models import CallRecord, EventType, TurnEvent, TurnLatency


def compute_turn_latencies(events: list[TurnEvent]) -> list[TurnLatency]:
    """Time from end-of-user-speech to first assistant audio byte per turn."""
    by_turn: dict[str, list[TurnEvent]] = {}
    for event in events:
        by_turn.setdefault(event.turn_id, []).append(event)

    latencies: list[TurnLatency] = []
    for turn_id, turn_events in by_turn.items():
        turn_events.sort(key=lambda e: e.timestamp_ms)
        speech_end = next(
            (e for e in turn_events if e.event_type == EventType.USER_SPEECH_END),
            None,
        )
        audio_start = next(
            (e for e in turn_events if e.event_type == EventType.ASSISTANT_AUDIO_START),
            None,
        )
        if speech_end and audio_start and audio_start.timestamp_ms >= speech_end.timestamp_ms:
            latencies.append(
                TurnLatency(
                    turn_id=turn_id,
                    call_id=speech_end.call_id,
                    latency_ms=audio_start.timestamp_ms - speech_end.timestamp_ms,
                )
            )
    return latencies


def enrich_call_record(record: CallRecord) -> CallRecord:
    record.turn_latencies = compute_turn_latencies(record.events)
    return record


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def aggregate_latencies(calls: list[CallRecord]) -> dict[str, float]:
    all_ms = [tl.latency_ms for call in calls for tl in call.turn_latencies]
    return {
        "p50_turn_latency_ms": percentile(all_ms, 50),
        "p95_turn_latency_ms": percentile(all_ms, 95),
        "p99_turn_latency_ms": percentile(all_ms, 99),
        "turn_count": float(len(all_ms)),
    }
