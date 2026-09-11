from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from browser_benchmark import sites, synth_data
from browser_benchmark.config import (
    DEFAULT_SEED,
    load_all_framework_configs,
    load_framework_config,
    load_router_config,
    load_tasks,
    tasks_by_category,
)
from browser_benchmark.orchestrator import compare_frameworks, run_framework, select_tasks
from browser_benchmark.report import (
    CATEGORY_LABELS,
    format_category_matrix,
    format_failure_breakdown,
    format_overall_table,
    format_routed_tasks,
    format_routing_summary,
    write_report,
)
from browser_benchmark.router import route_suite, summarize_routing
from browser_benchmark.scoring import failure_breakdown, summarize_framework


def _config_root(args: argparse.Namespace) -> Path | None:
    return Path(args.config) if args.config else None


def _enabled_frameworks(root: Path | None) -> list[str]:
    """Enabled frameworks, strongest published success rate first."""
    configs = [cfg for cfg in load_all_framework_configs(root).values() if cfg.enabled]
    configs.sort(key=lambda c: c.reference.overall_success_rate, reverse=True)
    return [cfg.name for cfg in configs]


def cmd_list(args: argparse.Namespace) -> int:
    root = _config_root(args)
    if args.tasks:
        grouped = tasks_by_category(load_tasks(root))
        for category, group in grouped.items():
            print(f"{CATEGORY_LABELS[category.value]} ({len(group)})")
            for task in group:
                tags = ", ".join(task.tags)
                print(f"  {task.id:32} [{tags}]")
                print(f"  {'':32} {task.goal}")
            print()
        return 0

    configs = load_all_framework_configs(root)
    for name in sorted(configs, key=lambda n: -configs[n].reference.overall_success_rate):
        cfg = configs[name]
        status = "enabled" if cfg.enabled else "disabled"
        ref = cfg.reference
        print(
            f"  {name:16} [{status}] {cfg.observation:10} "
            f"ref {ref.overall_success_rate * 100:.0f}% success, "
            f"{ref.mean_duration_seconds:.0f}s mean, ${cfg.cost_per_task_usd:.2f}/task"
        )
        print(f"  {'':16} {cfg.description}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    root = _config_root(args)
    tasks = select_tasks(categories=args.categories, task_ids=args.tasks, config_root=root)
    run = asyncio.run(
        run_framework(args.framework, tasks, mode=args.mode, seed=args.seed, config_root=root)
    )
    summary = summarize_framework(run, load_framework_config(args.framework, root))

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_overall_table([summary]))
        print()
        print(format_category_matrix([summary]))
        print()
        print(format_failure_breakdown({args.framework: failure_breakdown(run)}))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    root = _config_root(args)
    names = args.frameworks or _enabled_frameworks(root)
    tasks = select_tasks(categories=args.categories, config_root=root)
    runs = asyncio.run(
        compare_frameworks(names, tasks, mode=args.mode, seed=args.seed, config_root=root)
    )
    summaries = [summarize_framework(run, load_framework_config(run.framework, root)) for run in runs]
    breakdowns = {run.framework: failure_breakdown(run) for run in runs}

    print(format_overall_table(summaries))
    print()
    print(format_category_matrix(summaries))
    if args.failures:
        print()
        print(format_failure_breakdown(breakdowns))

    if args.output:
        payload = {"seed": args.seed, "frameworks": summaries, "failure_modes": breakdowns}
        json_path, md_path = write_report(payload, Path(args.output), prefix="compare")
        print(f"\nWrote {json_path} and {md_path}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    root = _config_root(args)
    tasks = select_tasks(categories=args.categories, config_root=root)
    routed = asyncio.run(route_suite(tasks, mode=args.mode, seed=args.seed, config_root=root))
    summary = summarize_routing(routed, load_router_config(root), root)

    print(format_routing_summary(summary))
    if args.detail:
        print()
        print(format_routed_tasks(routed))

    if args.output:
        payload = {"seed": args.seed, "routing": summary}
        json_path, md_path = write_report(payload, Path(args.output), prefix="route")
        print(f"\nWrote {json_path} and {md_path}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    sites.serve_forever(args.port)
    return 0


def cmd_synth(args: argparse.Namespace) -> int:
    records = synth_data.generate(args.kind, args.rows, seed=args.seed)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(synth_data.to_csv(records), encoding="utf-8")
        print(f"Wrote {len(records)} {args.kind} rows to {path}")
    else:
        print(synth_data.to_csv(records), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="browser-benchmark",
        description="Benchmark browser automation frameworks across 30 real-world workflows.",
    )
    parser.add_argument("--config", help="Path to config directory (default: ./config)")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="List frameworks (or tasks with --tasks)")
    list_p.add_argument("--tasks", action="store_true", help="List the 30 workflows instead")
    list_p.set_defaults(func=cmd_list)

    run_p = sub.add_parser("run", help="Run the suite against one framework")
    run_p.add_argument("--framework", default="playwright_mcp")
    run_p.add_argument("--categories", nargs="+", help="Limit to these categories")
    run_p.add_argument("--tasks", nargs="+", help="Limit to these task ids")
    run_p.add_argument("--mode", choices=["mock", "live"], default="mock")
    run_p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    run_p.add_argument("--json", action="store_true")
    run_p.set_defaults(func=cmd_run)

    cmp_p = sub.add_parser("compare", help="Compare all three frameworks")
    cmp_p.add_argument("--frameworks", nargs="+", help="Default: all enabled")
    cmp_p.add_argument("--categories", nargs="+")
    cmp_p.add_argument("--mode", choices=["mock", "live"], default="mock")
    cmp_p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    cmp_p.add_argument("--failures", action="store_true", help="Include failure-mode breakdown")
    cmp_p.add_argument("--output", help="Report output directory")
    cmp_p.set_defaults(func=cmd_compare)

    route_p = sub.add_parser("route", help="Run the tiered router over the suite")
    route_p.add_argument("--categories", nargs="+")
    route_p.add_argument("--mode", choices=["mock", "live"], default="mock")
    route_p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    route_p.add_argument("--detail", action="store_true", help="Per-task escalation trail")
    route_p.add_argument("--output", help="Report output directory")
    route_p.set_defaults(func=cmd_route)

    serve_p = sub.add_parser("serve", help="Serve the fixture sites locally")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.set_defaults(func=cmd_serve)

    synth_p = sub.add_parser("synth", help="Generate synthetic form data")
    synth_p.add_argument("--kind", choices=list(synth_data.KINDS), default="contacts")
    synth_p.add_argument("--rows", type=int, default=50)
    synth_p.add_argument("--seed", type=int, default=20260101)
    synth_p.add_argument("--output", help="Write CSV here instead of stdout")
    synth_p.set_defaults(func=cmd_synth)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
