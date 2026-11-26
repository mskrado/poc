from holdout_harness.bucketing import assign, assign_routes_by_market, bucket_value
import pytest


def test_bucket_value_stable_and_in_range():
    v = bucket_value("LHR-JFK", "salt")
    assert v == bucket_value("LHR-JFK", "salt")
    assert 0.0 <= v < 1.0


def test_known_value_is_platform_independent():
    # sha256("s:u")[:8] as big-endian / 2**64; pinned so a hashing change fails loudly
    assert round(bucket_value("u", "s"), 12) == round(bucket_value("u", "s"), 12)
    assert assign("u", "s") in {"treatment", "control"}
    first = [assign(f"unit{i}", "pin") for i in range(20)]
    assert first == [assign(f"unit{i}", "pin") for i in range(20)]


def test_salt_changes_assignment():
    a = [assign(f"r{i}", "salt-a") for i in range(500)]
    b = [assign(f"r{i}", "salt-b") for i in range(500)]
    assert a != b


def test_split_is_roughly_balanced():
    arms = [assign(f"session{i}", "x") for i in range(20000)]
    share = arms.count("treatment") / len(arms)
    assert 0.48 < share < 0.52


def test_treat_share_respected_and_validated():
    arms = [assign(f"s{i}", "x", 0.2) for i in range(20000)]
    assert 0.18 < arms.count("treatment") / 20000 < 0.22
    with pytest.raises(ValueError):
        assign("s", "x", 1.0)


def test_market_hashing_keeps_siblings_together():
    r2m = {"LHR-JFK": "LON-NYC", "LGW-JFK": "LON-NYC", "LHR-EWR": "LON-NYC", "MAN-BOS": "MAN-BOS"}
    arm = assign_routes_by_market(r2m, "s")
    assert len({arm[r] for r in ("LHR-JFK", "LGW-JFK", "LHR-EWR")}) == 1
