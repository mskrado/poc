# voice-agent-benchmark

> **Article:** [I Benchmarked the 2026 Voice Agent Stack: Vapi vs Retell vs Pipecat vs Roll-Your-Own](https://roiscale.ai/sites/roiscale/articles/89233950-d237-4024-be85-4556f8eb0d20/i-benchmarked-the-2026-voice-agent-stack-vapi-vs-retell-vs-pipecat-vs-roll-your)  
> *roiscale.ai — Rex runs 1,000 outbound calls per stack on an appointment-confirmation scenario and publishes latency, cost, and error-rate comparisons across Vapi, Retell, Pipecat, and a Twilio + OpenAI Realtime roll-your-own path.*

This POC is an **open, config-driven benchmark harness** for reproducing and extending that methodology. It includes:

- A **SynthCaller** simulated patient (rule-based by default; swap in GPT-4o-mini for live runs)
- **Stack adapters** for Vapi, Retell, Pipecat, and OpenAI Realtime
- Unified **turn event schema** (end-of-user-speech → first assistant audio byte)
- **Latency, cost, and error-rate** aggregation with article reference values baked into config
- **Dry-run mode** — no API keys required for local demos and CI

## What it demonstrates

| Article element | POC behavior |
|---|---|
| Appointment confirmation scenario | `config/scenario.yaml` + `config/patient_list.csv` |
| 1,000 calls per stack | `voice-benchmark run --calls 1000` (mock or live) |
| p95 turn latency | `metrics/latency.py` — VAD end → first audio byte |
| Cost per minute | Configurable rate cards in `config/stacks/*.yaml` |
| SynthCaller patient simulator | `synth_caller/patient_agent.py` with persona scripts |
| Webhook instrumentation | `voice_benchmark/webhook/server.py` (optional FastAPI listener) |
| Article reference numbers | `reference:` block in each stack config for side-by-side comparison |

## Layout

```
voice-agent-benchmark/
  config/
    scenario.yaml           # shared prompt + personas
    patient_list.csv        # synthetic patient roster
    stacks/                 # per-stack config + pricing + reference metrics
  voice_benchmark/
    cli.py                  # `voice-benchmark` CLI
    orchestrator.py         # batch runner
    synth_caller/           # simulated callee
    stacks/                 # adapter plugins (mock + live stubs)
    metrics/                # latency, cost, event normalization
    webhook/                # turn-event listener for live runs
  demo.py                   # article-style comparison demo
  tests/
```

## Quick start

```bash
cd voice-agent-benchmark
python -m pip install -e ".[dev]"
python demo.py --scenario compare --calls 5
python -m pytest -q
```

## CLI

```bash
# List configured stacks (with article reference values)
voice-benchmark list

# Dry-run one stack
voice-benchmark run --stack mock --calls 10

# Compare all four article stacks (mock mode, no API keys)
voice-benchmark compare --calls 5 --output reports/

# Live mode (requires credentials in env — see config/stacks/*.yaml)
voice-benchmark run --stack vapi --mode live --calls 1
```

## Configuration

Each stack is a YAML file under `config/stacks/`. Secrets use `${ENV_VAR}` placeholders:

| Stack | Key env vars |
|---|---|
| `vapi` | `VAPI_ASSISTANT_ID`, `VAPI_PHONE_NUMBER_ID` |
| `retell` | `RETELL_AGENT_ID`, `RETELL_FROM_NUMBER` |
| `pipecat` | Self-hosted — wire your Daily/Pipecat pipeline |
| `openai_realtime` | `TWILIO_FROM_NUMBER` + OpenAI Realtime credentials |
| `mock` | None — dry-run simulator |

Edit `config/scenario.yaml` to change the system prompt, personas, and turn-detection defaults. Edit pricing blocks to match your plan.

## Example output

```
Stack            | p95 latency | $/min | error rate | calls
vapi             | 312ms       | $0.14 | 0.0%       | 5
retell           | 358ms       | $0.31 | 0.0%       | 5
pipecat          | 521ms       | $0.07 | 0.0%       | 5
openai_realtime  | 445ms       | $0.19 | 0.0%       | 5
```

Mock-mode numbers are **simulated** around each stack's article reference profile — use live mode with real webhooks for production measurements.

## Webhook server (live runs)

```bash
pip install -e ".[live]"
docker compose up webhook
# Point Vapi/Retell webhooks at http://your-host:8080/webhook/{call_id}
```

## Extending

1. Add a stack config: `config/stacks/my_stack.yaml`
2. Implement `StackAdapter.place_call()` in `voice_benchmark/stacks/`
3. Register in `voice_benchmark/stacks/registry.py`
4. Add webhook normalization in `metrics/events.py` if needed

## Article reference values (from config)

| Stack | Ref p95 | Ref $/min | Ref error rate |
|---|---|---|---|
| Vapi | 380ms | $0.14 | 3.1% |
| Retell | 420ms | $0.31 | 1.2% |
| Pipecat | 610ms | $0.07 | 4.4% |
| OpenAI Realtime (tuned) | 520ms | $0.19 | 3.9% |

## License

MIT — see [LICENSE](LICENSE).
