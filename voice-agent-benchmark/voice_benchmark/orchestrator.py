from __future__ import annotations

import asyncio
from pathlib import Path

from voice_benchmark.config import load_patient_list, load_scenario, load_stack_config
from voice_benchmark.metrics.latency import enrich_call_record
from voice_benchmark.models import StackRunResult
from voice_benchmark.stacks.registry import get_adapter


async def run_benchmark(
    stack_name: str,
    *,
    calls: int | None = None,
    mode: str = "mock",
    config_root: Path | None = None,
    concurrency: int | None = None,
) -> StackRunResult:
    scenario = load_scenario(config_root)
    patients = load_patient_list(config_root)
    stack_config = load_stack_config(stack_name, config_root)

    if not stack_config.enabled:
        raise ValueError(f"Stack '{stack_name}' is disabled in config")

    adapter = get_adapter(stack_config, mode=mode, scenario=scenario)
    target_calls = calls if calls is not None else len(patients)
    limit = concurrency or stack_config.concurrency
    sem = asyncio.Semaphore(limit)

    async def one_call(index: int):
        patient = patients[index % len(patients)]
        async with sem:
            record = await adapter.place_call(patient, index)
            return enrich_call_record(record)

    tasks = [one_call(i) for i in range(target_calls)]
    results = await asyncio.gather(*tasks)
    return StackRunResult(stack=stack_name, calls=list(results))


async def compare_stacks(
    stack_names: list[str],
    *,
    calls: int = 5,
    mode: str = "mock",
    config_root: Path | None = None,
) -> list[StackRunResult]:
    runs: list[StackRunResult] = []
    for name in stack_names:
        runs.append(
            await run_benchmark(name, calls=calls, mode=mode, config_root=config_root)
        )
    return runs
