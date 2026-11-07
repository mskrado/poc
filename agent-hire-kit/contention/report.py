"""Correctness checks and CSV/JSONL artifacts.

Passing checks means the scripted fixture behaved as specified. It does not
measure agents, people, or a production system.
"""

from __future__ import annotations

import csv
import json
import os
import platform
import sys
from pathlib import Path
from typing import List

from .banner import (
    AUTHOR,
    BANNER,
    ISOLATION_LIMIT,
    MODEL_VERSION,
    NOT_MEASURED,
    PACKET,
    RELEASE,
    SIMULATION,
)
from .contract import contract_concurrent_shared, contract_isolated, contract_serial
from .replay import ReplayError, replay_ledger, replay_task
from .schedule import ModeResult
from .tasks import SHARED_PATH, extend_line
from .workspace import memory_marker_path


AUDIT_KEYS = ("tool", "input", "output", "model_version", "memory_read")

DEFINITIONS = {
    "useful_completed": (
        "The worker's record equals qty * unit_cents and that worker appears once "
        "in the ledger of the workspace it wrote."
    ),
    "conflict": "A compare-and-swap found a newer file version than the worker had read.",
    "retry": "Another compare-and-swap attempt after a conflict.",
    "logical_ticks": (
        "Scripted schedule clock. Overlapping steps share a tick. Not wall time, "
        "and not human time."
    ),
    "schedule_wall_seconds": (
        "time.perf_counter around the schedule only, before the memory probe and "
        "before writing artifacts. Machine-dependent. Not an agent or human measurement."
    ),
    "workers": "Deterministic Python functions, or OS threads running those functions. Not AI agents.",
}


def runtime_metadata() -> dict:
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
    }


def _ledger(result: ModeResult, worker_id: str = "shared") -> dict:
    key = "shared" if result.workspace_layout == "shared" else worker_id
    return result.workspaces[key].snapshot()[SHARED_PATH]["body"]


