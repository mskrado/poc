from oncall_agent.harness import default_fixtures_path, load_fixtures, run_harness


def test_historical_harness_all_pass():
    fixtures = load_fixtures(default_fixtures_path())
    # Default: destructive verbs require human confirm (article rule).
    # Auto-resolve fixtures use non-destructive allowlisted steps only.
    report = run_harness(fixtures, human_confirmed_destructive=False)
    assert report.failed == 0, [(c.incident_id, c.expected, c.actual) for c in report.cases if not c.passed]
    assert report.pass_rate == 1.0


def test_fixtures_cover_near_disaster():
    fixtures = load_fixtures(default_fixtures_path())
    migration = next(f for f in fixtures if f.incident_id == "PD-1004")
    assert "postgresql" in migration.notes.lower() or "near-disaster" in migration.notes.lower()
