#!/usr/bin/env python3
"""Replay the shipped decision-gate run. No Ollama and no dataset download."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from gate.sweep import DEFAULT_THRESHOLDS, sweep_router

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def _summary() -> dict:
    return json.loads((RESULTS / "summary.json").read_text())


def _rows() -> list[dict]:
    with (RESULTS / "results.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def show_summary(summary: dict) -> None:
    chat, gate = summary["chat"], summary["gate"]
    print("=== shipped run (results/summary.json) ===")
    print(f"tickets: {summary['tickets']}  (Bitext, CDLA-Sharing-1.0)")
    for name, block in (("chat", chat), ("gate", gate)):
        print(
            f"{name:5s} in_tok={block['input_tokens']:>6} out_tok={block['output_tokens']:>6} "
            f"wall={block['wall_s']:>7}s  category_acc={block['category_accuracy']:.2%}  "
            f"intent_acc={block['intent_accuracy']:.2%}"
        )
    print(
        f"retry loops stopped: {summary['retry_loops_stopped']}/{summary['retry_loops_total']}  "
        f"false stops on controls: {summary['stop_gate_false_stops_on_controls']}"
    )
    print(f"poisoned memory flagged: {summary['poisoned_memory_flagged']}/{summary['poisoned_memory_total']}")
    review = summary["orion_review"]
    print(
        f"orion paths: {review['paths']}  wrong answers (ungated): {review['wrong_answers_ungated']}  "
        f"score_only: {review['score_only']}  uncaught: {review['uncaught']}"
    )
    actions = gate["route_action_counts"]
    print(
        f"router at 0.8: route_human={actions.get('route_human', 0)} "
        f"route_small={actions.get('route_small', 0)} "
        f"route_frontier={actions.get('route_frontier', 0)}"
    )
    run = summary["run"]
    print(
        f"ollama {run['ollama_version']}  gate={run['gate_model']}  chat={run['chat_model']}  "
        f"run_seconds={run['run_seconds']}"
    )


def show_cases(summary: dict) -> None:
    print("=== four error-entry cases (shipped scores, not a rerun) ===")
    print("python run.py --cases calls the models again")
    for case_id, row in summary["orion_error_paths"].items():
        print(
            f"{case_id}  path={row['path']}  ungated_wrong={row['answer_wrong']}  "
            f"p_ok={row['p_ok']:.4f}  action={row['stop_gate_action']}  "
            f"error_scanner={row['error_scanner_hit']}  caught_by={row['caught_by']}"
        )


def show_sweep(rows: list[dict]) -> None:
    print("=== threshold sweep (results/results.csv, no model calls) ===")
    print("| threshold | to_human | confident_human | low_confidence_fallback | small_model | frontier |")
    print("| --- | --- | --- | --- | --- | --- |")
    for row in sweep_router(rows, DEFAULT_THRESHOLDS):
        print(
            f"| {row['threshold']:.1f} | {row['route_human']} | {row['confident_human']} | "
            f"{row['low_confidence_fallback']} | {row['route_small']} | {row['route_frontier']} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=["summary", "cases", "sweep", "all"],
        default="all",
    )
    args = parser.parse_args()
    summary = _summary()
    rows = _rows()
    steps = ["summary", "cases", "sweep"] if args.scenario == "all" else [args.scenario]
    for index, step in enumerate(steps):
        if index:
            print()
        {"summary": lambda: show_summary(summary), "cases": lambda: show_cases(summary), "sweep": lambda: show_sweep(rows)}[step]()


if __name__ == "__main__":
    main()
