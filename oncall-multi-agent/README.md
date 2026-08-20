# oncall-multi-agent

> **Article:** [I Replaced My Whole On-Call Rotation With a Multi-Agent System. Here Is What I Got Right and What I Got Wrong.](https://roiscale.ai/sites/roiscale/articles/cb684b24-c407-471f-bacd-0fe607a68b1b/i-replaced-my-whole-on-call-rotation-with-a-multi-agent-system-here-is-what-i)  
> *roiscale.ai — a LangGraph-style multi-agent on-call responder wired to PagerDuty, Datadog, and runbooks that auto-resolves ~31% of incidents, with severity gates and a sandbox that prevented a near-`rm -rf`-prod moment.*

This POC implements the architecture decisions from the article as a **runnable, dependency-free** simulation:

1. Explicit state graph (`diagnose → execute_runbook → resolve | escalate`)
2. **Severity gate** — SEV1 / SEV2 always page a human after gathering context
3. **Sandboxed runbook execution** — explicit command allowlist (no raw shell)
4. **Destructive-action classifier** — `restart` / `delete` / `drop` / `terminate` / `kill` need human confirm
5. **Reasoning traces** posted as Slack-style context packs on every outcome
6. **Historical incident harness** — the eval layer the author wished they'd built on day one

No real PagerDuty, Datadog, or Docker access. Tools are mocked; the safety controls are real.

## What it demonstrates

| Article claim | POC behavior |
|---|---|
| SEV1/SEV2 never auto-resolve | Severity gate escalates after diagnose |
| Sandbox saved prod | `restart postgresql-primary` is not allowlisted → escalate |
| Destructive classifier | Allowlisted `systemctl restart …` still needs human confirm |
| Reasoning trace ≥ resolution | Every run emits a Slack-style thread with the full trace |
| Evals from day one | `fixtures/incidents.json` + harness checks routing |

## Layout

```
oncall-multi-agent/
  oncall_agent/       # graph, sandbox, tools, harness
  fixtures/           # historical incidents for replay evals
  demo.py
  tests/
```

## Quick start

```bash
cd oncall-multi-agent
python -m pip install -e ".[dev]"
python demo.py --scenario all
python -m pytest -q
```

## Example output

**Disk full (SEV3)** — auto-resolved via allowlisted, non-destructive cleanup:

```
outcome: resolved
runbook: disk-full-cleanup
Slack: [AUTO-RESOLVED] … reasoning trace …
```

**SEV1 outage** — context gathered, human paged immediately:

```
outcome: escalated
paged_human: True
trace includes: SEV1 always pages a human (severity gate)
```

**Stuck migration (near-disaster)** — sandbox blocks the bad command:

```
outcome: escalated
sandbox_blocks: ["Command not on allowlist: 'restart postgresql-primary'"]
```

**Historical harness:**

```
pass_rate: 100% (6/6)
```

## State diagram

```
PagerDuty webhook (simulated fixture)
        │
        ▼
   [diagnose] ── metrics + logs + incident metadata
        │
        ├── severity ≤ 2 ──────────────────► [escalate] ──► Slack context pack
        │
        ▼
  runbook search (keyword stand-in for vector RAG)
        │
        ├── no confident match ────────────► [escalate]
        │
        ▼
 [execute_runbook] ── each step through sandbox
        │
        ├── blocked / destructive ─────────► [escalate]
        │
        ▼
    evaluate metrics
        │
        ├── recovered ──► [resolve] ──► Slack
        └── not recovered ──► [escalate]
```

## License

MIT — see [LICENSE](LICENSE).
