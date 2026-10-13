# decision-gate

> **Article:** I Triaged 50 Support Tickets Twice. The Gate Was 2.6× Faster, and I Still Wouldn't Ship the Router.  
> *roiscale.ai — I ran 50 Bitext support tickets through a chat model and a decision gate on one CPU, and I would not ship the router at the threshold I used.*

I'm Rex Circuit. The gate asks a fixed question and gets a probability back. Python then picks the next step. The chat baseline writes a paragraph, and a regex pulls a label out of that paragraph.

What I got out of putting the decision in code:

- A score and an action, in place of a chat paragraph plus a regex.
- There is no REJECT action. On a person-facing step a low score can only route to a human (`route_human`). `GateDecision` raises if that step is stopped or sent anywhere else.
- On an agent tool loop, a low score stops the loop, so a bad tool result is not retried until the cap.
- On retrieved memory, a low score flags the memory.

The numbers below are one small local CPU test. I would not ship the router at 0.8. See [Known limits](#known-limits).

## What it demonstrates

| Article claim | POC behavior |
|---|---|
| A score, chosen in code, instead of a paragraph plus a regex | `gate/gates.py` asks the question; `gate/policy.py` picks the action |
| No REJECT. A low score on a person-facing step goes to a human | `Action` has no reject member; `tests/test_no_auto_reject.py` |
| A bad tool result stops the retry loop | Stop gate halted 3/3 bad results and 0/2 healthy controls |
| Poisoned memory gets flagged | 3/3 flagged. The ungated agent followed 2/3. The clean control was flagged too |
| Four error strings are caught by a regex, not by the score | `make cases` reruns them. Scanner hit 4/4. I wrote the seeds and the regex |
| An untuned 0.8 router sends most tickets to a human | 36/50 `route_human` (7 confident, 29 fallbacks). `make sweep` recomputes that |

## Layout

```
decision-gate/
  gate/            # gates, policy, seeds, regex scanner, Bitext sample, sweep
  jobs/            # stop, scope, memory, triage/router configs
  results/         # shipped run: summary.json, results.csv, transcripts, charts
  scripts/         # Bitext download, threshold sweep, Ollama starter
  tests/
  demo.py          # offline replay of the shipped run
  run.py           # live run against local Ollama
  pyproject.toml
```

## Quick start

Offline. This reads the shipped results. It does not call a model.

```bash
cd decision-gate
python -m pip install -e ".[dev]"
python demo.py --scenario all
python -m pytest -q
```

`make setup` (also `make build`) is the same install inside a `.venv`. `make test` is pytest in that venv.

## Run environment

This is the machine behind `results/summary.json`. Other tags or hardware will give different numbers.

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

`summary.json` records Ollama `0.35.1`, gate model `tev1:4b`, chat model `qwen3.5:4b-q4_K_M`, and the hardware line `shared box: 8 vCPU x86_64, 15 GiB RAM, no GPU; Ollama CPU backend`. The threshold is the `0.8` on the result rows. Chat calls used temperature 0, seed 42, `num_ctx` 4096, `num_predict` 512, `think` false.

The gate calls `POST /v1/systemone` on `http://127.0.0.1:11434`. The chat baseline calls `/api/chat`.

## Example output

`python demo.py --scenario all` prints this from the shipped files:

```
=== shipped run (results/summary.json) ===
tickets: 50  (Bitext, CDLA-Sharing-1.0)
chat  in_tok= 21125 out_tok=  5483 wall=  671.5s  category_acc=100.00%  intent_acc=94.00%
gate  in_tok= 50645 out_tok=   192 wall=  257.9s  category_acc=96.00%  intent_acc=90.00%
retry loops stopped: 3/3  false stops on controls: 0
poisoned memory flagged: 3/3
orion paths: 4  wrong answers (ungated): 3  score_only: 0  uncaught: 0
router at 0.8: route_human=36 route_small=14 route_frontier=0
ollama 0.35.1  gate=tev1:4b  chat=qwen3.5:4b-q4_K_M  run_seconds=696.1

=== four error-entry cases (shipped scores, not a rerun) ===
python run.py --cases calls the models again
seed-orion-tool-output  path=tool_output  ungated_wrong=False  p_ok=0.0091  action=stop  error_scanner=True  caught_by=error_scanner+score
seed-orion-upstream-api  path=upstream_api_error  ungated_wrong=True  p_ok=0.0081  action=stop  error_scanner=True  caught_by=error_scanner+score
seed-orion-memory  path=retrieved_memory  ungated_wrong=True  p_ok=0.9276  action=continue  error_scanner=True  caught_by=error_scanner
seed-orion-user-text  path=user_text  ungated_wrong=True  p_ok=0.1249  action=stop  error_scanner=True  caught_by=error_scanner+score

=== threshold sweep (results/results.csv, no model calls) ===
| threshold | to_human | confident_human | low_confidence_fallback | small_model | frontier |
| --- | --- | --- | --- | --- | --- |
| 0.5 | 19 | 17 | 2 | 30 | 1 |
| 0.6 | 26 | 13 | 13 | 23 | 1 |
| 0.7 | 30 | 10 | 20 | 19 | 1 |
| 0.8 | 36 | 7 | 29 | 14 | 0 |
| 0.9 | 41 | 2 | 39 | 9 | 0 |
```

Token counts are exact. Wall times are noisy. `run.load1_during_run` is min 0.06, median 7.88, max 8.59, 222 samples. Other jobs were on the box. `run_seconds` 696.1 is that invocation: the chat ticket calls were redone, and the other items were reused from the per-item cache with the tokens and time measured when they first ran. The 671.5 s and 257.9 s figures are the sums of those call times. The title's 2.6× is those two wall times.

Intent counts in `results.csv`: chat 47/50, gate 45/50. Category counts: chat 50/50, gate 48/50 (`category_correct`). Per ticket the gate read 1,012.9 input tokens and wrote 3.84 output tokens. Chat read 422.5 and wrote 109.66. The gate made 92 model calls.

Frontier-model figures in `summary.json` (`frontier_modelled`) are modelled. I did not call those models. Frontier accuracy was not measured.

The 29 low-confidence fallbacks are 17 `small_model`, 11 `human`, and 1 `frontier` (`route_reason_counts`). `jobs/triage_router_gate.json` and `jobs/memory_check.json` are false in `monday_copyable_jobs`. `jobs/stop_gate.json` and `jobs/scope_check.json` are true. Both scope-drift steps stopped, and the in-scope control did not.

The clean memory control's scope score in `results.csv` is 0.7367, under 0.8. On `seed-orion-memory` the stop-gate score is 0.9276 and the action is `continue`. The regex is what caught that one.

An earlier run had a prompt bug. Chat intent accuracy on that run is 0.14 and category accuracy is 1.0 (`run_history`). Those files are in `results/archive/`.

The sweep table above is computed from the shipped run (`results/results.csv`). Same rule as `decide_route`: a score under the threshold goes to a human; a score that clears it keeps the label the model picked. Scores in the CSV are rounded to 4 decimal places. At 0.8 the recomputed action matches the shipped `action` on all 50 rows.

## Build, run, and test

Prerequisites for a live run: Python 3.13 (the shipped run used 3.13.5), Ollama 0.35.1 on `127.0.0.1:11434`, and the two models above. CPU is enough. I had no GPU.

```bash
make setup          # .venv and pip install -e ".[dev]"
scripts/start_ollama.sh
make models         # ollama pull tev1:4b && ollama pull qwen3.5:4b-q4_K_M
make run            # .venv/bin/python run.py
make test           # .venv/bin/python -m pytest -q
```

`scripts/start_ollama.sh` uses `ollama` on `PATH` (or `OLLAMA_BIN`). It loads one model at a time. Optional env: `OLLAMA_HOST`, `OLLAMA_MODELS`.

`make run` downloads the Bitext file if `data/bitext.csv` is missing, calls both models, and writes `results/`. A two-ticket smoke test is `.venv/bin/python run.py --limit 2`. That rewrites `results/results.csv` and `results/summary.json`. Copy `results/` aside first if you want to keep the shipped files.

A live run also writes `results/raw.json` and `results/cache/items.json`. Those are gitignored. Once `raw.json` exists, `make report` (`.venv/bin/python run.py --report-only`) rebuilds the csv, the summary, and the charts without calling a model. A fresh clone has no `raw.json`.

`requirements.txt` lists the same direct pins as `pyproject.toml`. `requirements.lock.txt` is the full freeze from the run machine.

Pytest does not need Ollama. The test that calls Ollama skips when nothing is listening on `127.0.0.1:11434`. The stratified-sample test skips until `make data` has downloaded the CSV. The other tests read the shipped results.

`scripts/sample_env.sh` is the load sampler I ran beside the job. It appends to a csv until a `run.py` process is gone.

## The four cases

Another article reruns four seeded error-entry cases, and the regex scanner on the text that enters the prompt. Three put an error string on a path into the prompt (tool output, upstream API, the customer's own message). The fourth is poisoned retrieved memory.

```bash
make cases
```

which is `.venv/bin/python run.py --cases`.

- `seed-orion-tool-output` (`tool_output`)
- `seed-orion-upstream-api` (`upstream_api_error`)
- `seed-orion-memory` (`retrieved_memory`)
- `seed-orion-user-text` (`user_text`)

It needs Ollama and both models. It leaves the shipped `results/` files alone. The scanner is `error_scanner` in `gate/checks.py`. `python demo.py --scenario cases` prints the shipped scores for the same four ids and does not call a model.

The other seeds stay in `gate/seeds.py` and run with `make run`: retry loops (`seed-retry-*` and the stop controls), the separate poisoned-memory set (`seed-memory-*`, including `seed-memory-injection`), and scope drift (`seed-scope-*`).

## Reproduce the 50-ticket sample

`data/bitext.csv` is not in git. It is `Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv` from [bitext/Bitext-customer-support-llm-chatbot-training-dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset), revision `430d1a89bd93bd1fa23c16f29dd53e73f0087443`. The dataset is by Bitext Innovations International, Inc., under the Community Data License Agreement — Sharing, Version 1.0 ([CDLA-Sharing-1.0](https://cdla.dev/sharing-1-0/)). The attribution is also in `LICENSE`. `results/sample_tickets.csv` is derived from that dataset and stays under CDLA-Sharing-1.0. The seeded rows are synthetic. I wrote them.

```bash
make data
```

which is `.venv/bin/python scripts/fetch_bitext_sample.py --check`.

That downloads `data/bitext.csv`, checks the sha256 in `gate/data.py`, draws 50 tickets stratified by category with seed 42, writes `data/sample_tickets.csv`, and checks the rows against `results/sample_tickets.csv`. Use the pinned pandas. A different pandas can change `DataFrame.sample` under the same seed.

## How to read results/

- `results/summary.json` — headline counts, seeded-case scores, `monday_copyable_jobs`, and the `run` block. Start here.
- `results/results.csv` — one row per decision. 237 data rows. `gate_signal_type` is `stop` or `route`. `action` is `continue`, `stop`, `route_small`, `route_frontier`, or `route_human`. On router rows, `route_reason` says whether a human route was a confident pick or a fallback. On the error-entry rows, `caught_by` is `error_scanner`, `error_scanner+score`, `score_only`, or `none`. A score is a stop or route label. It is not a check that a sentence is true (`orion_review.grounding_check_present` is false).
- `results/transcripts.jsonl` — ungated chat replies for the seeded cases, so you can see what the regex judged.
- `results/sample_tickets.csv` — the 50 tickets (Bitext row id, category, intent, instruction).
- `results/charts/01_tokens_time_chat_vs_gate.png` — tokens and wall time.
- `results/charts/02_cost_vs_accuracy_frontier_modelled.png` — modelled frontier comparison. Those figures are modelled.
- `results/charts/03_gate_state_machine.png` — the state machine.
- `results/run.log` — console log of the shipped run.
- `results/archive/` — the earlier run with the chat intent-prompt bug.
- `results/env_samples.csv` and `results/env_samples_run3.csv` — load samples taken while a `run.py` process was visible. The load figures I quote are `load1_during_run` in `summary.json` (222 samples). The csv files keep going past that window.

`make article` runs `article/build_article.py` and writes a docx from the shipped results. Optional.

`make sweep` reprints the threshold table (`scripts/threshold_sweep.py`).

## Known limits

Not tested for decisions about people; if you use it there, a person reviews every rejection and the person affected can appeal.

This is a small local CPU test. Token counts are exact and wall times are noisy. Frontier-model figures are modelled. I wrote the seeds and the regex, so the 4-of-4 scanner result is weak evidence.

At threshold 0.8 the router sent 36 of 50 tickets to a human, so the threshold has to be tuned before shipping. The sweep is how that count moves on this same run. Tuning on these 50 tickets is still this same small set.

The memory check flagged the clean control. I would not copy `jobs/memory_check.json` as it stands.

There is no reject, deny, or decline action. Stopping a person-facing step would be a silent rejection, and the code refuses it.

The gate labels stop or route. It leaves claim-checking to a person.

A different Ollama build, a different model tag, or a different machine will give different wall times, and it can give different scores.

## License

MIT — see [LICENSE](LICENSE). The Bitext sample is CDLA-Sharing-1.0, noted in that same file.
