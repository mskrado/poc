"""Command line for the synthetic contention harness."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .banner import BANNER, ISOLATION_LIMIT, RELEASE, PACKET
from .report import verify_suite, write_artifacts
from .schedule import run_suite
from .tasks import default_fixture_path, load_fixture


def prepare_out(path: Path) -> Path:
    path = path.resolve()
    kit = Path(__file__).resolve().parent.parent
    if path == Path(path.anchor) or path == kit or path == kit.parent:
        raise ValueError(f"refusing output path {path}")
    if path.is_symlink():
        raise ValueError(f"refusing symlink output path {path}")
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"output path is not a directory: {path}")
        # Replace only this run directory. Callers pass a dedicated folder.
        for child in path.iterdir():
            raise ValueError(f"output directory is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_out() -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return Path("out") / f"synthetic-{stamp}"


def format_table(results) -> str:
    header = f"{'mode':<28} {'useful':>7} {'conflicts':>9} {'retries':>8} {'logical_ticks':>14} {'wall_s':>12}"
    lines = [header]
    for result in results:
        ticks = "n/a" if result.logical_ticks is None else str(result.logical_ticks)
        lines.append(
            f"{result.mode:<28} {result.useful:>7} {result.conflicts:>9} {result.retries:>8} "
            f"{ticks:>14} {result.schedule_wall_seconds:>12.6f}"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Synthetic contention simulation: serial vs concurrent scripted workers."
    )
    parser.add_argument("--fixture", default=str(default_fixture_path()), help="synthetic tasks.json")
    parser.add_argument("--out", default=None, help="empty directory for CSV, JSONL, and logs")
    parser.add_argument("--max-retries", type=int, default=None, help="default: n-1 for the script, 1000 for OS threads")
    parser.add_argument("--skip-threads", action="store_true", help="run only the deterministic schedules")
    args = parser.parse_args(argv)
    print(BANNER)
    print(ISOLATION_LIMIT)
    print(f"release {RELEASE}  packet {PACKET}")
    try:
        tasks = load_fixture(args.fixture)
        out = prepare_out(Path(args.out) if args.out else default_out())
        results = run_suite(tasks, max_retries=args.max_retries, threads=not args.skip_threads)
        errors = verify_suite(results)
        write_artifacts(out, results, errors)
    except (ValueError, OSError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2
    print(format_table(results))
    print("logical_ticks are the scripted schedule clock. They are not a speedup result.")
    denied = results[0].probe.get("cross_reads_denied")
    leaked = results[0].probe.get("cross_reads_succeeded")
    print(f"scoped-memory probe (per deterministic mode): cross reads denied {denied}, succeeded {leaked}.")
    print(f"artifacts: {out}")
    if errors:
        print(f"assertions: FAIL ({len(errors)})", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("assertions: PASS")
    return 0
