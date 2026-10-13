"""Recompute router actions from shipped results. No model calls."""
from __future__ import annotations

from .policy import decide_route
from .types import Action

DEFAULT_THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9)


def router_rows(rows: list[dict]) -> list[dict]:
    """The 50 Bitext router decisions. Score is P(chosen label), 4 d.p. in the CSV."""
    out = [r for r in rows if r.get("source") == "bitext" and r.get("gate") == "router_gate"]
    return out


def sweep_router(rows: list[dict], thresholds=DEFAULT_THRESHOLDS) -> list[dict]:
    """How many tickets route to a human if the threshold changes.

    Same rule as decide_route: score below the threshold is a low-confidence
    fallback to a human; a score that clears the threshold keeps the model's
    label (small_model, frontier, or human).
    """
    routers = router_rows(rows)
    table = []
    for threshold in thresholds:
        t = float(threshold)
        confident_human = 0
        fallback = 0
        route_small = 0
        route_frontier = 0
        for r in routers:
            score = float(r["score"])
            label = r["predicted_label"]
            action = decide_route(label, score, t, True)
            if action is Action.ROUTE_SMALL:
                route_small += 1
            elif action is Action.ROUTE_FRONTIER:
                route_frontier += 1
            elif score < t:
                fallback += 1
            elif label == "human":
                confident_human += 1
            else:
                raise ValueError(f"unexpected human route for {r.get('ticket_id')}: {label} {score} @ {t}")
        route_human = confident_human + fallback
        if route_human + route_small + route_frontier != len(routers):
            raise ValueError("router sweep does not cover every ticket")
        table.append({
            "threshold": t,
            "tickets": len(routers),
            "route_human": route_human,
            "confident_human": confident_human,
            "low_confidence_fallback": fallback,
            "route_small": route_small,
            "route_frontier": route_frontier,
        })
    return table
