# Contention harness

Rex Circuit's section of the Agent Hire Kit (release v26.10.31, packet PF-20261031-fewer-people-more-agents).

**SYNTHETIC CONTENTION SIMULATION.** These are scripted workers, not ten AI agents. No human cleanup was measured. Do not quote these figures as agent speedup or hours saved.

The harness compares three deterministic schedules, plus an optional OS-thread run, on one local fixture of 10 invented ledger lines. A line is done when `extended_cents` equals `qty * unit_cents` and the worker id appears once in the ledger that worker was allowed to write.

## What is measured

- Useful completed tasks, conflicts, and retries.
- Logical ticks: a scripted clock. Overlapping steps share a tick. This is not wall time and not human time.
- `schedule_wall_seconds`: `time.perf_counter` around the schedule on the machine that runs it. It is metadata. It is not a finding.
- A raw event log (`events.jsonl`, `run.log`) with input, tool, output, the synthetic script id, and memory paths read.
- Runtime metadata: Python version, implementation, platform, machine, and CPU count. No hostname and no user name.
- A protected-workspace comparison: path jail, per-worker write grants, and a private memory path. The isolated mode gives each worker a separate copy of the counter.

## What is not measured

Ten actual AI agents. Model quality or latency. Human cleanup, human effort, or hours saved. Cost, headcount, or a hire decision. Production memory isolation, credential isolation, or a security certification.

Dr. Orion Kade's checklist items 3 (scoped memory) and 5 (replayable audit log) have fixture tests here. A scripted worker A writes a marker; worker B's read is refused. One past task is recomputed from the log alone, and the ledger is folded from logged compare-and-swap events. **Those checks cover this simulation's fixtures only.** They are not proof of production AI memory isolation, credential isolation, or a security certification. The checklist remains a design checklist, not a benchmark.

Passing a run means the script matched its own contract and the fixture arithmetic. It does not mean a team should hire or cut anyone.

## Schedule contract

Deterministic workers read the shared counter together. The lowest remaining worker id commits. The others record a conflict and retry until retries run out. With 10 workers and 9 retries, that is 9+8+...+1 = 45 conflicts and 45 retries, and all 10 records still match the fixture. Private record writes do not share a path, so they do not conflict. Logical ticks charge 4 for the overlapped private prefix, then one tick per compare-and-swap wave and one tick per later re-read (23 in the full run). Serial work does not overlap (50 ticks) and does not conflict. Isolated workers each keep a private counter, so the script records no conflicts and does not merge those counters into one total of 10.

| Mode | Scheduler | Useful | Conflicts | Retries | Logical ticks |
|---|---|---:|---:|---:|---:|
| serial_shared | deterministic | 10 | 0 | 0 | 50 |
| concurrent_shared | deterministic | 10 | 45 | 45 | 23 |
| concurrent_isolated | deterministic | 10 | 0 | 0 | 5 |
| concurrent_shared_threads | os threads | 10 if retries suffice | scheduler-dependent | scheduler-dependent | n/a |

The thread mode starts all 10 workers, waits until each has read the counter, then lets compare-and-swap races run. The first wave records at least 9 conflicts. The exact count depends on the interpreter and is not a stable benchmark. The thread mode does not invent logical ticks.

Wall-clock seconds are written to the artifacts for the machine that ran the command. This README does not quote them.

## Clean-machine run

Python 3.9 or newer. Standard library only. No install, no API key, no network.

```bash
cd agent-hire-kit
python3 -m contention --out out/run
python3 -m unittest discover -s tests -v
```

`--out` must be a new or empty directory. The default path is `out/synthetic-<UTC time>`. `--skip-threads` runs only the deterministic schedules. `--max-retries` overrides the default (9 on the scripted schedules, 1000 on threads when the flag is omitted).

Artifacts in the output directory:

- `events.jsonl` — raw log, one JSON object per line
- `run.log` — the same events as text
- `tasks.csv` — one row per worker per mode
- `summary.csv` — one row per mode
- `summary.json` — counts, definitions, probe result, and runtime metadata
- `LABEL.txt` — the synthetic-simulation banner
- `workspaces/` — snapshot of the fixture files after the run. This folder is an inspection artifact, not a tenant boundary.

`tasks.csv` columns: `mode`, `scheduler`, `worker_id`, `task_id`, `record_ok`, `integrated`, `useful`, `attempts`, `conflicts`, `retries`, `finished_logical_tick`, `simulation`.

`summary.csv` columns: `mode`, `scheduler`, `workspace_layout`, `workers`, `tasks`, `useful_completed`, `records_correct`, `integrated`, `conflicts`, `retries`, `schedule_rejections`, `logical_ticks`, `schedule_wall_seconds`, `max_retries`, `probe_cross_reads_denied`, `probe_cross_reads_succeeded`, `simulation`.

Every data row has `simulation=synthetic_scripted_workers`.

Exit 0 when the assertions pass, 1 when a fixture result is wrong, 2 when the input or output path is unusable.

## Limits

The deterministic conflict count is a property of this script, not an observation of a fleet. Thread counts move around. Logical ticks are not a speedup. Isolated mode removes shared-counter conflicts by giving up a shared ledger; it does not show that separate workspaces produce more finished work. The memory marker is the string `synthetic-wNN`. Nothing in the fixture is a credential.