def verify_mode(result: ModeResult) -> List[str]:
    errors: List[str] = []
    tasks = result.tasks
    n = len(tasks)
    prefix = result.mode

    for event in result.events:
        missing = [key for key in AUDIT_KEYS if key not in event]
        if missing:
            errors.append(f"{prefix} event {event.get('event')} missing {missing}")
            continue
        if event["model_version"] != MODEL_VERSION:
            errors.append(f"{prefix} model_version is not the synthetic script id")
        if not isinstance(event["memory_read"], list):
            errors.append(f"{prefix} memory_read is not a list")
        if event["event"] == "read_memory_denied":
            if event["memory_read"] != []:
                errors.append(f"{prefix} denied memory read still lists memory_read entries")
            if not isinstance(event["output"], dict) or event["output"].get("allowed") is not False:
                errors.append(f"{prefix} denied memory read is not marked allowed=false")
            if "synthetic-" in json.dumps(event["output"]):
                errors.append(f"{prefix} denied memory read includes marker text")

    for task in tasks:
        key = "shared" if result.workspace_layout == "shared" else task.worker_id
        body = result.workspaces[key].snapshot()[task.record]["body"]
        formula = extend_line(task.initial)
        if body != formula or body["extended_cents"] != body["qty"] * body["unit_cents"]:
            errors.append(f"{prefix} {task.task_id} record does not equal qty * unit_cents")
        try:
            replayed = replay_task(result.events, task.task_id)
        except ReplayError as exc:
            errors.append(f"{prefix} {exc}")
        else:
            if replayed != formula:
                errors.append(f"{prefix} {task.task_id} replay does not equal the fixture formula")

    if result.workspace_layout == "shared":
        ledger = _ledger(result)
        owners = ledger.get("owners")
        if not isinstance(owners, list) or ledger.get("total") != len(owners) or len(owners) != len(set(owners)):
            errors.append(f"{prefix} ledger total, owners, and unique owners disagree")
        else:
            try:
                folded = replay_ledger(result.events, "shared")
            except ReplayError as exc:
                errors.append(f"{prefix} {exc}")
            else:
                if folded != ledger:
                    errors.append(f"{prefix} ledger replay does not match the workspace")
            if result.scheduler == "os_threads":
                integrated = {outcome.worker_id for outcome in result.outcomes if outcome.integrated}
                if set(owners) != integrated:
                    errors.append(f"{prefix} thread ledger owners do not match integrated workers")
            else:
                integrated = [outcome.worker_id for outcome in result.outcomes if outcome.integrated]
                if owners != integrated:
                    errors.append(f"{prefix} ledger order {owners} does not match integrated workers {integrated}")
        snap = result.workspaces["shared"].snapshot()
        for task in tasks:
            if memory_marker_path(task.worker_id) not in snap:
                errors.append(f"{prefix} {task.worker_id} marker is missing from the shared snapshot")
    else:
        for task in tasks:
            ledger = _ledger(result, task.worker_id)
            if ledger != {"total": 1, "owners": [task.worker_id]}:
                errors.append(f"{prefix} {task.worker_id} isolated ledger is not a private total of 1")
            try:
                folded = replay_ledger(result.events, task.worker_id)
            except ReplayError as exc:
                errors.append(f"{prefix} {exc}")
            else:
                if folded != ledger:
                    errors.append(f"{prefix} {task.worker_id} isolated ledger replay mismatch")
            allowed = {task.record, SHARED_PATH, memory_marker_path(task.worker_id)}
            present = set(result.workspaces[task.worker_id].snapshot())
            if present != allowed:
                errors.append(f"{prefix} {task.worker_id} isolated paths {sorted(present)} are not {sorted(allowed)}")

    conflict_events = sum(1 for event in result.events if event["event"] == "cas_conflict")
    retry_events = sum(1 for event in result.events if event["event"] == "retry")
    if conflict_events != result.conflicts:
        errors.append(f"{prefix} conflict events {conflict_events} != outcome conflicts {result.conflicts}")
    if retry_events != result.retries:
        errors.append(f"{prefix} retry events {retry_events} != outcome retries {result.retries}")
    for outcome in result.outcomes:
        if outcome.attempts < 1 or outcome.retries != outcome.attempts - 1:
            errors.append(f"{prefix} {outcome.worker_id} retries are not attempts minus one")
        if outcome.useful and not (outcome.record_ok and outcome.integrated):
            errors.append(f"{prefix} {outcome.worker_id} useful flag is inconsistent")

    if result.records_correct != n:
        errors.append(f"{prefix} records_correct {result.records_correct} != {n}")
    if result.schedule_rejections != 0:
        errors.append(f"{prefix} schedule rejected {result.schedule_rejections} writes or reads")

    probe = result.probe
    expected_denied = 0 if n < 2 else n
    if probe.get("own_reads_ok") != n:
        errors.append(f"{prefix} own memory reads {probe.get('own_reads_ok')} != {n}")
    if probe.get("cross_reads_denied") != expected_denied or probe.get("cross_reads_succeeded") != 0:
        errors.append(
            f"{prefix} scoped-memory probe denied {probe.get('cross_reads_denied')} "
            f"and leaked {probe.get('cross_reads_succeeded')}"
        )
    if result.workspace_layout == "isolated" and probe.get("markers_absent_from_other_workspaces") != n * (n - 1):
        errors.append(f"{prefix} isolated workspaces still contain another worker's marker")

    if result.mode == "serial_shared":
        _match_contract(errors, result, contract_serial(n))
    elif result.mode == "concurrent_shared":
        spec = contract_concurrent_shared(n, result.max_retries)
        _match_contract(errors, result, spec)
        if result.workspace_layout == "shared" and _ledger(result).get("owners") != spec["owners"]:
            errors.append(f"{prefix} owners {_ledger(result).get('owners')} != contract {spec['owners']}")
    elif result.mode == "concurrent_isolated":
        _match_contract(errors, result, contract_isolated(n))
    elif result.mode == "concurrent_shared_threads":
        if result.logical_ticks is not None:
            errors.append(f"{prefix} thread mode must not invent logical ticks")
        if result.useful != n:
            errors.append(f"{prefix} thread mode integrated {result.useful} of {n}")
        if result.conflicts < max(0, n - 1):
            errors.append(f"{prefix} thread mode recorded {result.conflicts} conflicts; the barrier requires at least {n - 1}")
        if result.retries != result.conflicts:
            errors.append(f"{prefix} thread retries {result.retries} != conflicts {result.conflicts}")
        if set(_ledger(result).get("owners") or []) != {task.worker_id for task in tasks}:
            errors.append(f"{prefix} thread ledger is missing a worker")
    else:
        errors.append(f"unknown mode {result.mode}")

    if result.schedule_wall_seconds < 0:
        errors.append(f"{prefix} negative wall time")
    return errors


def _match_contract(errors: List[str], result: ModeResult, spec: dict) -> None:
    pairs = (
        ("useful", result.useful, spec["useful"]),
        ("conflicts", result.conflicts, spec["conflicts"]),
        ("retries", result.retries, spec["retries"]),
        ("logical_ticks", result.logical_ticks, spec["logical_ticks"]),
    )
    for name, got, want in pairs:
        if got != want:
            errors.append(f"{result.mode} {name} {got} != schedule contract {want}")


def verify_suite(results: List[ModeResult]) -> List[str]:
    errors: List[str] = []
    for result in results:
        errors.extend(verify_mode(result))
    return errors


def mode_row(result: ModeResult) -> dict:
    ledger_owners = None
    if result.workspace_layout == "shared":
        ledger_owners = _ledger(result).get("owners")
    return {
        "mode": result.mode,
        "scheduler": result.scheduler,
        "workspace_layout": result.workspace_layout,
        "workers": len(result.tasks),
        "tasks": len(result.tasks),
        "useful_completed": result.useful,
        "records_correct": result.records_correct,
        "integrated": result.integrated_count,
        "conflicts": result.conflicts,
        "retries": result.retries,
        "schedule_rejections": result.schedule_rejections,
        "logical_ticks": result.logical_ticks,
        "schedule_wall_seconds": result.schedule_wall_seconds,
        "max_retries": result.max_retries,
        "ledger_owners": ledger_owners,
        "probe": result.probe,
        "simulation": SIMULATION,
    }


