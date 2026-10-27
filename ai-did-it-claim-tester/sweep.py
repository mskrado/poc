"""Threshold sweep: what share of Banking77 tickets a CPU model handles alone vs sends to a person.
TF-IDF + logistic regression (C=30). Thresholds read on validation, reported on test.
  pip install scikit-learn datasets && python sweep.py"""
import random, time
from collections import defaultdict
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union

ds = load_dataset("legacy-datasets/banking77", revision="refs/convert/parquet")
names = ds["train"].features["label"].names
tr = [{"text": r["text"], "label": names[r["label"]]} for r in ds["train"]]
test = [{"text": r["text"], "label": names[r["label"]]} for r in ds["test"]]

# 10% stratified validation split, seed 42 (9,000 train / 1,003 val / 3,080 test)
by = defaultdict(list)
for i, r in enumerate(tr): by[r["label"]].append(i)
rng, val_idx = random.Random(42), set()
for lab in sorted(by):
    idx = by[lab][:]; rng.shuffle(idx); val_idx.update(idx[:max(1, round(len(idx) * 0.10))])
train = [r for i, r in enumerate(tr) if i not in val_idx]
val = [r for i, r in enumerate(tr) if i in val_idx]

clf = make_pipeline(
    make_union(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1),
               TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)),
    LogisticRegression(C=30, max_iter=3000))
t0 = time.perf_counter(); clf.fit([r["text"] for r in train], [r["label"] for r in train])
print(f"train {len(train)} / val {len(val)} / test {len(test)}, trained in {time.perf_counter() - t0:.1f}s")

def score(rows):
    P = clf.predict_proba([r["text"] for r in rows]); k = P.argmax(1)
    return [(clf.classes_[k[i]] == r["label"], P[i, k[i]]) for i, r in enumerate(rows)]

V, T = score(val), score(test)
print("thresh | val acc | model handles | test acc | wrong | to a person")
for t in [round(i * 0.05, 2) for i in range(20)]:
    va = [ok for ok, c in V if c >= t]; ta = [ok for ok, c in T if c >= t]
    print(f"{t:6.2f} | {sum(va)/len(va):7.1%} | {len(ta):5d} ({len(ta)/len(T):5.1%}) | "
          f"{sum(ta)/len(ta):7.1%} | {len(ta)-sum(ta):4d} | {len(T)-len(ta):4d} ({(len(T)-len(ta))/len(T):5.1%})")
