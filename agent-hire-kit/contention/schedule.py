"""Serial, barrier-concurrent, isolated, and OS-thread schedules.

The first three use a scripted clock. Logical overlap is that clock: disjoint
record writes are applied one after another because their paths do not meet.
The shared counter is the file that contends, and its waves are explicit.
OS threads are a separate mode. Their conflict count follows the interpreter
and is not a stable benchmark.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .banner import MODEL_VERSION
from .memory import probe_scoped_memory
from .tasks import SHARED_PATH, Task, extend_line
from .workspace import (
    ConflictError,
    Workspace,
    build_isolated,
    build_shared,
)


def integrate(counter: dict, worker_id: str) -> dict:
    owners = list(counter["owners"])
    if worker_id in owners:
        raise RuntimeError(f"duplicate ledger owner {worker_id}")
    return {"total": counter["total"] + 1, "owners": owners + [worker_id]}


def prepare(tasks: List[Task]) -> List[Task]:
    if not tasks:
        raise ValueError("no tasks")
    ordered = sorted(tasks, key=lambda task: task.worker_id)
    ids = [task.worker_id for task in ordered]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate worker id")
    for task in ordered:
        if "/" in task.worker_id or task.worker_id in ("", ".", ".."):
            raise ValueError(f"worker id is not a single path segment: {task.worker_id}")
    return ordered


def resolve_retries(n: int, max_retries: Optional[int]) -> int:
    if max_retries is None:
        return n - 1
    if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError("max_retries must be a nonnegative integer")
    return max_retries


@dataclass
class TaskOutcome:
    worker_id: str
    task_id: str
    record_ok: bool
    integrated: bool
    attempts: int
    conflicts: int
    retries: int
    finished_logical_tick: Optional[int]

    @property
    def useful(self) -> bool:
        return self.record_ok and self.integrated


@dataclass
class ModeResult:
    mode: str
    scheduler: str
    workspace_layout: str
    max_retries: int
    outcomes: List[TaskOutcome]
    events: List[dict]
    logical_ticks: Optional[int]
    schedule_wall_seconds: float
    workspaces: Dict[str, Workspace]
    tasks: List[Task]
    probe: dict = field(default_factory=dict)
    schedule_rejections: int = 0

    @property
    def useful(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.useful)

    @property
    def records_correct(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.record_ok)

    @property
    def integrated_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.integrated)

    @property
    def conflicts(self) -> int:
        return sum(outcome.conflicts for outcome in self.outcomes)

    @property
    def retries(self) -> int:
        return sum(outcome.retries for outcome in self.outcomes)


class Log:
    def __init__(self, mode: str, scheduler: str):
        self.mode = mode
        self.scheduler = scheduler
        self.events: List[dict] = []
        self.t0 = time.perf_counter()
        self._lock = threading.Lock()

    def wall(self) -> float:
        return time.perf_counter() - self.t0

    def add(self, **kwargs) -> dict:
        event = {
            "mode": self.mode,
            "scheduler": self.scheduler,
            "workspace": kwargs["workspace"],
            "worker_id": kwargs.get("worker_id"),
            "task_id": kwargs.get("task_id"),
            "event": kwargs["event"],
            "tool": kwargs["tool"],
            "input": _copy(kwargs.get("input")),
            "output": _copy(kwargs.get("output")),
            "model_version": MODEL_VERSION,
            "memory_read": list(kwargs.get("memory_read") or []),
            "path": kwargs.get("path"),
            "logical_tick": kwargs.get("logical_tick"),
            "wall_s": self.wall(),
            "attempt": kwargs.get("attempt"),
            "commit_seq": kwargs.get("commit_seq"),
        }
        with self._lock:
            self.events.append(event)
        return event


def _copy(value):
    if isinstance(value, dict):
        return {key: _copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy(item) for item in value]
    return value


def _seed(log: Log, ws: Workspace, workspace: str, tasks: List[Task]) -> None:
    snap = ws.snapshot()
    log.add(
        event="seed",
        tool="seed",
        workspace=workspace,
        worker_id=None,
        task_id=None,
        path=SHARED_PATH,
        logical_tick=None,
        input={"path": SHARED_PATH},
        output={"version": 0, "body": snap[SHARED_PATH]["body"]},
        memory_read=[],
        attempt=None,
    )
    for task in tasks:
        log.add(
            event="seed",
            tool="seed",
            workspace=workspace,
            worker_id=task.worker_id,
            task_id=task.task_id,
            path=task.record,
            logical_tick=None,
            input={"path": task.record},
            output={"version": 0, "body": snap[task.record]["body"]},
            memory_read=[],
            attempt=None,
        )


def _private_prefix(log: Log, ws: Workspace, workspace: str, task: Task, tick: int) -> bool:
    """Read, extend, and write one record. Returns whether the write matches the formula."""
    version, body = ws.read(task.worker_id, task.record)
    log.add(
        event="read_record",
        tool="read_record",
        workspace=workspace,
        worker_id=task.worker_id,
        task_id=task.task_id,
        path=task.record,
        logical_tick=tick,
        input={"path": task.record, "version": version},
        output=body,
        memory_read=[],
        attempt=None,
    )
    extended = extend_line(body)
    log.add(
        event="transform",
        tool="extend_line",
        workspace=workspace,
        worker_id=task.worker_id,
        task_id=task.task_id,
        path=task.record,
        logical_tick=tick + 1,
        input=body,
        output=extended,
        memory_read=[],
        attempt=None,
    )
    ws.cas(task.worker_id, task.record, version, extended)
    written_version, written = ws.read(task.worker_id, task.record)
    log.add(
        event="write_record",
        tool="write_record",
        workspace=workspace,
        worker_id=task.worker_id,
        task_id=task.task_id,
        path=task.record,
        logical_tick=tick + 2,
        input={"expected_version": version, "body": extended},
        output=written,
        memory_read=[],
        attempt=None,
    )
    del written_version
    return written == extend_line(task.initial)


def _cas_once(log, ws, workspace, task, seen_version, seen_body, attempt, tick, conflicts_so_far, max_retries):
    """Try one ledger compare-and-swap. Returns (integrated, conflicts, retries_delta, exhausted)."""
    new_body = integrate(seen_body, task.worker_id)
    try:
        _version, commit_seq = ws.cas(task.worker_id, SHARED_PATH, seen_version, new_body)
    except ConflictError as exc:
        log.add(
            event="cas_conflict",
            tool="compare_and_swap",
            workspace=workspace,
            worker_id=task.worker_id,
            task_id=task.task_id,
            path=SHARED_PATH,
            logical_tick=tick,
            input={"expected_version": seen_version, "seen": seen_body, "worker_id": task.worker_id},
            output={"conflict": True, "expected_version": exc.expected, "actual_version": exc.actual},
            memory_read=[],
            attempt=attempt,
        )
        conflicts = conflicts_so_far + 1
        if conflicts > max_retries:
            log.add(
                event="task_exhausted",
                tool="stop",
                workspace=workspace,
                worker_id=task.worker_id,
                task_id=task.task_id,
                path=SHARED_PATH,
                logical_tick=tick,
                input={"conflicts": conflicts, "max_retries": max_retries},
                output={"integrated": False},
                memory_read=[],
                attempt=attempt,
            )
            return False, conflicts, 0, True
        log.add(
            event="retry",
            tool="retry",
            workspace=workspace,
            worker_id=task.worker_id,
            task_id=task.task_id,
            path=SHARED_PATH,
            logical_tick=tick,
            input={"conflicts": conflicts},
            output={"will_retry": True},
            memory_read=[],
            attempt=attempt,
        )
        return False, conflicts, 1, False
    log.add(
        event="cas_ok",
        tool="compare_and_swap",
        workspace=workspace,
        worker_id=task.worker_id,
        task_id=task.task_id,
        path=SHARED_PATH,
        logical_tick=tick,
        input={"expected_version": seen_version, "seen": seen_body, "worker_id": task.worker_id},
        output=new_body,
        memory_read=[],
        attempt=attempt,
        commit_seq=commit_seq,
    )
    log.add(
        event="task_done",
        tool="stop",
        workspace=workspace,
        worker_id=task.worker_id,
        task_id=task.task_id,
        path=SHARED_PATH,
        logical_tick=tick,
        input={"attempt": attempt},
        output={"integrated": True},
        memory_read=[],
        attempt=attempt,
    )
    return True, conflicts_so_far, 0, False


def _read_shared(log, ws, workspace, task, tick):
    version, body = ws.read(task.worker_id, SHARED_PATH)
    log.add(
        event="read_shared",
        tool="read_shared",
        workspace=workspace,
        worker_id=task.worker_id,
        task_id=task.task_id,
        path=SHARED_PATH,
        logical_tick=tick,
        input={"path": SHARED_PATH},
        output={"version": version, "body": body},
        memory_read=[],
        attempt=None,
    )
    return version, body


def _finish(mode, scheduler, layout, max_retries, outcomes, log, tick, workspaces, tasks) -> ModeResult:
    wall = log.wall()
    result = ModeResult(
        mode=mode,
        scheduler=scheduler,
        workspace_layout=layout,
        max_retries=max_retries,
        outcomes=outcomes,
        events=log.events,
        logical_ticks=tick,
        schedule_wall_seconds=wall,
        workspaces=workspaces,
        tasks=tasks,
        schedule_rejections=sum(ws.rejection_count("schedule") for ws in workspaces.values()),
    )
    result.probe = probe_scoped_memory(log, tasks, workspaces, layout)
    return result


def run_serial(tasks: List[Task], max_retries: Optional[int] = None) -> ModeResult:
    tasks = prepare(tasks)
    retries = resolve_retries(len(tasks), max_retries)
    ws = build_shared(tasks)
    log = Log("serial_shared", "deterministic")
    _seed(log, ws, "shared", tasks)
    outcomes = []
    tick = 0
    for task in tasks:
        record_ok = _private_prefix(log, ws, "shared", task, tick + 1)
        tick += 3
        conflicts = 0
        retry_count = 0
        attempts = 0
        integrated = False
        while True:
            tick += 1
            seen_version, seen_body = _read_shared(log, ws, "shared", task, tick)
            tick += 1
            attempts += 1
            integrated, conflicts, retry_delta, exhausted = _cas_once(
                log, ws, "shared", task, seen_version, seen_body, attempts, tick, conflicts, retries
            )
            retry_count += retry_delta
            if integrated or exhausted:
                break
        outcomes.append(TaskOutcome(
            task.worker_id, task.task_id, record_ok, integrated, attempts, conflicts, retry_count, tick
        ))
    return _finish("serial_shared", "deterministic", "shared", retries, outcomes, log, tick, {"shared": ws}, tasks)


def run_concurrent_shared(tasks: List[Task], max_retries: Optional[int] = None) -> ModeResult:
    tasks = prepare(tasks)
    retries = resolve_retries(len(tasks), max_retries)
    ws = build_shared(tasks)
    log = Log("concurrent_shared", "deterministic")
    _seed(log, ws, "shared", tasks)
    state = []
    for step in range(4):
        tick = step + 1
        for task in tasks:
            if step == 0:
                version, body = ws.read(task.worker_id, task.record)
                state.append({
                    "task": task,
                    "rec_version": version,
                    "rec_body": body,
                    "conflicts": 0,
                    "retries": 0,
                    "attempts": 0,
                    "integrated": False,
                    "exhausted": False,
                    "record_ok": False,
                    "finished": None,
                    "sv": None,
                    "seen": None,
                })
                log.add(
                    event="read_record", tool="read_record", workspace="shared",
                    worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                    logical_tick=tick, input={"path": task.record, "version": version},
                    output=body, memory_read=[], attempt=None,
                )
            elif step == 1:
                row = state[tasks.index(task)]
                extended = extend_line(row["rec_body"])
                row["extended"] = extended
                log.add(
                    event="transform", tool="extend_line", workspace="shared",
                    worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                    logical_tick=tick, input=row["rec_body"], output=extended,
                    memory_read=[], attempt=None,
                )
            elif step == 2:
                row = next(item for item in state if item["task"].worker_id == task.worker_id)
                ws.cas(task.worker_id, task.record, row["rec_version"], row["extended"])
                _version, written = ws.read(task.worker_id, task.record)
                row["record_ok"] = written == extend_line(task.initial)
                log.add(
                    event="write_record", tool="write_record", workspace="shared",
                    worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                    logical_tick=tick, input={"expected_version": row["rec_version"], "body": row["extended"]},
                    output=written, memory_read=[], attempt=None,
                )
            else:
                row = next(item for item in state if item["task"].worker_id == task.worker_id)
                row["sv"], row["seen"] = _read_shared(log, ws, "shared", task, tick)
    tick = 4
    need_reread = False
    while True:
        active = [row for row in state if not row["integrated"] and not row["exhausted"]]
        if not active:
            break
        if need_reread:
            tick += 1
            for row in active:
                row["sv"], row["seen"] = _read_shared(log, ws, "shared", row["task"], tick)
        need_reread = True
        tick += 1
        for row in sorted(active, key=lambda item: item["task"].worker_id):
            row["attempts"] += 1
            integrated, conflicts, retry_delta, exhausted = _cas_once(
                log, ws, "shared", row["task"], row["sv"], row["seen"],
                row["attempts"], tick, row["conflicts"], retries,
            )
            row["conflicts"] = conflicts
            row["retries"] += retry_delta
            row["integrated"] = integrated
            row["exhausted"] = exhausted
            if integrated or exhausted:
                row["finished"] = tick
    outcomes = [
        TaskOutcome(
            row["task"].worker_id, row["task"].task_id, row["record_ok"], row["integrated"],
            row["attempts"], row["conflicts"], row["retries"], row["finished"],
        )
        for row in state
    ]
    return _finish(
        "concurrent_shared", "deterministic", "shared", retries, outcomes, log, tick, {"shared": ws}, tasks
    )


def run_concurrent_isolated(tasks: List[Task], max_retries: Optional[int] = None) -> ModeResult:
    tasks = prepare(tasks)
    retries = resolve_retries(len(tasks), max_retries)
    workspaces = {task.worker_id: build_isolated(task) for task in tasks}
    log = Log("concurrent_isolated", "deterministic")
    for task in tasks:
        _seed(log, workspaces[task.worker_id], task.worker_id, [task])
    rows = []
    for step in range(5):
        tick = step + 1
        for task in tasks:
            ws = workspaces[task.worker_id]
            if step == 0:
                version, body = ws.read(task.worker_id, task.record)
                rows.append({
                    "task": task, "version": version, "body": body, "record_ok": False,
                    "conflicts": 0, "retries": 0, "attempts": 0, "integrated": False,
                })
                log.add(
                    event="read_record", tool="read_record", workspace=task.worker_id,
                    worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                    logical_tick=tick, input={"path": task.record, "version": version},
                    output=body, memory_read=[], attempt=None,
                )
            elif step == 1:
                row = next(item for item in rows if item["task"].worker_id == task.worker_id)
                extended = extend_line(row["body"])
                row["extended"] = extended
                log.add(
                    event="transform", tool="extend_line", workspace=task.worker_id,
                    worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                    logical_tick=tick, input=row["body"], output=extended, memory_read=[], attempt=None,
                )
            elif step == 2:
                row = next(item for item in rows if item["task"].worker_id == task.worker_id)
                ws.cas(task.worker_id, task.record, row["version"], row["extended"])
                _version, written = ws.read(task.worker_id, task.record)
                row["record_ok"] = written == extend_line(task.initial)
                log.add(
                    event="write_record", tool="write_record", workspace=task.worker_id,
                    worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                    logical_tick=tick,
                    input={"expected_version": row["version"], "body": row["extended"]},
                    output=written, memory_read=[], attempt=None,
                )
            elif step == 3:
                row = next(item for item in rows if item["task"].worker_id == task.worker_id)
                row["sv"], row["seen"] = _read_shared(log, ws, task.worker_id, task, tick)
            else:
                row = next(item for item in rows if item["task"].worker_id == task.worker_id)
                row["attempts"] = 1
                integrated, conflicts, retry_delta, exhausted = _cas_once(
                    log, ws, task.worker_id, task, row["sv"], row["seen"], 1, tick, 0, retries
                )
                row["integrated"] = integrated
                row["conflicts"] = conflicts
                row["retries"] = retry_delta
                if not integrated and not exhausted:
                    raise RuntimeError("isolated ledger CAS must finish in one attempt")
    outcomes = [
        TaskOutcome(
            row["task"].worker_id, row["task"].task_id, row["record_ok"], row["integrated"],
            row["attempts"], row["conflicts"], row["retries"], 5,
        )
        for row in rows
    ]
    return _finish(
        "concurrent_isolated", "deterministic", "isolated", retries, outcomes, log, 5, workspaces, tasks
    )


def run_threads(tasks: List[Task], max_retries: Optional[int] = None) -> ModeResult:
    tasks = prepare(tasks)
    retries = resolve_retries(len(tasks), max_retries)
    ws = build_shared(tasks)
    log = Log("concurrent_shared_threads", "os_threads")
    _seed(log, ws, "shared", tasks)
    barrier = threading.Barrier(len(tasks), timeout=30)
    outcomes: List[Optional[TaskOutcome]] = [None] * len(tasks)
    errors: List[BaseException] = []
    error_lock = threading.Lock()

    def run_one(index: int, task: Task) -> None:
        passed = False
        try:
            version, body = ws.read(task.worker_id, task.record)
            log.add(
                event="read_record", tool="read_record", workspace="shared",
                worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                logical_tick=None, input={"path": task.record, "version": version},
                output=body, memory_read=[], attempt=None,
            )
            extended = extend_line(body)
            log.add(
                event="transform", tool="extend_line", workspace="shared",
                worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                logical_tick=None, input=body, output=extended, memory_read=[], attempt=None,
            )
            ws.cas(task.worker_id, task.record, version, extended)
            _v, written = ws.read(task.worker_id, task.record)
            record_ok = written == extend_line(task.initial)
            log.add(
                event="write_record", tool="write_record", workspace="shared",
                worker_id=task.worker_id, task_id=task.task_id, path=task.record,
                logical_tick=None, input={"expected_version": version, "body": extended},
                output=written, memory_read=[], attempt=None,
            )
            seen_version, seen_body = ws.read(task.worker_id, SHARED_PATH)
            log.add(
                event="read_shared", tool="read_shared", workspace="shared",
                worker_id=task.worker_id, task_id=task.task_id, path=SHARED_PATH,
                logical_tick=None, input={"path": SHARED_PATH},
                output={"version": seen_version, "body": seen_body}, memory_read=[], attempt=None,
            )
            barrier.wait()
            passed = True
            conflicts = 0
            retry_count = 0
            attempts = 0
            integrated = False
            while True:
                attempts += 1
                integrated, conflicts, retry_delta, exhausted = _cas_once(
                    log, ws, "shared", task, seen_version, seen_body, attempts, None, conflicts, retries
                )
                retry_count += retry_delta
                if integrated or exhausted:
                    break
                seen_version, seen_body = ws.read(task.worker_id, SHARED_PATH)
                log.add(
                    event="read_shared", tool="read_shared", workspace="shared",
                    worker_id=task.worker_id, task_id=task.task_id, path=SHARED_PATH,
                    logical_tick=None, input={"path": SHARED_PATH},
                    output={"version": seen_version, "body": seen_body}, memory_read=[], attempt=None,
                )
            outcomes[index] = TaskOutcome(
                task.worker_id, task.task_id, record_ok, integrated, attempts, conflicts, retry_count, None
            )
        except Exception as exc:
            with error_lock:
                errors.append(exc)
            if not passed:
                try:
                    barrier.abort()
                except Exception:
                    pass

    threads = [
        threading.Thread(target=run_one, args=(index, task), name=f"synthetic-{task.worker_id}", daemon=True)
        for index, task in enumerate(tasks)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    if any(thread.is_alive() for thread in threads):
        raise RuntimeError("a scripted worker thread did not finish within 30 seconds")
    if errors:
        raise RuntimeError(f"scripted worker failed: {errors[0]}") from errors[0]
    if any(outcome is None for outcome in outcomes):
        raise RuntimeError("a scripted worker produced no outcome")
    done: List[TaskOutcome] = [outcome for outcome in outcomes if outcome is not None]
    return _finish(
        "concurrent_shared_threads", "os_threads", "shared", retries, done, log, None, {"shared": ws}, tasks
    )


def run_suite(tasks: List[Task], max_retries: Optional[int] = None, threads: bool = True) -> List[ModeResult]:
    """Run the reproducible modes, then OS threads when requested.

    When max_retries is omitted, deterministic modes use n - 1 (enough for the
    barrier rule to integrate every worker) and the thread mode uses 1000 so a
    slow scheduler can still finish. An explicit max_retries applies to all modes.
    """
    n = len(prepare(tasks))
    retries = resolve_retries(n, max_retries)
    modes = [
        run_serial(tasks, retries),
        run_concurrent_shared(tasks, retries),
        run_concurrent_isolated(tasks, retries),
    ]
    if threads:
        thread_retries = 1000 if max_retries is None else retries
        modes.append(run_threads(tasks, thread_retries))
    return modes