def build_summary(results: List[ModeResult], errors: List[str]) -> dict:
    return {
        "banner": BANNER,
        "isolation_limit": ISOLATION_LIMIT,
        "kit": "agent-hire-kit",
        "component": "contention-harness",
        "author": AUTHOR,
        "release": RELEASE,
        "packet": PACKET,
        "simulation": SIMULATION,
        "planned_workers": 10,
        "model_version": MODEL_VERSION,
        "not_measured": list(NOT_MEASURED),
        "definitions": DEFINITIONS,
        "comparison_note": (
            "Deterministic modes differ by the scripted overlap rule. "
            "The same useful_completed with different conflicts means the script "
            "finished the same fixture tasks, not that agents or people are faster."
        ),
        "runtime": runtime_metadata(),
        "modes": [mode_row(result) for result in results],
        "assertions": {"passed": not errors, "errors": errors},
        "checks": [
            "record_formula",
            "task_replay",
            "ledger_replay",
            "scoped_memory",
            "schedule_contract_or_thread_bound",
            "audit_fields",
        ],
    }


def write_artifacts(out: Path, results: List[ModeResult], errors: List[str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    summary = build_summary(results, errors)
    (out / "LABEL.txt").write_text(
        BANNER + "\n\n" + ISOLATION_LIMIT + "\n\n"
        "Workspace snapshots are run artifacts for inspection. They are not a tenant boundary.\n"
        "The scoped-memory check is the workspace API: another scripted worker's read is refused.\n",
        encoding="utf-8",
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_summary_csv(out / "summary.csv", results)
    _write_tasks_csv(out / "tasks.csv", results)
    _write_events(out / "events.jsonl", results)
    _write_run_log(out / "run.log", results)
    for result in results:
        for name, ws in result.workspaces.items():
            base = out / "workspaces" / result.mode / name
            for path, payload in ws.snapshot().items():
                dest = base / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_summary_csv(path: Path, results: List[ModeResult]) -> None:
    fields = [
        "mode", "scheduler", "workspace_layout", "workers", "tasks", "useful_completed",
        "records_correct", "integrated", "conflicts", "retries", "schedule_rejections",
        "logical_ticks", "schedule_wall_seconds", "max_retries",
        "probe_cross_reads_denied", "probe_cross_reads_succeeded", "simulation",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = mode_row(result)
            writer.writerow({
                "mode": row["mode"],
                "scheduler": row["scheduler"],
                "workspace_layout": row["workspace_layout"],
                "workers": row["workers"],
                "tasks": row["tasks"],
                "useful_completed": row["useful_completed"],
                "records_correct": row["records_correct"],
                "integrated": row["integrated"],
                "conflicts": row["conflicts"],
                "retries": row["retries"],
                "schedule_rejections": row["schedule_rejections"],
                "logical_ticks": "" if row["logical_ticks"] is None else row["logical_ticks"],
                "schedule_wall_seconds": f"{row['schedule_wall_seconds']:.6f}",
                "max_retries": row["max_retries"],
                "probe_cross_reads_denied": result.probe.get("cross_reads_denied"),
                "probe_cross_reads_succeeded": result.probe.get("cross_reads_succeeded"),
                "simulation": SIMULATION,
            })


def _write_tasks_csv(path: Path, results: List[ModeResult]) -> None:
    fields = [
        "mode", "scheduler", "worker_id", "task_id", "record_ok", "integrated", "useful",
        "attempts", "conflicts", "retries", "finished_logical_tick", "simulation",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            for outcome in result.outcomes:
                writer.writerow({
                    "mode": result.mode,
                    "scheduler": result.scheduler,
                    "worker_id": outcome.worker_id,
                    "task_id": outcome.task_id,
                    "record_ok": str(outcome.record_ok).lower(),
                    "integrated": str(outcome.integrated).lower(),
                    "useful": str(outcome.useful).lower(),
                    "attempts": outcome.attempts,
                    "conflicts": outcome.conflicts,
                    "retries": outcome.retries,
                    "finished_logical_tick": "" if outcome.finished_logical_tick is None else outcome.finished_logical_tick,
                    "simulation": SIMULATION,
                })


def _write_events(path: Path, results: List[ModeResult]) -> None:
    seq = 0
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            for event in result.events:
                seq += 1
                row = dict(event)
                row["seq"] = seq
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def _write_run_log(path: Path, results: List[ModeResult]) -> None:
    lines = [BANNER, ISOLATION_LIMIT, ""]
    for result in results:
        for event in result.events:
            lines.append(
                f"{event['mode']} tick={event['logical_tick']} {event['event']} "
                f"worker={event['worker_id']} task={event['task_id']} tool={event['tool']} "
                f"path={event['path']}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
