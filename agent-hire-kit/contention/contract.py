"""Independent specification of the scripted schedule.

The concurrent numbers are a property of the barrier rule below, not a
measurement of agents or people. Keep this file free of the scheduler so a
test can catch the two drifting apart.
"""

from __future__ import annotations


def contract_serial(n: int) -> dict:
    return {
        "useful": n,
        "conflicts": 0,
        "retries": 0,
        "logical_ticks": 5 * n,
        "owners": [f"w{i:02d}" for i in range(1, n + 1)],
    }


def contract_isolated(n: int) -> dict:
    return {
        "useful": n,
        "conflicts": 0,
        "retries": 0,
        "logical_ticks": 5,
        "per_ledger_total": 1,
    }


def contract_concurrent_shared(n: int, max_retries: int) -> dict:
    """Barrier schedule.

    All remaining workers read the same counter version. The lowest worker id
    commits. Each other worker records one conflict. A worker integrates only
    after that many failures, and only while failures stay within max_retries.
    The logical clock charges 4 ticks for the overlapped private prefix
    (read record, transform, write record, first shared read), then 1 tick per
    compare-and-swap wave and 1 tick for each later shared re-read.
    """
    if n < 1:
        raise ValueError("n must be positive")
    if max_retries < 0:
        raise ValueError("max_retries must be nonnegative")
    failures = [0] * n
    integrated = [False] * n
    conflicts = 0
    retries = 0
    ticks = 4
    first_wave = True
    while True:
        pending = [i for i in range(n) if not integrated[i] and failures[i] <= max_retries]
        if not pending:
            break
        if not first_wave:
            ticks += 1
        first_wave = False
        ticks += 1
        integrated[pending[0]] = True
        for i in pending[1:]:
            failures[i] += 1
            conflicts += 1
            if failures[i] <= max_retries:
                retries += 1
    owners = [f"w{i + 1:02d}" for i, ok in enumerate(integrated) if ok]
    return {
        "useful": len(owners),
        "conflicts": conflicts,
        "retries": retries,
        "logical_ticks": ticks,
        "owners": owners,
    }
