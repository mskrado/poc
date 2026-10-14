"""Self-check: prove the harness grades correctly before anyone times a run.

Arm A: empty workspace fails, reference server passes 12/12.
Arm B: seeded tree fails, reverse-applied seed passes.
Writes results/selfcheck.csv. These rows are tooling checks, never a no-AI baseline.
"""
import csv, shutil, subprocess, tempfile
from pathlib import Path
from twoarm import arms

ROOT = Path(__file__).parent


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        a = arms.prepare("A", Path(tmp) / "a")
        rows.append(("A", "empty", *arms.grade("A", a)))
        shutil.copy(ROOT / "tasks/arm_a_greenfield/reference/server.py", a / "server.py")
        rows.append(("A", "reference", *arms.grade("A", a)))
        b = arms.prepare("B", Path(tmp) / "b")
        rows.append(("B", "seeded", *arms.grade("B", b)))
        subprocess.run(["git", "apply", "-R", "-p1", str(ROOT / "tasks/arm_b_mature/seed_bug.patch")], cwd=b, check=True)
        rows.append(("B", "seed reverted", *arms.grade("B", b)))
    out = ROOT / "results/selfcheck.csv"; out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["arm", "workspace", "passed", "total"]); w.writerows(rows)
    for r in rows:
        print(f"Arm {r[0]:<2} {r[1]:<14} {r[2]}/{r[3]}")


if __name__ == "__main__":
    main()
