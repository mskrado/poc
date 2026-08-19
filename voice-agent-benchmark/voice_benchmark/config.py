from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Any

import yaml

from voice_benchmark.models import PatientRecord, StackConfig, StackReference

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), match.group(0))

        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return _expand_env(data)


def config_root(start: Path | None = None) -> Path:
    if start is not None:
        return start
    return Path(__file__).resolve().parent.parent / "config"


def load_scenario(root: Path | None = None) -> dict[str, Any]:
    return load_yaml(config_root(root) / "scenario.yaml")


def load_patient_list(root: Path | None = None) -> list[PatientRecord]:
    path = config_root(root) / "patient_list.csv"
    patients: list[PatientRecord] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            patients.append(
                PatientRecord(
                    name=row["name"],
                    phone=row["phone"],
                    persona=row["persona"],
                    appointment=row["appointment"],
                )
            )
    return patients


def load_stack_config(name: str, root: Path | None = None) -> StackConfig:
    path = config_root(root) / "stacks" / f"{name}.yaml"
    raw = load_yaml(path)
    ref_raw = raw.get("reference")
    reference = None
    if ref_raw:
        reference = StackReference(
            p95_turn_latency_ms=float(ref_raw["p95_turn_latency_ms"]),
            cost_per_minute=float(ref_raw["cost_per_minute"]),
            error_rate=float(ref_raw["error_rate"]),
        )
    return StackConfig(
        stack=str(raw.get("stack", name)),
        enabled=bool(raw.get("enabled", True)),
        description=str(raw.get("description", "")),
        raw=raw,
        reference=reference,
        concurrency=int(raw.get("concurrency", 10)),
    )


def list_stack_names(root: Path | None = None) -> list[str]:
    stacks_dir = config_root(root) / "stacks"
    return sorted(p.stem for p in stacks_dir.glob("*.yaml"))


def load_all_stack_configs(root: Path | None = None) -> dict[str, StackConfig]:
    return {name: load_stack_config(name, root) for name in list_stack_names(root)}
