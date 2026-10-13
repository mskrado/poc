#!/usr/bin/env python3
"""One command: python run.py

Needs a local Ollama >= 0.35 with the two models pulled (see README).
--limit N      smoke-test on the first N sampled tickets
--report-only  rebuild results/charts from results/raw.json without calling models
--cases        rerun only the 4 error-entry cases and the regex scanner
"""
from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gate import harness, report, seeds  # noqa: E402
from gate.data import ensure_dataset, intents_by_category, sample_tickets  # noqa: E402
from gate.types import GateDecision  # noqa: E402


def _display(path: Path) -> str:
    """Prefer a path relative to the project so logs are not machine-specific."""
    resolved = path.resolve()
    for base in (ROOT, Path.cwd()):
        try:
            return str(resolved.relative_to(base.resolve()))
        except ValueError:
            continue
    return resolved.name


def to_jsonable(o):
    if isinstance(o, GateDecision):
        d = dataclasses.asdict(o)
        return {k: (v.value if isinstance(v, enum.Enum) else v) for k, v in d.items()}
    if isinstance(o, dict):
        return {k: to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, enum.Enum):
        return o.value
    return o


def print_cases(chat_out, gate_out, secs: float):
    print("\n=== four error-entry cases ===")
    print("polluted paths + poisoned retrieved memory, plus the regex scanner")
    print(f"wall_s={secs:.1f}  (this rerun only; results/ is left as shipped)")
    for p in seeds.ORION_PATHS:
        c = chat_out[p["id"]]
        g = gate_out[p["id"]]
        d = g["stop"]
        print(f"{p['id']}  path={p['path']}  ungated_wrong={c['wrong']}  "
              f"p_ok={d.score:.4f}  action={d.action.value}  error_scanner={g['scanner']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--cases", action="store_true",
                    help="rerun only the 4 error-entry cases (polluted paths, poisoned memory) and the regex scanner")
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()
    if a.cases and a.report_only:
        ap.error("--cases reruns the models; it does not use --report-only")
    out = Path(a.out)

    if a.cases:
        try:
            harness.client.version()
        except Exception as e:
            print(f"Ollama is not reachable ({harness.client.HOST}): {e}", file=sys.stderr)
            print("Start it with scripts/start_ollama.sh and pull the models (make models).", file=sys.stderr)
            return 1
        chat_out, gate_out, secs = harness.run_cases()
        print_cases(chat_out, gate_out, secs)
        return 0

    out.mkdir(parents=True, exist_ok=True)

    data = ensure_dataset(ROOT / "data" / "bitext.csv")
    tickets = sample_tickets(data)
    if a.limit:
        tickets = tickets.head(a.limit)
    by_cat = intents_by_category(data)
    all_intents = sorted({i for v in by_cat.values() for i in v})
    tickets.to_csv(out / "sample_tickets.csv", index=False)

    if not a.report_only:
        (out / "cache").mkdir(exist_ok=True)
        harness.Cache.open(out / "cache" / "items.json")
        chat_out, gate_out, secs = harness.run_all(tickets, all_intents, by_cat)
        raw = {"chat": to_jsonable(chat_out), "gate": to_jsonable(gate_out),
               "meta": {"run_seconds": round(secs, 1), "chat_model": harness.CHAT_MODEL,
                        "gate_model": harness.GATE_MODEL, "ollama_version": harness.client.version(),
                        "gate_path": "ollama /v1/systemone (decision model)"}}
        (out / "raw.json").write_text(json.dumps(raw, indent=1))
    raw = json.loads((out / "raw.json").read_text())

    rows, summary = report.build(raw, tickets.to_dict("records"))
    summary["run"] = raw["meta"]
    summary["run"]["hardware"] = "shared box: 8 vCPU x86_64, 15 GiB RAM, no GPU; Ollama CPU backend"
    summary["run"]["chat_options"] = {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 512, "think": False}
    arch = out / "archive" / "run1-summary.json"
    if arch.exists():
        r1 = json.loads(arch.read_text())
        summary["run_history"] = {
            "run1_bug": "chat prompt did not list the intent labels, so the chat model invented intent names "
                        "(e.g. 'Inquiry about early exit penalty fees'); parser found no label in most answers",
            "run1_chat_intent_accuracy": r1["chat"]["intent_accuracy"],
            "run1_chat_category_accuracy": r1["chat"]["category_accuracy"],
            "run1_files": "results/archive/run1-summary.json, run1-results.csv, run1.log",
            "fix": "chat prompt now lists each category's intents; chat ticket calls re-run, all other items reused "
                   "from the per-item cache (results/cache/items.json) with the tokens/time measured when they ran",
            "earlier_crash": "a previous attempt lost its llama runner (HTTP 500 EOF) at gate ticket 26 on the shared box; "
                             "that attempt wrote no results; the per-item cache + retry was added after it",
        }
    envs = sorted(out.glob("env_samples*.csv"))
    if envs:
        import csv as _csv
        loads = [float(r["load1"]) for f in envs for r in _csv.DictReader(open(f)) if r.get("load1")]
        if loads:
            summary["run"]["load1_during_run"] = {"min": min(loads), "max": max(loads),
                                                  "median": sorted(loads)[len(loads) // 2], "samples": len(loads),
                                                  "note": "other agents share this box; wall times are noisy, token counts are not"}
    report.write(rows, summary, out)
    with open(out / "transcripts.jsonl", "w") as f:
        for kind in ("loops", "memory", "orion"):
            for k, v in raw["chat"][kind].items():
                f.write(json.dumps({"id": k, "kind": kind, "ungated_chat_output": v}) + "\n")

    from gate import charts
    charts.make_all(summary, rows, out / "charts")

    s = summary
    print("\n=== decision-gate results ===")
    print(f"tickets: {s['tickets']}  (Bitext, CDLA-Sharing-1.0)")
    for m in ("chat", "gate"):
        print(f"{m:5s} in_tok={s[m]['input_tokens']:>6} out_tok={s[m]['output_tokens']:>6} "
              f"wall={s[m]['wall_s']:>7}s  category_acc={s[m]['category_accuracy']:.2%}  intent_acc={s[m]['intent_accuracy']:.2%}")
    print(f"retry loops stopped: {s['retry_loops_stopped']}/{s['retry_loops_total']}  "
          f"false stops on controls: {s['stop_gate_false_stops_on_controls']}")
    print(f"poisoned memory flagged: {s['poisoned_memory_flagged']}/{s['poisoned_memory_total']}")
    o = s["orion_review"]
    print(f"orion paths: {o['paths']}  wrong answers (ungated): {o['wrong_answers_ungated']}  "
          f"score_only: {o['score_only']}  uncaught: {o['uncaught']}")
    print(f"frontier (MODELLED) all-tickets USD: {s['frontier_modelled']['all_tickets_to_frontier_usd']}")
    print(f"wrote {_display(out / 'results.csv')} and {_display(out / 'summary.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
