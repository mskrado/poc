# specialist-bakeoff

A harness for Banking77 intent classification. It scores a CPU baseline you can rerun, and it has two further arms — a Qwen3.5-9B LoRA model and Claude Opus 4.5 zero-shot — that were **not run**. Those arms need a GPU and an Anthropic API key you supply. This repo has no accuracy, latency, or cost for them.

## What it measures

One label out of 77 banking intents for a customer message.

| Arm | What | Confidence | Status |
|---|---|---|---|
| Baseline | TF-IDF (word 1–2 grams and character 2–5 grams) plus logistic regression, on CPU | `predict_proba` | Measured. See below. |
| Qwen | `Qwen/Qwen3.5-9B` LoRA SFT (r=16, alpha=32, all-linear, 2 epochs, learning rate 2e-4, bf16, TRL `SFTTrainer` + PEFT). The score is a softmax over 77 label log-likelihoods | `softmax` | **Not run.** Needs your GPU. |
| Opus | `claude-opus-4-5-20251101`, zero-shot, temperature 0, the same 77-label system prefix. Confidence is verbalized JSON. The API does not return logprobs | `verbalized` | **Not run.** Needs your Anthropic API key. |

The baseline is a floor. It is not one of the two arms.

Splits use seed 42. A stratified 10% slice of the 10,003 training rows is validation (1,003 validation / 9,000 train). Validation is for tuning only: logistic regression `C`, and the router threshold. The official test set (3,080) is scored once after that choice is frozen.

The router auto-routes a ticket when confidence is at least `t`, and otherwise sends it to a human. `t` is the lowest threshold on the validation sweep whose auto-routed accuracy is at least 95%. That threshold is applied once to test.

For each split the harness records accuracy with raw counts, macro-F1 over all 77 intents, macro-F1 on six fraud-adjacent intents, p50 and p99 per-ticket latency, a 10-bin reliability table, and expected calibration error (ECE) on the top-label probability.

Fraud-adjacent intents: `compromised_card`, `card_payment_not_recognised`, `lost_or_stolen_card`, `direct_debit_payment_not_recognised`, `cash_withdrawal_not_recognised`, `lost_or_stolen_phone`.

Cost per 1,000 tasks is `harness/cost.py`. Prices and times are arguments, not figures from a Qwen or Opus run. The shipped baseline row records $0 per 1,000 tasks. No Qwen or Opus cost was measured. The Opus script notes that the shared prefix is about 431 tokens, under the 4,096-token Opus 4.5 cache minimum, so a cache control on that prefix does not apply.

## Measured baseline

From `harness/results.csv` and `harness/out/baseline-summary.json`. These files are the reference run. `make baseline` should match the test count below. Latency and the hardware string follow the machine you run on.

| | Test |
|---|---|
| Correct | **2,802 / 3,080 (91.0%)** |
| Macro-F1 | **0.910** |
| ECE (10 bins) | **0.044** |
| `C` | 30, picked on validation |
| Router threshold | **0.45** (lowest validation threshold with auto-routed accuracy at least 95%) |
| Auto-routed | **2,877** tickets, **94.3%** correct on that slice (2,714 / 2,877) |
| To a human | **203** |

Validation, tuning only: 912 / 1,003 correct. Test macro-F1 on the six fraud-adjacent intents is 0.907. The weakest of those six is `card_payment_not_recognised` at 0.854. Fit on the reference box took 18.9 seconds. Latency in the summary is amortised batch time, not per-request latency.

Reference box: CPU only, 8 vCPU, 16 GiB RAM. Python 3.13.5, scikit-learn 1.9.1, numpy 2.5.4. No GPU.

## Qwen and Opus were not run

`results.csv` has no Qwen or Opus rows, and this repo has no predictions for them.

- Qwen needs a GPU you provide, the base weights, and a LoRA checkpoint you train. `make qwen-train` and `make qwen-infer` exit unless you pass `I_HAVE_A_GPU=1`. The scripts exit unless you pass `--i-have-a-gpu`, and they exit again when CUDA is not visible.
- Opus needs your own `ANTHROPIC_API_KEY`. `make opus` exits without that variable and without `I_HAVE_APPROVAL=1`. `harness/arm_opus.py` exits unless both the key and `--i-have-approval` are present. Calls are billed to your account.

## Dataset

Banking77, by PolyAI. 77 intents, 10,003 train examples and 3,080 test examples. Licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

`harness/data/train.csv` and `harness/data/test.csv` are those files from the PolyAI GitHub repository. If they are absent, the loader downloads the same paths:

https://github.com/PolyAI-LDN/task-specific-datasets/tree/master/banking_data

Cite: Iñigo Casanueva, Tadas Temcinas, Daniela Gerz, Matthew Henderson, and Ivan Vulic, *Efficient Intent Detection with Dual Sentence Encoders*, Proceedings of the 2nd Workshop on NLP for ConvAI, ACL 2020. https://arxiv.org/abs/2003.04807

The Hugging Face `datasets` loader for Banking77 is a dataset script and fails on current `datasets`. This kit uses the GitHub CSVs for that reason.

## Run

CPU only. No API key.

```bash
cd specialist-bakeoff
make baseline
```

That creates `.venv`, installs `requirements.txt` (numpy and scikit-learn), and runs `harness/baseline_tfidf.py`. It replaces the two `baseline-tfidf-lr` rows in `harness/results.csv` and rewrites `harness/out/baseline-summary.json`. Per-ticket predictions are written under `harness/out/` and are not committed. `make baseline` regenerates them.

The arms, only when you mean to use your own GPU or pay for API calls:

```bash
pip install -r requirements-arms.txt
make qwen-train I_HAVE_A_GPU=1
make qwen-infer I_HAVE_A_GPU=1 CKPT=ckpt/qwen-b77-lora SPLIT=val
make opus I_HAVE_APPROVAL=1 SPLIT=val LIMIT=20
```

`make opus` refuses without `ANTHROPIC_API_KEY` and without `I_HAVE_APPROVAL=1`. `make qwen-train` and `make qwen-infer` refuse without `I_HAVE_A_GPU=1`.

Modelled cost from token counts you supply. This does not call an API, and this repo has no measured token counts for the arms:

```bash
make cost PREFIX_TOK=... VAR_IN_TOK=... OUT_TOK=...
```

## Layout

```
specialist-bakeoff/
  harness/baseline_tfidf.py
  harness/train_qwen_lora.py
  harness/arm_qwen_infer.py
  harness/arm_opus.py
  harness/cost.py
  harness/results.csv
  harness/out/baseline-summary.json
  harness/results_schema.md
  requirements.txt
  requirements-arms.txt
```

## License

Code is MIT. See [LICENSE](LICENSE). The Banking77 CSVs remain under CC BY 4.0. Qwen and Claude weights are not in this repo.
