import ast
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contention.banner import BANNER, ISOLATION_LIMIT, MODEL_VERSION
from contention.cli import main
from contention.replay import replay_ledger, replay_task
from contention.tasks import load_fixture, make_tasks


class CliTests(unittest.TestCase):
    def test_fixture_is_the_planned_ten(self):
        loaded = load_fixture()
        self.assertEqual(loaded, make_tasks(10))
        self.assertEqual(loaded[0].expected["extended_cents"], 100)
        self.assertEqual(loaded[9].expected["extended_cents"], 3250)

    def test_clean_run_writes_artifacts_and_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            from io import StringIO
            import contextlib
            stdout = StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["--out", str(out), "--skip-threads"])
            text = stdout.getvalue()
            self.assertEqual(code, 0, text)
            self.assertIn("SYNTHETIC CONTENTION SIMULATION", text)
            self.assertIn("not ten AI agents", text)
            self.assertIn("assertions: PASS", text)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["banner"], BANNER)
            self.assertEqual(summary["isolation_limit"], ISOLATION_LIMIT)
            self.assertEqual(summary["author"], "Rex Circuit")
            self.assertEqual(summary["release"], "v26.10.31")
            self.assertEqual(summary["packet"], "PF-20261031-fewer-people-more-agents")
            self.assertTrue(summary["assertions"]["passed"])
            self.assertIn("human cleanup time", summary["not_measured"])
            self.assertIn("ten actual AI agents", summary["not_measured"])
            blob = json.dumps(summary)
            self.assertNotIn("hours_saved", blob)
            self.assertIn("Do not quote these figures as agent speedup", blob)
            self.assertNotIn("speedup_ratio", blob)
            modes = {row["mode"]: row for row in summary["modes"]}
            self.assertEqual(modes["serial_shared"]["useful_completed"], 10)
            self.assertEqual(modes["serial_shared"]["conflicts"], 0)
            self.assertEqual(modes["serial_shared"]["logical_ticks"], 50)
            self.assertEqual(modes["concurrent_shared"]["conflicts"], 45)
            self.assertEqual(modes["concurrent_shared"]["retries"], 45)
            self.assertEqual(modes["concurrent_shared"]["logical_ticks"], 23)
            self.assertEqual(modes["concurrent_isolated"]["conflicts"], 0)
            self.assertEqual(modes["concurrent_isolated"]["logical_ticks"], 5)
            self.assertNotIn("concurrent_shared_threads", modes)
            events = [json.loads(line) for line in (out / "events.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertGreater(len(events), 10)
            self.assertEqual(events[0]["model_version"], MODEL_VERSION)
            self.assertIn("memory_read", events[0])
            serial = [event for event in events if event["mode"] == "serial_shared"]
            self.assertEqual(replay_task(serial, "t03")["extended_cents"], 3 * 150)
            self.assertEqual(replay_ledger(serial, "shared")["total"], 10)
            denied = [event for event in serial if event["event"] == "read_memory_denied"]
            self.assertEqual(len(denied), 10)
            self.assertTrue(all(event["memory_read"] == [] for event in denied))
            with (out / "summary.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[1]["simulation"], "synthetic_scripted_workers")
            self.assertTrue((out / "tasks.csv").is_file())
            self.assertTrue((out / "run.log").is_file())
            self.assertIn("SYNTHETIC CONTENTION SIMULATION", (out / "LABEL.txt").read_text(encoding="utf-8"))
            runtime = summary["runtime"]
            self.assertIn("python", runtime)
            self.assertIn("cpu_count", runtime)
            self.assertNotIn("node", runtime)
            self.assertNotIn("user", runtime)

    def test_threads_flag_stays_inside_the_invariants(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            from io import StringIO
            import contextlib
            with contextlib.redirect_stdout(StringIO()):
                code = main(["--out", str(out)])
            self.assertEqual(code, 0)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            threads = [row for row in summary["modes"] if row["mode"] == "concurrent_shared_threads"][0]
            self.assertEqual(threads["useful_completed"], 10)
            self.assertGreaterEqual(threads["conflicts"], 9)
            self.assertIsNone(threads["logical_ticks"])
            self.assertEqual(threads["probe"]["cross_reads_succeeded"], 0)

    def test_refuses_a_nonempty_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            out.mkdir()
            (out / "keep.txt").write_text("x", encoding="utf-8")
            from io import StringIO
            import contextlib
            with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
                code = main(["--out", str(out), "--skip-threads"])
            self.assertEqual(code, 2)
            self.assertTrue((out / "keep.txt").is_file())

    def test_harness_source_does_not_import_network_clients(self):
        banned = {"socket", "urllib", "http", "requests", "openai", "anthropic", "subprocess"}
        for path in (ROOT / "contention").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".")[0]]
                self.assertFalse(banned.intersection(names), f"{path.name} imports {names}")


if __name__ == "__main__":
    unittest.main()
