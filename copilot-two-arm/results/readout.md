# copilot-two-arm readout

Runs: 2. Measured change = mean AI wall time / mean no-AI wall time - 1, computed per arm only when both arms have runs. Negative = faster with AI.

| Arm | AI runs (solved) | AI mean wall s | No-AI runs (solved) | No-AI mean wall s | Measured change | AI felt change |
|---|---|---|---|---|---|---|
| Arm A greenfield | 1 (1) | 3.4 | 0 (0) | n/a | n/a | -60.0% |
| Arm B mature fix | 1 (1) | 2.8 | 0 (0) | n/a | n/a | -40.0% |

## Runs

| run | arm | condition | who | tool | wall s | forecast % | felt % | tests | notes |
|---|---|---|---|---|---|---|---|---|---|
| c70a23f5 | A | ai | grokbot-agent | Grok Bot coding agent (box shell) | 3.4 | -50.0 | -60.0 | 12/12 | agent wrote server.py in one pass, no retries |
| 4b52d91a | B | ai | grokbot-agent | Grok Bot coding agent (box shell) | 2.8 | -30.0 | -40.0 | 465/465 | agent seeded this bug itself; contaminated |

Hardware: Intel(R) Xeon(R) Processor, 8 vCPU, 16 GiB RAM, Linux 6.12.94+. Python: 3.13.5.

This is a local measurement. It is not a replication of Peng et al. 2023 or METR 2025.
