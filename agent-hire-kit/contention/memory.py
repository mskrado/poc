"""Scoped-memory probe for the synthetic workspace.

Check 3 on Dr. Orion Kade's checklist asks whether agent B can read a marker
written by agent A. This probe answers that question for these fixtures only.
"""

from __future__ import annotations

from .banner import ISOLATION_LIMIT
from .workspace import ProtectedError, memory_marker_path


def marker_body(worker_id: str, task_id: str) -> dict:
    return {
        "marker": f"synthetic-{worker_id}",
        "source": "fixture",
        "author": worker_id,
        "task_id": task_id,
    }


def _workspace_name(layout: str, worker_id: str) -> str:
    return "shared" if layout == "shared" else worker_id


def probe_scoped_memory(log, tasks, workspaces: dict, layout: str) -> dict:
    own_ok = 0
    denied = 0
    succeeded = 0
    absent = 0
    for task in tasks:
        name = _workspace_name(layout, task.worker_id)
        ws = workspaces[name]
        path = memory_marker_path(task.worker_id)
        body = marker_body(task.worker_id, task.task_id)
        ws.write_new(task.worker_id, path, body, phase="probe")
        log.add(
            event="write_memory",
            tool="write_memory",
            workspace=name,
            worker_id=task.worker_id,
            task_id=task.task_id,
            path=path,
            logical_tick=None,
            input={"path": path, "body": body},
            output={"written": True},
            memory_read=[],
            attempt=None,
        )
    for task in tasks:
        name = _workspace_name(layout, task.worker_id)
        ws = workspaces[name]
        path = memory_marker_path(task.worker_id)
        _version, body = ws.read(task.worker_id, path, phase="probe")
        own_ok += 1
        log.add(
            event="read_memory",
            tool="read_memory",
            workspace=name,
            worker_id=task.worker_id,
            task_id=task.task_id,
            path=path,
            logical_tick=None,
            input={"path": path},
            output=body,
            memory_read=[path],
            attempt=None,
        )
    if len(tasks) >= 2:
        for index, task in enumerate(tasks):
            other = tasks[(index + 1) % len(tasks)]
            name = _workspace_name(layout, task.worker_id)
            ws = workspaces[name]
            path = memory_marker_path(other.worker_id)
            try:
                ws.read(task.worker_id, path, phase="probe")
            except ProtectedError as exc:
                if exc.reason != "scoped_memory":
                    raise
                denied += 1
                log.add(
                    event="read_memory_denied",
                    tool="read_memory",
                    workspace=name,
                    worker_id=task.worker_id,
                    task_id=task.task_id,
                    path=path,
                    logical_tick=None,
                    input={"path": path},
                    output={"allowed": False, "reason": "scoped_memory"},
                    memory_read=[],
                    attempt=None,
                )
            else:
                succeeded += 1
                log.add(
                    event="read_memory_leaked",
                    tool="read_memory",
                    workspace=name,
                    worker_id=task.worker_id,
                    task_id=task.task_id,
                    path=path,
                    logical_tick=None,
                    input={"path": path},
                    output={"allowed": True},
                    memory_read=[path],
                    attempt=None,
                )
    if layout == "isolated":
        for task in tasks:
            ws = workspaces[task.worker_id]
            for other in tasks:
                if other.worker_id == task.worker_id:
                    continue
                if memory_marker_path(other.worker_id) not in ws.files:
                    absent += 1
    return {
        "own_reads_ok": own_ok,
        "cross_reads_denied": denied,
        "cross_reads_succeeded": succeeded,
        "markers_absent_from_other_workspaces": absent if layout == "isolated" else None,
        "limit": ISOLATION_LIMIT,
    }
