from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from voice_benchmark.config import config_root, list_stack_names, load_all_stack_configs
from voice_benchmark.orchestrator import compare_stacks, run_benchmark
from voice_benchmark.report import format_comparison_table, summarize_run, write_report


def _default_config_root() -> Path:
    return config_root()


def cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.config) if args.config else _default_config_root().parent / "config"
    if args.config:
        root = Path(args.config)

    result = asyncio.run(
        run_benchmark(
            args.stack,
            calls=args.calls,
            mode=args.mode,
            config_root=root,
            concurrency=args.concurrency,
        )
    )
    summary = summarize_run(result, root)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_comparison_table([summary]))

    if args.output:
        out = Path(args.output)
        write_report([summary], out, prefix=f"{args.stack}-{args.mode}")
        print(f"\nWrote report to {out}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    root = Path(args.config) if args.config else _default_config_root().parent / "config"
    all_stacks = load_all_stack_configs(root)
    names = args.stacks or [n for n, c in all_stacks.items() if c.enabled and n != "mock"]

    results = asyncio.run(
        compare_stacks(names, calls=args.calls, mode=args.mode, config_root=root)
    )
    summaries = [summarize_run(r, root) for r in results]

    print(format_comparison_table(summaries))
    if args.output:
        out = Path(args.output)
        json_path, md_path = write_report(summaries, out, prefix="compare")
        print(f"\nWrote {json_path} and {md_path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = Path(args.config) if args.config else _default_config_root().parent / "config"
    for name in list_stack_names(root):
        cfg = load_all_stack_configs(root)[name]
        status = "enabled" if cfg.enabled else "disabled"
        ref = cfg.reference
        ref_note = ""
        if ref:
            ref_note = f" (ref p95={ref.p95_turn_latency_ms}ms, ${ref.cost_per_minute}/min)"
        print(f"  {name:16} [{status}]{ref_note} — {cfg.description}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voice-benchmark",
        description="Benchmark voice agent stacks: latency, cost, reliability.",
    )
    parser.add_argument(
        "--config",
        help="Path to config directory (default: ./config)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run benchmark for one stack")
    run_p.add_argument("--stack", default="mock", help="Stack name (default: mock)")
    run_p.add_argument("--calls", type=int, default=5, help="Number of calls to simulate")
    run_p.add_argument(
        "--mode",
        choices=["mock", "live"],
        default="mock",
        help="mock = dry-run simulator; live = real API adapters (requires keys)",
    )
    run_p.add_argument("--concurrency", type=int, default=None)
    run_p.add_argument("--output", help="Report output directory")
    run_p.add_argument("--json", action="store_true", help="Print JSON summary")
    run_p.set_defaults(func=cmd_run)

    cmp_p = sub.add_parser("compare", help="Compare multiple stacks")
    cmp_p.add_argument(
        "--stacks",
        nargs="+",
        help="Stack names (default: all enabled except mock)",
    )
    cmp_p.add_argument("--calls", type=int, default=5)
    cmp_p.add_argument("--mode", choices=["mock", "live"], default="mock")
    cmp_p.add_argument("--output", default="reports", help="Report output directory")
    cmp_p.set_defaults(func=cmd_compare)

    list_p = sub.add_parser("list", help="List configured stacks")
    list_p.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
