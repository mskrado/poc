"""In-process workspace with a path jail, write grants, and private memory paths.

This is a simulation fixture. Refusing a cross-worker read here is not a
production memory-isolation, credential, or security result.
"""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Set


class WorkspaceError(Exception):
    pass


class ProtectedError(WorkspaceError):
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"{reason}: {path}")


class ConflictError(WorkspaceError):
    def __init__(self, path: str, expected: int, actual: int):
        self.path = path
        self.expected = expected
        self.actual = actual
        super().__init__(f"conflict on {path}: saw version {expected}, actual {actual}")


@dataclass
class FileState:
    version: int
    body: dict


def normalize(path: str) -> str:
    """Reject absolute paths and any '..' segment. Return a posix relative path."""
    if not isinstance(path, str) or path == "" or path.startswith(("/", "\\")) or "\\" in path or "\x00" in path:
        raise ProtectedError(str(path), "path_jail")
    parts = PurePosixPath(path).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ProtectedError(path, "path_jail")
    return "/".join(parts)


def memory_owner(path: str) -> Optional[str]:
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "memory":
        return parts[1]
    return None


def memory_marker_path(worker_id: str) -> str:
    return f"memory/{worker_id}/marker.json"


class Workspace:
    def __init__(self, label: str):
        self.label = label
        self.files: Dict[str, FileState] = {}
        self.grants: Dict[str, Set[str]] = {}
        self.rejected: List[dict] = []
        self._commit_seq = 0
        self._lock = threading.Lock()

    def seed(self, path: str, body: dict) -> None:
        path = normalize(path)
        with self._lock:
            if path in self.files:
                raise WorkspaceError(f"already seeded: {path}")
            self.files[path] = FileState(0, copy.deepcopy(body))

    def allow(self, worker_id: str, paths: Set[str]) -> None:
        self.grants[worker_id] = {normalize(p) for p in paths}

    def read(self, worker_id: str, path: str, phase: str = "schedule") -> tuple:
        path = self._normalize_or_reject(worker_id, path, phase)
        with self._lock:
            self._authorize(worker_id, path, write=False, phase=phase)
            state = self.files.get(path)
            if state is None:
                raise WorkspaceError(f"missing {path}")
            return state.version, copy.deepcopy(state.body)

    def cas(self, worker_id: str, path: str, expected: int, new_body: dict, phase: str = "schedule"):
        path = self._normalize_or_reject(worker_id, path, phase)
        with self._lock:
            self._authorize(worker_id, path, write=True, phase=phase)
            state = self.files.get(path)
            if state is None:
                raise WorkspaceError(f"missing {path}")
            if state.version != expected:
                raise ConflictError(path, expected, state.version)
            self._commit_seq += 1
            state.version += 1
            state.body = copy.deepcopy(new_body)
            return state.version, self._commit_seq

    def write_new(self, worker_id: str, path: str, body: dict, phase: str = "schedule") -> int:
        path = self._normalize_or_reject(worker_id, path, phase)
        with self._lock:
            self._authorize(worker_id, path, write=True, phase=phase)
            if path in self.files:
                raise WorkspaceError(f"exists: {path}")
            self.files[path] = FileState(1, copy.deepcopy(body))
            return 1

    def snapshot(self) -> Dict[str, dict]:
        with self._lock:
            return {
                path: {"version": state.version, "body": copy.deepcopy(state.body)}
                for path, state in self.files.items()
            }

    def rejection_count(self, phase: str) -> int:
        return sum(1 for row in self.rejected if row["phase"] == phase)

    def _normalize_or_reject(self, worker_id: str, path: str, phase: str) -> str:
        try:
            return normalize(path)
        except ProtectedError:
            with self._lock:
                self._reject(worker_id, str(path), "path_jail", phase)
            raise

    def _authorize(self, worker_id: str, path: str, write: bool, phase: str) -> None:
        owner = memory_owner(path)
        if owner is not None:
            if owner != worker_id:
                self._reject(worker_id, path, "scoped_memory", phase)
                raise ProtectedError(path, "scoped_memory")
            return
        if write and path not in self.grants.get(worker_id, set()):
            self._reject(worker_id, path, "grant", phase)
            raise ProtectedError(path, "grant")

    def _reject(self, worker_id: str, path: str, reason: str, phase: str) -> None:
        self.rejected.append({
            "worker_id": worker_id,
            "path": path,
            "reason": reason,
            "phase": phase,
        })


def build_shared(tasks: list) -> Workspace:
    from .tasks import INITIAL_COUNTER, SHARED_PATH
    ws = Workspace("shared")
    ws.seed(SHARED_PATH, INITIAL_COUNTER)
    for task in tasks:
        ws.seed(task.record, task.initial)
        ws.allow(task.worker_id, {task.record, SHARED_PATH})
    return ws


def build_isolated(task) -> Workspace:
    from .tasks import INITIAL_COUNTER, SHARED_PATH
    ws = Workspace(f"isolated/{task.worker_id}")
    ws.seed(task.record, task.initial)
    ws.seed(SHARED_PATH, INITIAL_COUNTER)
    ws.allow(task.worker_id, {task.record, SHARED_PATH})
    return ws
