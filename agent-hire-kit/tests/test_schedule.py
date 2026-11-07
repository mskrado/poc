import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contention.contract import contract_concurrent_shared, contract_isolated, contract_serial
from contention.replay import ReplayError, replay_ledger, replay_task
from contention.report import verify_mode
from contention.schedule import run_concurrent_isolated, run_concurrent_shared, run_serial, run_suite, run_threads
from contention.tasks import make_tasks


def _strip(events):
    cleaned = []
    for event in events:
        row = dict(event)
        row.pop("wall_s", None)
        cleaned.append(row)
    return cleaned


class ScheduleContractTests(unittest.TestCase):
    def test_contract_for_planned_size(self):
        self.assertEqual(contract_serial(10)["logical_ticks"], 50)
        self.assertEqual(contract_serial(10)["conflicts"], 0)
        spec = contract_concurrent_shared(10, 9)
        self.assertEqual(spec["useful"], 10)
        self.assertEqual(spec["conflicts"], 45)
        self.assertEqual(spec["retries"], 45)
        self.assertEqual(spec["logical_ticks"], 23)
        self.assertEqual(spec["owners"], [f"w{i:02d}" for i in range(1, 11)])
        self.assertEqual(contract_isolated(10)["logical_ticks"], 5)
        self.assertEqual(contract_isolated(10)["conflicts"], 0)

    def test_scheduler_matches_contract_across_sizes(self):
        for n in range(1, 11):
            for retries in range(0, n):
                with self.subTest(n=n, retries=retries):
                    tasks = make_tasks(n)
                    serial = run_serial(tasks, retries)
                    shared = run_concurrent_shared(tasks, retries)
                    isolated = run_concurrent_isolated(tasks, retries)
                    self.assertEqual(verify_mode(serial), [])
                    self.assertEqual(verify_mode(shared), [])
                    self.assertEqual(verify_mode(isolated), [])

    def test_low_retries_leave_correct_records_unintegrated(self):
        result = run_concurrent_shared(make_tasks(10), 0)
        self.assertEqual(result.useful, 1)
        self.assertEqual(result.records_correct, 10)
        self.assertEqual(result.conflicts, 9)
        self.assertEqual(result.retries, 0)
        self.assertEqual(result.logical_ticks, 5)
        self.assertEqual(verify_mode(result), [])

    def test_one_retry_integrates_two_workers(self):
        result = run_concurrent_shared(make_tasks(10), 1)
        self.assertEqual(result.useful, 2)
        self.assertEqual(result.conflicts, 17)
        self.assertEqual(result.retries, 9)
        self.assertEqual(result.logical_ticks, 7)
        self.assertEqual(verify_mode(result), [])

    def test_worker_order_does_not_change_the_winner(self):
        tasks = list(reversed(make_tasks(4)))
        result = run_concurrent_shared(tasks, 0)
        self.assertEqual(result.outcomes[0].worker_id, "w01")
        self.assertTrue(result.outcomes[0].integrated)
        self.assertEqual(verify_mode(result), [])

    def test_deterministic_repeat(self):
        tasks = make_tasks(10)
        first = run_suite(tasks, threads=False)
        second = run_suite(tasks, threads=False)
        for left, right in zip(first, second):
            self.assertEqual(_strip(left.events), _strip(right.events))
            self.assertEqual(left.conflicts, right.conflicts)
            self.assertEqual(left.logical_ticks, right.logical_ticks)

    def test_replay_one_task_from_the_log_alone(self):
        result = run_serial(make_tasks(10), 9)
        # Drop the workspace. The log is the only input.
        events = result.events
        recomputed = replay_task(events, "t01")
        self.assertEqual(recomputed["extended_cents"], 1 * 100)
        recomputed = replay_task(events, "t10")
        self.assertEqual(recomputed["extended_cents"], 10 * 325)
        self.assertEqual(replay_ledger(events, "shared")["total"], 10)

    def test_replay_rejects_a_tampered_log(self):
        events = [dict(event) for event in run_serial(make_tasks(2), 1).events]
        for event in events:
            if event["event"] == "transform" and event["task_id"] == "t01":
                event["output"] = dict(event["output"])
                event["output"]["extended_cents"] = -1
        with self.assertRaises(ReplayError):
            replay_task(events, "t01")

    def test_isolated_ledgers_are_not_merged(self):
        result = run_concurrent_isolated(make_tasks(10), 9)
        self.assertEqual(result.useful, 10)
        self.assertEqual(result.conflicts, 0)
        totals = []
        for task in result.tasks:
            ledger = result.workspaces[task.worker_id].snapshot()["shared/counter.json"]["body"]
            totals.append(ledger["total"])
            self.assertEqual(ledger["owners"], [task.worker_id])
        self.assertEqual(totals, [1] * 10)
        self.assertEqual(result.probe["markers_absent_from_other_workspaces"], 90)
        self.assertEqual(result.probe["cross_reads_succeeded"], 0)
        self.assertEqual(verify_mode(result), [])


class ThreadTests(unittest.TestCase):
    def test_thread_invariants_repeat(self):
        tasks = make_tasks(10)
        for _ in range(20):
            result = run_threads(tasks, 1000)
            errors = verify_mode(result)
            self.assertEqual(errors, [], errors)
            self.assertGreaterEqual(result.conflicts, 9)
            self.assertIsNone(result.logical_ticks)
            replay_task(result.events, "t04")
            self.assertEqual(replay_ledger(result.events, "shared")["total"], 10)


if __name__ == "__main__":
    unittest.main()
