# agent-fsm

> **Article:** [Agents Are State Machines. Your Framework Is Lying to You.](https://roiscale.ai/sites/roiscale/articles/b90b3e8f-c4e6-4542-9f27-573d8c720e5a/agents-are-state-machines-your-framework-is-lying-to-you)  
> *roiscale.ai — argues that agent frameworks hide a finite-state-machine core, and that explicit FSM design produces cheaper, debuggable, predictably-failing agents.*

This POC implements and demonstrates the article's central claim: every "reasoning agent" is really a **finite state machine** driven by probabilistic token generation. Frameworks that obscure this mental model lead to ghost states, runaway loops, and expensive confusion. This code makes the FSM explicit and contrasts it with a naive framework-style loop.

## What it demonstrates

| Article claim | POC behavior |
|---|---|
| Explicit transition table | `TRANSITIONS` whitelist; invalid moves raise `InvalidTransitionError` |
| Hard turn ceiling | `max_turns=8` forces `ESCALATING` |
| Retry limit | `VALIDATING → EXTRACTING` capped at 2 retries |
| State-scoped tools | Each state receives only the tools it needs |
| Ghost state detection | Skipping `VALIDATING` → `ERROR`, not silent re-prompt |
| Human-readable audit | `summarize_for_reviewer()` for escalation queues |
| Framework-style failures | `NaiveReasoningAgent` burns tokens on ghost outputs |

## Layout

```
agent-fsm/
  agent_fsm/          # Explicit FSM orchestrator (~200 lines)
  agent_naive/        # Comparison naive loop
  demo.py             # Runnable scenarios
  tests/              # pytest suite
```

## Quick start

```bash
cd agent-fsm
python -m pip install -e ".[dev]"
python demo.py --scenario all
python -m pytest -q
```

## Example output

**Happy path** — linear progression with scoped tools:

```
INIT → EXTRACTING → VALIDATING → ROUTING → DONE (4 turns)
Tools at EXTRACTING: ('extract_fields',) — not the full catalog
```

**Ghost state** — invalid skip blocked immediately:

```
EXTRACTING → ROUTING raises InvalidTransitionError → ERROR
Reviewer summary explains the blocked transition
```

**Naive loop** — same document, 12 steps, ~22k simulated tokens, never finishes:

```
Step 4-6: unparseable output — re-prompting silently
Step 7+: keeps looping with full tool list every step
```

## State diagram

```
[INIT] ──────────────────────────────► [ERROR]
  │                                        ▲
  ▼                                        │
[EXTRACTING] ──────────────────────────────┤
  │                                        │
  ▼                                        │
[VALIDATING] ── retry (≤2) ──► [EXTRACTING]
  │
  ▼
[ROUTING] ──► [DONE]
  │
  └── low confidence ──► [ESCALATING] ──► [DONE]
```

## Production checklist (from the article)

- [x] Every transition logged with trigger and model output
- [x] `max_turns` tested — ceiling routes to `ESCALATING`
- [x] Tool list scoped per state
- [x] `TRANSITIONS` table unit-tested
- [x] `ERROR` state observable in demo output
- [x] Retry counter with explicit limit

Standalone reference implementation — no framework dependencies. Lift patterns into production orchestration code or compare against LangGraph-style explicit graphs.

## License

MIT — see [LICENSE](LICENSE).
