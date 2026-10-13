"""Bitext sample: 50 tickets stratified across the 11 categories, fixed seed."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import requests

BITEXT_REV = "430d1a89bd93bd1fa23c16f29dd53e73f0087443"
BITEXT_FILE = "Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv"
BITEXT_URL = (f"https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/"
              f"resolve/{BITEXT_REV}/{BITEXT_FILE}")
BITEXT_SHA256 = "6f81102b0100b97b8468eb04368033a23206bf1fde9d53500d5806ec1001a434"
SEED = 42
N_TICKETS = 50

# Short descriptions, built from each category's own intent names. The chat
# baseline and the gate get exactly the same text.
CATEGORIES = {
    "ACCOUNT": "Create, delete, edit or switch an account; recover a password; registration problems.",
    "CANCEL": "Questions about cancellation fees.",
    "CONTACT": "Wants to reach customer service or a human agent.",
    "DELIVERY": "Delivery options and how long delivery takes.",
    "FEEDBACK": "Complaints or reviews about the service.",
    "INVOICE": "Check or get an invoice.",
    "ORDER": "Place, change, cancel or track an order.",
    "PAYMENT": "Payment methods or a problem with a payment.",
    "REFUND": "Refund policy, getting a refund, or tracking a refund.",
    "SHIPPING": "Set up or change a shipping address.",
    "SUBSCRIPTION": "Newsletter subscription.",
}


def ensure_dataset(path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(BITEXT_URL, timeout=300, headers={"User-Agent": "decision-gate-sample/1.0"})
        r.raise_for_status()
        path.write_bytes(r.content)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != BITEXT_SHA256:
        raise RuntimeError(f"Bitext file hash mismatch: {digest}")
    return path


def allocation(counts: pd.Series, n: int) -> dict[str, int]:
    """Every category gets floor(n/k); the remainder goes by largest-remainder
    proportional share, so big categories get the extra tickets."""
    k = len(counts)
    base = {c: n // k for c in counts.index}
    left = n - sum(base.values())
    share = counts / counts.sum() * n
    order = list(counts.sort_values(ascending=False).index)  # deterministic tie-break
    ranked = sorted(counts.index, key=lambda c: (-share[c], order.index(c)))
    for c in ranked[:left]:
        base[c] += 1
    return base


def sample_tickets(path: Path, n: int = N_TICKETS, seed: int = SEED) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.reset_index().rename(columns={"index": "row"})
    alloc = allocation(df["category"].value_counts(), n)
    parts = [df[df.category == c].sample(k, random_state=seed) for c, k in sorted(alloc.items())]
    out = pd.concat(parts).reset_index(drop=True)
    out["ticket_id"] = "bitext-" + out["row"].astype(str)
    return out[["ticket_id", "row", "category", "intent", "instruction", "flags"]]


def intents_by_category(path: Path) -> dict[str, list[str]]:
    df = pd.read_csv(path)
    return {c: sorted(g.intent.unique()) for c, g in df.groupby("category")}
