import csv, json, os, time
from common import HERE
COLS = ["run_id","arm","status","split","n","correct","accuracy","macro_f1","fraud6_macro_f1",
        "p50_latency_s","p99_latency_s","ece","conf_source","router_threshold","auto_routed","to_human",
        "input_tokens","cache_write_tokens","cache_read_tokens","output_tokens","train_gpu_h","serve_gpu_h",
        "gpu_usd_per_h","labelling_usd","cost_per_1k_full_usd","cost_per_1k_cached_usd","hardware","versions","seed"]
RES = os.path.join(HERE, "results.csv")

def append(row):
    """Write one scoreboard row. A rerun replaces the previous row for the same arm and split."""
    rows = []
    if os.path.exists(RES):
        with open(RES, newline="") as f:
            rows = list(csv.DictReader(f))
    rows = [r for r in rows if not (r.get("arm") == row.get("arm") and r.get("split") == str(row.get("split")))]
    rows.append({k: row.get(k, "") for k in COLS})
    with open(RES, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def dump_preds(name, rows):
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", name), "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")

def run_id(arm, split): return f"{arm}-{split}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
