from oncall_agent.sandbox import RunbookSandbox, classify_destructive


class TestDestructiveClassifier:
    def test_flags_restart_and_kill(self):
        hits = classify_destructive("restart postgresql-primary")
        assert "restart" in hits

    def test_clean_command_has_no_flags(self):
        assert classify_destructive("df -h") == []


class TestSandbox:
    def test_allowlisted_command_runs(self):
        sb = RunbookSandbox()
        result = sb.execute("df -h")
        assert result.allowed

    def test_blocks_postgresql_primary_restart(self):
        """The article near-miss: restart postgresql-primary is not allowlisted."""
        sb = RunbookSandbox()
        result = sb.execute("restart postgresql-primary")
        assert not result.allowed
        assert "allowlist" in result.reason.lower()

    def test_destructive_allowlisted_needs_human(self):
        sb = RunbookSandbox(human_confirmed=False)
        result = sb.execute("systemctl restart app-worker")
        assert not result.allowed
        assert result.requires_human_confirm

    def test_destructive_allowlisted_with_human_confirm(self):
        sb = RunbookSandbox(human_confirmed=True)
        result = sb.execute("systemctl restart app-worker")
        assert result.allowed

    def test_non_destructive_flush_runs_without_human(self):
        sb = RunbookSandbox(human_confirmed=False)
        result = sb.execute("redis-cli FLUSHDB")
        assert result.allowed
