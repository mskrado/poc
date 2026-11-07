"""Local fixture tasks. Invented SKUs only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


SHARED_PATH = "shared/counter.json"
INITIAL_COUNTER = {"total": 0, "owners": []}


@dataclass(frozen=True)
class Task:
    task_id: str
    worker_id: str
    record: str
    initial: dict
    op: str
    expected: dict


def extend_line(body: dict) -> dict:
    """Pure fixture op: extended_cents = qty * unit_cents. Does not mutate body."""
    if body.get("sku") is None or "qty" not in body or "unit_cents" not in body:
        raise ValueError("record is missing sku, qty, or unit_cents")
    qty = body["qty"]
    unit = body["unit_cents"]
    if isinstance(qty, bool) or not isinstance(qty, int):
        raise ValueError("qty must be an int")
    if isinstance(unit, bool) or not isinstance(unit, int):
        raise ValueError("unit_cents must be an int")
    return {
        "sku": body["sku"],
        "qty": qty,
        "unit_cents": unit,
        "extended_cents": qty * unit,
    }


def make_tasks(n: int = 10) -> List[Task]:
    """Build n scripted tasks. Planned kit size is 10. n is for tests of the schedule rule."""
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 99:
        raise ValueError("worker count must be an integer from 1 to 99")
    tasks = []
    for i in range(1, n + 1):
        worker_id = f"w{i:02d}"
        initial = {
            "sku": f"SYN-{i:02d}",
            "qty": i,
            "unit_cents": 100 + (i - 1) * 25,
            "extended_cents": None,
        }
        tasks.append(Task(
            task_id=f"t{i:02d}",
            worker_id=worker_id,
            record=f"records/{worker_id}.json",
            initial=initial,
            op="extend_line",
            expected=extend_line(initial),
        ))
    return tasks


def default_fixture_path() -> Path:
    return Path(__file__).resolve().parent.parent / "fixtures" / "tasks.json"


def load_fixture(path: Optional[str] = None) -> List[Task]:
    """Load the checked-in fixture. It must be the planned 10-worker synthetic set."""
    fixture = Path(path) if path else default_fixture_path()
    try:
        raw = json.loads(fixture.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read fixture {fixture}: {exc}") from exc
    if raw.get("label") != "SYNTHETIC CONTENTION SIMULATION":
        raise ValueError("fixture is missing the synthetic label")
    if raw.get("shared_path") != SHARED_PATH:
        raise ValueError("fixture shared_path is not the harness counter")
    rows = raw.get("tasks")
    if not isinstance(rows, list) or len(rows) != 10:
        raise ValueError("fixture must contain the planned 10 tasks")
    expected_tasks = make_tasks(10)
    loaded: List[Task] = []
    for row, canon in zip(rows, expected_tasks):
        try:
            task = Task(
                task_id=row["task_id"],
                worker_id=row["worker_id"],
                record=row["record"],
                initial=row["initial"],
                op=row["op"],
                expected=row["expected"],
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"fixture task is incomplete: {exc}") from exc
        if task.op != "extend_line":
            raise ValueError(f"{task.task_id} has an unsupported op")
        if extend_line(task.initial) != task.expected:
            raise ValueError(f"{task.task_id} expected value does not match qty * unit_cents")
        if task != canon:
            raise ValueError(f"{task.task_id} does not match the planned synthetic fixture")
        loaded.append(task)
    return loaded
