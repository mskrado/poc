"""Run the six checks on the stores in stores.csv.
  python run_stores.py discover        # find one product + one category page per store -> targets.json
  python run_stores.py run 1           # run 1 -> appends rows to results.csv
  python run_stores.py run 2           # run 2, same frozen URLs
  python run_stores.py compare         # confirmed.csv: a result counts only if both runs agree
"""
import csv
import json
import sys
from pathlib import Path

from rexcat.discover import discover
from rexcat.fetch import PoliteSession
from rexcat.run import CHECK_COLUMNS, run_store

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
FIELDS = ["run", "store", "group", "product_url", "category_url"] + CHECK_COLUMNS + ["schema_shipping", "timestamp_utc", "notes"]


def stores():
    with open(HERE / "stores.csv") as f:
        return list(csv.DictReader(f))


def cmd_discover():
    sess, targets = PoliteSession(), {}
    for s in stores():
        d = discover(sess, s["home_url"])
        targets[s["store"]] = d
        print(s["store"], d)
    (OUT / "targets.json").write_text(json.dumps(targets, indent=1))
    (OUT / "discover-log.json").write_text(json.dumps(sess.log, indent=1))


def cmd_run(n):
    targets = json.loads((OUT / "targets.json").read_text())
    sess = PoliteSession()
    path = OUT / "results.csv"
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for s in stores():
            t = targets[s["store"]]
            row = run_store(sess, s["home_url"], t["product_url"], t["category_url"])
            row.update({"run": n, "store": s["store"], "group": s["group"]})
            w.writerow(row)
            f.flush()
            print(n, s["store"], [row[c] for c in CHECK_COLUMNS])
    (OUT / f"run{n}-log.json").write_text(json.dumps(sess.log, indent=1))


def cmd_compare():
    rows = list(csv.DictReader(open(OUT / "results.csv")))
    by = {}
    for r in rows:
        by.setdefault(r["store"], {})[r["run"]] = r
    with open(OUT / "confirmed.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["store", "group", "check", "run1", "run2", "confirmed"])
        for store, runs in by.items():
            a, b = runs["1"], runs["2"]
            for c in CHECK_COLUMNS + ["schema_shipping"]:
                conf = a[c] if a[c] == b[c] else "changed"
                w.writerow([store, a["group"], c, a[c], b[c], conf])


if __name__ == "__main__":
    {"discover": lambda: cmd_discover(), "run": lambda: cmd_run(sys.argv[2]),
     "compare": lambda: cmd_compare()}[sys.argv[1]]()
