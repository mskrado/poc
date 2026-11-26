"""Deterministic, salted, stable bucketing.

Uses SHA-256, never Python's built-in hash(), so the same unit lands in the same
arm on every machine and every run. Change the salt to re-randomise.
"""
import hashlib

TREAT = "treatment"
CONTROL = "control"


def bucket_value(unit_id: str, salt: str) -> float:
    """Map (salt, unit_id) to a stable float in [0, 1)."""
    digest = hashlib.sha256(f"{salt}:{unit_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def assign(unit_id: str, salt: str, treat_share: float = 0.5) -> str:
    """Return 'treatment' or 'control' for one unit."""
    if not 0.0 < treat_share < 1.0:
        raise ValueError("treat_share must be between 0 and 1")
    return TREAT if bucket_value(unit_id, salt) < treat_share else CONTROL


def assign_routes_by_market(route_to_market: dict, salt: str, treat_share: float = 0.5) -> dict:
    """Split-route design: hash the *market*, not the route.

    Routes that compete for the same demand (LHR-JFK and LGW-JFK both sit in
    LON-NYC) always share an arm, so the treated engine can't steal bookings
    from a control route next door and call it lift.
    """
    return {r: assign(m, salt, treat_share) for r, m in route_to_market.items()}
