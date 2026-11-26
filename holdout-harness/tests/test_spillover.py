from holdout_harness.spillover import cross_bucket_customers, mixed_markets
from holdout_harness.bucketing import assign, assign_routes_by_market
from holdout_harness.synth import make_routes


def test_mixed_markets_detects_shared_demand():
    r2m = {"a": "M1", "b": "M1", "c": "M2"}
    arm = {"a": "treatment", "b": "control", "c": "control"}
    assert mixed_markets(arm, r2m) == ["M1"]


def test_market_hashing_has_no_mixed_markets_route_hashing_does():
    r2m, _ = make_routes(1)
    assert mixed_markets(assign_routes_by_market(r2m, "s"), r2m) == []
    assert len(mixed_markets({r: assign(r, "s") for r in r2m}, r2m)) > 0


def test_cross_bucket_customers():
    b = [{"customer_id": "c1", "arm": "treatment"}, {"customer_id": "c1", "arm": "control"},
         {"customer_id": "c2", "arm": "control"}, {"customer_id": "c2", "arm": "control"}]
    assert cross_bucket_customers(b) == {"c1"}
