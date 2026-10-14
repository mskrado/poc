# decision-gate

I'm Rex Circuit. This folder is the harness I ran on support-ticket work: a decision gate beside a normal chat model.

The gate asks a fixed question and gets a probability back. Python then picks the next step. The chat baseline does what a lot of harnesses do: it writes a paragraph, and a regex pulls a label out of that paragraph.

What I got out of putting the decision in code:

- A score and an action, in place of a chat paragraph plus a regex.
- There is no REJECT action. On a person-facing step a low score can only route to a human (`route_human`). `GateDecision` raises if that step is stopped or sent anywhere else. When the action is `route_human`, `defer_reason` says why, for example `low_confidence: top=small_model p=0.69 < 0.8`. A confident human pick is `model_choice: top=human p=0.95 >= 0.8`. Every other action leaves `defer_reason` as `None`. Logging that reason is an idea from Noah Solace (roiscale.ai).
- On an agent tool loop, a low score stops the loop. A bad tool result does not get retried until the cap.
- On retrieved memory, a low score flags the memory.

The numbers below are one small local CPU test. I would not ship the router at the threshold I used. See [Known limits](#known-limits).

## Run environment

This is the machine and the toolchain behind `results/summary.json`. Other tags or hardware will give different numbers.

| | |
|---|---|
| Ollama | 0.35.1 |
| Gate model | `tev1:4b` (Q8_0) |
| Chat model | `qwen3.5:4b-q4_K_M` |
| Routing threshold | 0.8 on every gate, not tuned |
| OS | Debian 13 |
| CPU | 8 vCPU |
| RAM | 15 GiB |
| GPU | none |
| Python | 3.13.5 |

`summary.json` records Ollama `0.35.1`, gate model `tev1:4b`, chat model `qwen3.5:4b-q4_K_M`, and the hardware line `shared box: 8 vCPU x86_64, 15 GiB RAM, no GPU; Ollama CPU backend`. The threshold is the `0.8` stored on the result rows and in `assumptions.threshold`. Chat calls used temperature 0, seed 42, `num_ctx` 4096, `num_predict` 512, `think` false (`run.chat_options`).

The gate calls `POST /v1/systemone` on `http://127.0.0.1:11434`. The chat baseline calls `/api/chat` with `stream` false.

## What the shipped run measured

50 Bitext tickets, stratified by category, seed 42 (`summary.json` → `data`). Plus the synthetic seeds in `gate/seeds.py`.

From `results/summary.json`, with intent counts taken from the `intent_correct` column in `results.csv`:

| | Chat | Gate |
|---|---|---|
| Input tokens | 21,125 | 50,645 |
| Output tokens | 5,483 | 192 |
| Wall time | 671.5 s | 257.9 s |
| Category | 50/50 (100%) | 48/50 (96%) |
| Intent | 47/50 (94%) | 45/50 (90%) |

The gate made 92 model calls on the tickets. Per ticket it read 1,012.9 input tokens and wrote 3.84 output tokens. Chat read 422.5 and wrote 109.66. Those per-ticket figures are `input_tokens_per_ticket` and `output_tokens_per_ticket` in `summary.json`.

Token counts are exact. Wall times are noisy. `run.load1_during_run` is min 0.06, median 7.88, max 8.59, 222 samples. Other jobs were on the box. `run.run_seconds` is 696.1 for that invocation: chat ticket calls were redone, and the other items were reused from the per-item cache with the tokens and time measured when they first ran. The 671.5 s and 257.9 s figures are the sums of those call times.

Frontier-model figures in `summary.json` (`frontier_modelled`) are modelled. I did not call those models. The field says frontier accuracy was not measured.

Seeded cases, same file:

- Retry loops: the stop gate stopped 3 of 3 bad tool results. False stops on the 2 healthy controls: 0.
- Poisoned memory (`seed-memory-*`): flagged 3 of 3. The ungated chat agent followed 2 of 3. The clean control was also flagged (`memory_control_falsely_flagged` is true). Its scope score in `results.csv` is 0.7367, under 0.8.
- Scope: both drift steps stopped, and the in-scope control did not (`summary.json` → `scope`).
- Router at 0.8: `route_human` 36, `route_small` 14, and 0 to frontier. Of the 36, 7 are confident `human` picks (`model_choice:human`) and 29 are low-confidence fallbacks (17 `small_model`, 11 `human`, 1 `frontier` in `route_reason_counts`). Most of the 50 tickets went to a human. The threshold has to be tuned before shipping. `jobs/triage_router_gate.json` is false in `monday_copyable_jobs`. `jobs/memory_check.json` is false too. `jobs/stop_gate.json` and `jobs/scope_check.json` are true.
- Four error-entry paths: the regex scanner hit 4 of 4 (`orion_review.caught_by_non_score_detector`). `score_only` is 0 and `uncaught` is 0. Ungated wrong answers: 3. I wrote the seeds and the regex, so 4 of 4 is weak evidence. On `seed-orion-memory` the stop-gate score in `results.csv` is 0.9276 and the action is `continue`. The regex is what caught that one (`caught_by` is `error_scanner`).

An earlier run had a prompt bug. Chat intent accuracy on that run is 0.14 and category accuracy is 1.0 (`run_history`). The files are under `results/archive/`. The table above is the fixed run.

## Prerequisites

- Python 3.13. The shipped run used 3.13.5.
- Ollama 0.35.1, listening on `127.0.0.1:11434`. The gate needs `/v1/systemone` from that line of Ollama.
- Models `tev1:4b` (Q8_0) and `qwen3.5:4b-q4_K_M`.
- CPU is enough. I had no GPU.
- `make` is optional. Each target below is also a Python command.

## Setup and build

From this directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`requirements.txt` is the direct pins. `requirements.lock.txt` is the full freeze from the run machine. Same step via make:

```bash
make setup
```

`make build` is that same target.

Start Ollama and pull the models:

```bash
scripts/start_ollama.sh
make models
```

`make models` is `ollama pull tev1:4b && ollama pull qwen3.5:4b-q4_K_M`. `scripts/start_ollama.sh` uses `ollama` on `PATH` (or `OLLAMA_BIN`). It loads one model at a time (`OLLAMA_MAX_LOADED_MODELS=1`). Optional env: `OLLAMA_HOST`, `OLLAMA_MODELS`.

## Run

Full run. This downloads the Bitext file if `data/bitext.csv` is missing, calls both models, and writes `results/`:

```bash
make run
```

which is `.venv/bin/python run.py`.

Two-ticket smoke test, still calls the models:

```bash
.venv/bin/python run.py --limit 2
```

`--limit` rewrites `results/results.csv` and `results/summary.json`. Copy `results/` aside first if you want to keep the shipped files.

A live run also writes `results/raw.json` and `results/cache/items.json`. Those are gitignored. Once `results/raw.json` exists:

```bash
make report
```

which is `.venv/bin/python run.py --report-only`. That rebuilds the csv, the summary, and the charts without calling a model. A fresh clone has no `raw.json`, so this target waits until you have run the models once.

`scripts/sample_env.sh` is the load sampler I ran beside the job. It appends to a csv until a `run.py` process is gone:

```bash
scripts/sample_env.sh results/env_samples.csv
```

## The four cases

Another article reruns four seeded error-entry cases, and the regex scanner on the text that enters the prompt. I kept the seeds. Three of them put an error string on a path into the prompt (tool output, upstream API, the customer's own message). The fourth is poisoned retrieved memory.

```bash
make cases
```

which is `.venv/bin/python run.py --cases`.

That command reruns only these four ids:

- `seed-orion-tool-output` (`tool_output`)
- `seed-orion-upstream-api` (`upstream_api_error`)
- `seed-orion-memory` (`retrieved_memory`)
- `seed-orion-user-text` (`user_text`)

It needs Ollama and both models. It does not download Bitext, and it leaves the shipped `results/` files alone. The scanner is `error_scanner` in `gate/checks.py`.

The other seeds stay in `gate/seeds.py` and run with `make run`: retry loops (`seed-retry-*` and the stop controls), the separate poisoned-memory set (`seed-memory-*`, including `seed-memory-injection`), and scope drift (`seed-scope-*`).

## Reproduce the 50-ticket sample

`data/bitext.csv` is not in git. It is the Bitext file `Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv` from the Hugging Face dataset [bitext/Bitext-customer-support-llm-chatbot-training-dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset), revision `430d1a89bd93bd1fa23c16f29dd53e73f0087443`. The dataset is by Bitext Innovations International, Inc., licensed under the Community Data License Agreement — Sharing, Version 1.0 ([CDLA-Sharing-1.0](https://cdla.dev/sharing-1-0/)). Attribution and the pinned revision are also in `LICENSE`. `results/sample_tickets.csv` is derived from that dataset and stays under CDLA-Sharing-1.0. The seeded rows are synthetic. I wrote them.

```bash
make data
```

which is `.venv/bin/python scripts/fetch_bitext_sample.py --check`.

That downloads `data/bitext.csv`, checks the sha256 in `gate/data.py`, draws 50 tickets stratified across the 11 categories with seed 42, writes `data/sample_tickets.csv`, and checks the rows against `results/sample_tickets.csv`. Use the pinned pandas. A different pandas can change `DataFrame.sample` under the same seed.

## Test

```bash
make test
```

which is `.venv/bin/python -m pytest -q`.

Ollama does not have to be running. The test that calls Ollama skips when nothing is listening on `127.0.0.1:11434`. The stratified-sample test skips when `data/bitext.csv` is absent (run `make data` if you want that one to execute). The results tests read the shipped `results/results.csv` and `results/summary.json`.

## Threshold sweep

`results.csv` stores `predicted_label` and `score` on each of the 50 `router_gate` rows. This recomputes how many of those tickets route to a human at 0.5, 0.6, 0.7, 0.8, and 0.9. It does not call a model.

```bash
make sweep
```

which is `.venv/bin/python scripts/threshold_sweep.py`.

The rule is `decide_route` in `gate/policy.py`. If the score is below the threshold, the ticket goes to a human (low-confidence fallback). If the score clears the threshold, the ticket goes to the label the model picked (`small_model`, `frontier`, or `human`). Scores in the CSV are rounded to 4 decimal places. At 0.8 the recomputed action matches the shipped `action` on all 50 rows.

This table is computed from the shipped run (`results/results.csv`):

| threshold | to_human | confident_human | low_confidence_fallback | small_model | frontier |
| --- | --- | --- | --- | --- | --- |
| 0.5 | 19 | 17 | 2 | 30 | 1 |
| 0.6 | 26 | 13 | 13 | 23 | 1 |
| 0.7 | 30 | 10 | 20 | 19 | 1 |
| 0.8 | 36 | 7 | 29 | 14 | 0 |
| 0.9 | 41 | 2 | 39 | 9 | 0 |

The 0.8 row matches `summary.json`: 36 to a human, 7 confident human picks, 29 fallbacks, 14 to the small model, 0 to frontier.

## How to read results/

- `results/summary.json` — headline counts, seeded-case scores, `monday_copyable_jobs`, and the `run` block. Start here.
- `results/results.csv` — one row per decision. 237 data rows. `gate_signal_type` is `stop` or `route`. `action` is `continue`, `stop`, `route_small`, `route_frontier`, or `route_human`. On router rows, `route_reason` says whether a human route was a confident pick or a fallback. On the error-entry rows, `caught_by` is `error_scanner`, `error_scanner+score`, `score_only`, or `none`. A score is a stop or route label. It is not a check that a sentence is true (`orion_review.grounding_check_present` is false). `defer_reason` is on the `GateDecision` object, not a new column in this file.
- `results/transcripts.jsonl` — ungated chat replies for the seeded cases, so you can see what the regex judged.
- `results/sample_tickets.csv` — the 50 tickets (Bitext row id, category, intent, instruction).
- `results/charts/01_tokens_time_chat_vs_gate.png` — tokens and wall time, from the summary.
- `results/charts/02_cost_vs_accuracy_frontier_modelled.png` — modelled frontier comparison. Those figures are modelled.
- `results/charts/03_gate_state_machine.png` — the state machine.
- `results/run.log` — console log of the shipped run.
- `results/archive/` — the earlier run with the chat intent-prompt bug (`run_history`).
- `results/env_samples.csv` and `results/env_samples_run3.csv` — load and free-memory samples taken while a `run.py` process was visible. The load figures I quote are `load1_during_run` in `summary.json` (222 samples). The csv files keep going past that window.

## Known limits

Not tested for decisions about people; if you use it there, a person reviews every rejection and the person affected can appeal.

This is a small local CPU test. Token counts are exact and wall times are noisy. Frontier-model figures are modelled. I wrote the seeds and the regex, so the 4-of-4 scanner result is weak evidence.

At threshold 0.8 the router sent 36 of 50 tickets to a human, so the threshold has to be tuned before shipping. The sweep above is how that count moves on this same run. Tuning on these 50 tickets is still this same small set.

The memory check flagged the clean control. I would not copy `jobs/memory_check.json` as it stands.

There is no reject, deny, or decline action. Stopping a person-facing step would be a silent rejection, and the code refuses it.

The gate does not check whether a claim in an answer is true.

A different Ollama build, a different model tag, or a different machine will give different wall times, and it can give different scores.

## Layout

- `gate/types.py` — `GateDecision`, including `defer_reason`.
- `gate/gates.py` — stop, scope, memory, triage, intent.
- `gate/policy.py` — turns a score into an action.
- `gate/checks.py` — the regex error scanner and the chat-prose parsers.
- `gate/seeds.py` — synthetic rows, including the four error-entry cases and the poisoned-memory seeds.
- `gate/data.py` — Bitext download, sha256, and the stratified sample.
- `gate/client.py` — Ollama HTTP. Host from `OLLAMA_HOST_URL`, default `http://127.0.0.1:11434`.
- `gate/sweep.py` — the threshold sweep.
- `jobs/*.json` — the four job configs. `run.py` is the runner.
- `scripts/fetch_bitext_sample.py` — download and sample check.
- `scripts/threshold_sweep.py` — print the sweep table.
- `article/build_article.py` — `make article` writes a docx from the shipped results. Optional.

## License

Code is MIT. The Bitext sample is CDLA-Sharing-1.0. Both are in `LICENSE`.
