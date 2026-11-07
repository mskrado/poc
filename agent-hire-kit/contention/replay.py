"""Replay a task or the shared ledger from the audit log alone.

The arithmetic here is intentionally written out again, instead of calling the
worker, so a wrong logged output fails the check. Replaying this simulation
log is not a production audit certification.
"""

from __future__ import annotations

import copy
from typing import List, Optional

from .tasks import SHARED_PATH


class ReplayError(Exception):
    pass


def _require(events: List[dict], task_id: str, name: str) -> dict:
    found = [event for event in events if event.get("task_id") == task_id and event.get("event") == name]
    if len(found) != 1:
        raise ReplayError(f"{task_id} has {len(found)} {name} events in the log")
    return found[0]


def replay_task(events: List[dict], task_id: str) -> dict:
    """Recompute one task's record from the logged transform input. No workspace."""
    transform = _require(events, task_id, "transform")
    if transform.get("tool") != "extend_line":
        raise ReplayError(f"{task_id} transform tool is {transform.get('tool')!r}")
    if transform.get("memory_read") != []:
        raise ReplayError(f"{task_id} transform recorded an unexpected memory read")
    body = transform.get("input")
    if not isinstance(body, dict):
        raise ReplayError(f"{task_id} transform input is missing")
    try:
        recomputed = {
            "sku": body["sku"],
            "qty": body["qty"],
            "unit_cents": body["unit_cents"],
            "extended_cents": body["qty"] * body["unit_cents"],
        }
    except (KeyError, TypeError) as exc:
        raise ReplayError(f"{task_id} transform input cannot be recomputed: {exc}") from exc
    if transform.get("output") != recomputed:
        raise ReplayError(f"{task_id} logged output does not match qty * unit_cents from the logged input")
    write = _require(events, task_id, "write_record")
    if write.get("output") != recomputed:
        raise ReplayError(f"{task_id} write_record does not match the replayed transform")
    return recomputed


def replay_ledger(events: List[dict], workspace: str, shared_path: str = SHARED_PATH) -> Optional[dict]:
    """Fold seed and successful compare-and-swap events for one workspace.

    Each successful swap must be exactly the prior body plus one owner. The
    function returns the ledger implied by the log, or None when the log has
    no seed for that workspace.
    """
    seeds = []
    commits = []
    for event in events:
        if event.get("workspace") != workspace or event.get("path") != shared_path:
            continue
        if event.get("event") == "seed":
            seeds.append(event)
        elif event.get("event") == "cas_ok":
            commits.append(event)
    if not seeds and not commits:
        return None
    if len(seeds) != 1:
        raise ReplayError(f"{workspace} has {len(seeds)} ledger seeds")
    seeded = seeds[0].get("output") or {}
    body = copy.deepcopy(seeded.get("body"))
    # commit_seq is assigned under the workspace lock, so thread logs can be
    # folded even when the JSONL order is not the commit order.
    try:
        commits.sort(key=lambda event: event["commit_seq"])
    except (KeyError, TypeError) as exc:
        raise ReplayError("ledger compare-and-swap is missing commit_seq") from exc
    for event in commits:
        seen = (event.get("input") or {}).get("seen")
        worker_id = event.get("worker_id")
        if seen != body:
            raise ReplayError(
                f"logged read of {workspace} {shared_path} does not match the prior committed ledger"
            )
        if not isinstance(body.get("owners"), list) or worker_id in body["owners"]:
            raise ReplayError(f"ledger replay refused a duplicate or unreadable owner list for {worker_id}")
        expected = {
            "total": body["total"] + 1,
            "owners": list(body["owners"]) + [worker_id],
        }
        if event.get("output") != expected:
            raise ReplayError(f"logged ledger write for {worker_id} is not prior total + 1")
        if expected["total"] != len(expected["owners"]):
            raise ReplayError("replayed ledger total does not match its owners")
        body = expected
    return body
