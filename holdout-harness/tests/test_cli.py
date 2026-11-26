import csv

from holdout_harness.cli import main


def test_cli_writes_labelled_results(tmp_path, capsys):
    assert main(["run", "--out", str(tmp_path), "--boot", "300"]) == 0
    rows = list(csv.DictReader(open(tmp_path / "results.csv")))
    assert len(rows) == 7
    assert all(r["label"] == "synthetic test data" for r in rows)
    summary = (tmp_path / "summary.md").read_text()
    assert "synthetic test data" in summary


def test_holdout_beats_pre_post_and_guards_fire(tmp_path):
    main(["run", "--out", str(tmp_path), "--boot", "300"])
    rows = {(r["design"], r["estimator"]): r for r in csv.DictReader(open(tmp_path / "results.csv"))}
    pp = rows[("split-route (market-hashed)", "naive pre/post, treated routes only")]
    cup = rows[("split-route (market-hashed)", "holdout + CUPED (log revenue), Welch 95% CI")]
    leaky = rows[("split-route (route-hashed, leaky)", "holdout on test/pre ratio, bootstrap 95% CI")]
    assert float(pp["rel_lift"]) > 0.10            # carries the synthetic fare move
    assert float(cup["ci_low"]) <= 0.02 <= float(cup["ci_high"])
    assert pp["flags"] == "mixed_markets=0"
    assert leaky["flags"] != "mixed_markets=0"
    assert float(leaky["rel_lift"]) > float(cup["rel_lift"])


def test_cli_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    main(["run", "--out", str(a), "--boot", "200"])
    main(["run", "--out", str(b), "--boot", "200"])
    assert (a / "results.csv").read_text() == (b / "results.csv").read_text()
