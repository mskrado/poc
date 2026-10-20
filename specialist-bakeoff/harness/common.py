"""Shared data loading, prompts and metrics for the Banking77 specialist-vs-frontier bake-off."""
import csv, json, os, random, urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SEED = 42
VAL_FRAC = 0.10
BASE = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/"
FRAUD = ["compromised_card", "card_payment_not_recognised", "lost_or_stolen_card",
         "direct_debit_payment_not_recognised", "cash_withdrawal_not_recognised", "lost_or_stolen_phone"]

def _get(name):
    os.makedirs(DATA, exist_ok=True)
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        urllib.request.urlretrieve(BASE + name, p)
    with open(p, newline="") as f:
        return [{"text": r["text"], "label": r["category"]} for r in csv.DictReader(f)]

def load_splits():
    """train/val carved from the 10,003 train rows (stratified, seeded); test = 3,080 official rows."""
    tr, te = _get("train.csv"), _get("test.csv")
    by = defaultdict(list)
    for i, r in enumerate(tr):
        by[r["label"]].append(i)
    rng = random.Random(SEED); val_idx = set()
    for lab in sorted(by):
        idx = by[lab][:]; rng.shuffle(idx)
        val_idx.update(idx[:max(1, round(len(idx) * VAL_FRAC))])
    train = [r for i, r in enumerate(tr) if i not in val_idx]
    val = [r for i, r in enumerate(tr) if i in val_idx]
    for s, rows in (("train", train), ("val", val), ("test", te)):
        for j, r in enumerate(rows): r["id"] = f"{s}-{j:05d}"
    return train, val, te

def labels():
    return sorted({r["label"] for r in _get("train.csv")})

def system_prefix():
    """Static, cacheable prefix: instructions + all 77 labels. Identical bytes on every call."""
    labs = "\n".join(labels())
    return ("You classify a single online-banking customer message into exactly one intent label.\n"
            "Allowed labels (copy one exactly):\n" + labs + "\n\n"
            'Reply with JSON only: {"label": "<one allowed label>", "confidence": <0..1>}')

def user_msg(text):
    return f"Message: {text}"

# ---------------- metrics ----------------
def f1_per_class(gold, pred):
    tp, fp, fn = Counter(), Counter(), Counter()
    for g, p in zip(gold, pred):
        if g == p: tp[g] += 1
        else: fp[p] += 1; fn[g] += 1
    out = {}
    for c in set(gold):
        pr = tp[c] / (tp[c] + fp[c]) if tp[c] + fp[c] else 0.0
        rc = tp[c] / (tp[c] + fn[c]) if tp[c] + fn[c] else 0.0
        out[c] = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    return out

def pct(xs, q):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)

def calibration(conf, correct, bins=10):
    """Reliability table + expected calibration error (ECE)."""
    rows, ece, n = [], 0.0, len(conf)
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(conf) if (lo <= c < hi) or (b == bins - 1 and c == 1.0)]
        if not idx: rows.append((lo, hi, 0, None, None)); continue
        acc = sum(correct[i] for i in idx) / len(idx); mc = sum(conf[i] for i in idx) / len(idx)
        ece += len(idx) / n * abs(acc - mc); rows.append((lo, hi, len(idx), mc, acc))
    return ece, rows

def threshold_sweep(conf, correct, steps=None):
    """Router: auto-route when top-label prob >= t, else send to a human. Tune on VAL only."""
    steps = steps or [i / 20 for i in range(0, 20)] + [0.97, 0.99]
    out = []
    for t in steps:
        auto = [i for i, c in enumerate(conf) if c >= t]
        acc = sum(correct[i] for i in auto) / len(auto) if auto else None
        out.append({"threshold": t, "auto_routed": len(auto), "to_human": len(conf) - len(auto),
                    "auto_accuracy": acc, "n": len(conf)})
    return out

def summarize(rows):
    """rows: dicts with gold, pred, conf, latency_s (optional)."""
    gold = [r["gold"] for r in rows]; pred = [r["pred"] for r in rows]
    correct = [int(g == p) for g, p in zip(gold, pred)]
    f1 = f1_per_class(gold, pred)
    lat = [r["latency_s"] for r in rows if r.get("latency_s") is not None]
    conf = [r["conf"] for r in rows if r.get("conf") is not None]
    s = {"n": len(rows), "correct": sum(correct), "accuracy": sum(correct) / len(rows),
         "macro_f1": sum(f1.values()) / len(f1),
         "fraud6_macro_f1": sum(f1[c] for c in FRAUD) / len(FRAUD),
         "fraud6_f1": {c: f1[c] for c in FRAUD},
         "p50_latency_s": pct(lat, .5), "p99_latency_s": pct(lat, .99)}
    if len(conf) == len(rows):
        s["ece"], s["reliability"] = calibration(conf, correct)
    return s
