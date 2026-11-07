import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contention.tasks import INITIAL_COUNTER, SHARED_PATH, make_tasks
from contention.workspace import (
    ConflictError,
    ProtectedError,
    build_shared,
    memory_marker_path,
    normalize,
)


class WorkspaceTests(unittest.TestCase):
    def test_path_jail_rejects_escape(self):
        for path in ("../outside.json", "/tmp/x.json", "records/../../etc/passwd", "memory/w01/../../shared/counter.json", "a\\b", ""):
            with self.subTest(path=path):
                with self.assertRaises(ProtectedError):
                    normalize(path)
        self.assertEqual(normalize("records/./w01.json"), "records/w01.json")

    def test_cross_worker_record_write_is_refused(self):
        tasks = make_tasks(2)
        ws = build_shared(tasks)
        version, body = ws.read("w02", tasks[0].record)
        with self.assertRaises(ProtectedError) as caught:
            ws.cas("w02", tasks[0].record, version, body)
        self.assertEqual(caught.exception.reason, "grant")
        self.assertEqual(ws.snapshot()[tasks[0].record]["version"], 0)
        self.assertEqual(ws.rejection_count("schedule"), 1)

    def test_scoped_memory_cannot_be_widened_by_a_grant(self):
        tasks = make_tasks(2)
        ws = build_shared(tasks)
        path = memory_marker_path("w01")
        ws.write_new("w01", path, {"marker": "synthetic-w01"}, phase="probe")
        ws.allow("w02", {tasks[1].record, SHARED_PATH, path})
        with self.assertRaises(ProtectedError) as caught:
            ws.read("w02", path, phase="probe")
        self.assertEqual(caught.exception.reason, "scoped_memory")
        version, body = ws.read("w01", path, phase="probe")
        self.assertEqual(body["marker"], "synthetic-w01")
        self.assertEqual(version, 1)
        self.assertIn(path, ws.snapshot())

    def test_compare_and_swap_conflict_keeps_the_previous_body(self):
        tasks = make_tasks(1)
        ws = build_shared(tasks)
        version, body = ws.read("w01", SHARED_PATH)
        self.assertEqual(body, INITIAL_COUNTER)
        ws.cas("w01", SHARED_PATH, version, {"total": 1, "owners": ["w01"]})
        with self.assertRaises(ConflictError):
            ws.cas("w01", SHARED_PATH, version, {"total": 99, "owners": ["w01"]})
        self.assertEqual(ws.snapshot()[SHARED_PATH]["body"], {"total": 1, "owners": ["w01"]})


if __name__ == "__main__":
    unittest.main()
