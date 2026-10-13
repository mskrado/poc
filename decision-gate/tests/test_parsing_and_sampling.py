from pathlib import Path

import pandas as pd
import pytest

from gate.checks import error_scanner, parse_agent_action, parse_category, parse_intent, parse_route
from gate.data import CATEGORIES, allocation, sample_tickets

ROOT = Path(__file__).resolve().parents[1]


def test_parse_category():
    cats = list(CATEGORIES)
    assert parse_category("**Category:** ORDER\nIntent: track_order", cats) == "ORDER"
    assert parse_category("This is a refund question (REFUND).", cats) == "REFUND"
    assert parse_category("no idea", cats) == ""


def test_parse_intent_and_route():
    assert parse_intent("Intent: track order", ["track_order", "cancel_order"]) == "track_order"
    assert parse_route("Handler: **small_model** because routine") == "small_model"
    assert parse_route("should go to a human agent") == "human"


def test_parse_agent_action():
    assert parse_agent_action("ESCALATE") == "ESCALATE"
    assert parse_agent_action("ANSWER: your tracking number is ...") == "ANSWER"
    assert parse_agent_action("hmm") == "RETRY"


def test_error_scanner():
    assert error_scanner("ERROR 503 upstream timeout")
    assert error_scanner("Traceback (most recent call last):")
    assert not error_scanner('{"status": 200, "tracking": "1Z999"}')


def test_four_error_entry_cases_and_poisoned_memory_seeds():
    """Another article reruns these four cases plus the regex scanner."""
    from gate.seeds import ORION_PATHS, POISONED_MEMORY
    assert [p["id"] for p in ORION_PATHS] == [
        "seed-orion-tool-output",
        "seed-orion-upstream-api",
        "seed-orion-memory",
        "seed-orion-user-text",
    ]
    for p in ORION_PATHS:
        assert error_scanner(p["context"] + "\n" + p["customer"]), p["id"]
    assert {m["id"] for m in POISONED_MEMORY} == {
        "seed-memory-admin-note", "seed-memory-injection", "seed-memory-wrong-fact",
    }


def test_allocation_sums_to_50_and_covers_all():
    counts = pd.Series({"A": 6000, "B": 4000, "C": 1000, "D": 950})
    a = allocation(counts, 10)
    assert sum(a.values()) == 10 and min(a.values()) >= 2


@pytest.mark.skipif(not (ROOT / "data" / "bitext.csv").exists(), reason="dataset not downloaded")
def test_sample_is_deterministic_and_stratified():
    a = sample_tickets(ROOT / "data" / "bitext.csv")
    b = sample_tickets(ROOT / "data" / "bitext.csv")
    assert len(a) == 50 and a.ticket_id.tolist() == b.ticket_id.tolist()
    assert set(a.category) == set(CATEGORIES)
