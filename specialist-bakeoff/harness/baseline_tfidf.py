"""Sanity BASELINE (not one of the two arms): TF-IDF + logistic regression on CPU.
C tuned on val; test touched once.   python baseline_tfidf.py
"""
import json, platform, os, time
import numpy as np, sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union
from common import HERE, load_splits, summarize, threshold_sweep
from results_io import append, dump_preds, run_id

def hw():
    n = os.cpu_count()
    model, mem_s = "CPU", ""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    break
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    mem_s = f", {int(line.split()[1]) / 1048576:.0f} GiB RAM"
                    break
    except OSError:
        pass
    return f"CPU only: {n} vCPU {model}{mem_s}"

def build(C):
    feats = make_union(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1),
                       TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2))
    return make_pipeline(feats, LogisticRegression(C=C, max_iter=3000))

def score(clf, rows):
    t0 = time.perf_counter(); P = clf.predict_proba([r["text"] for r in rows]); dt = time.perf_counter() - t0
    cls = clf.classes_; k = P.argmax(1)
    # batch prediction: per-ticket latency = batch wall time / n (noted as amortised, not per-request)
    return [dict(id=r["id"], gold=r["label"], pred=cls[k[i]], conf=float(P[i, k[i]]), latency_s=dt / len(rows))
            for i, r in enumerate(rows)]

def main():
    train, val, test = load_splits()
    X, y = [r["text"] for r in train], [r["label"] for r in train]
    best = None; grid = {}
    for C in [1, 3, 10, 30, 100]:
        clf = build(C).fit(X, y); s = summarize(score(clf, val)); grid[C] = s["accuracy"]
        if best is None or s["accuracy"] > best[1]: best = (C, s["accuracy"], clf)
    C, _, clf = best
    t0 = time.perf_counter(); clf = build(C).fit(X, y); train_s = time.perf_counter() - t0
    vrows = score(clf, val); vs = summarize(vrows)
    sweep = threshold_sweep([r["conf"] for r in vrows], [int(r["gold"] == r["pred"]) for r in vrows])
    # router threshold: lowest t whose auto-routed val accuracy >= 0.95
    thr = next((s["threshold"] for s in sweep if s["auto_accuracy"] and s["auto_accuracy"] >= 0.95), None)
    trows = score(clf, test); ts = summarize(trows)  # test touched once
    auto = sum(r["conf"] >= thr for r in trows) if thr is not None else None
    vers = f"python {platform.python_version()}, scikit-learn {sklearn.__version__}, numpy {np.__version__}"
    for split, s, rows in (("val", vs, vrows), ("test", ts, trows)):
        dump_preds(f"baseline-{split}-preds.jsonl", rows)
        append(dict(run_id=run_id("baseline-tfidf-lr", split), arm="baseline-tfidf-lr", status="measured", split=split,
                    conf_source="predict_proba", router_threshold=thr if split == "test" else "",
                    auto_routed=auto if split == "test" else "", to_human=(len(trows) - auto) if split == "test" and auto is not None else "",
                    hardware=hw(), versions=vers, seed=42, cost_per_1k_full_usd=0,
                    **{k: v for k, v in s.items() if not isinstance(v, (dict, list))}))
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "baseline-summary.json"), "w") as f:
        json.dump({"C_grid_val_acc": grid, "C": C, "train_seconds": train_s, "router_threshold": thr,
                   "val_sweep": sweep, "val": vs, "test": ts}, f, indent=1, default=str)
    print(json.dumps({"C": C, "grid": grid, "train_s": round(train_s, 1), "thr": thr, "test_auto": auto,
                      "hw": hw(), "val": {k: v for k, v in vs.items() if k != "reliability"},
                      "test": {k: v for k, v in ts.items() if k != "reliability"}}, indent=1, default=str))

if __name__ == "__main__": main()
