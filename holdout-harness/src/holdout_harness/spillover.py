"""Spillover guards: find places where treated and control share demand."""
from collections import defaultdict


def mixed_markets(route_arm: dict, route_to_market: dict) -> list:
    """Markets that contain routes in both arms. Should be empty for a clean split."""
    arms = defaultdict(set)
    for route, arm in route_arm.items():
        arms[route_to_market[route]].add(arm)
    return sorted(m for m, a in arms.items() if len(a) > 1)


def cross_bucket_customers(bookings) -> set:
    """Customers whose bookings landed in more than one arm.

    `bookings` is an iterable of dicts with 'customer_id' and 'arm'. In a
    booking-cohort test the arm is usually set per session, so one traveller
    who searches twice can see both prices. Flag them; don't silently count them.
    """
    seen = defaultdict(set)
    for b in bookings:
        seen[b["customer_id"]].add(b["arm"])
    return {c for c, a in seen.items() if len(a) > 1}
