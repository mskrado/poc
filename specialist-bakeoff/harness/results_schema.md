# results.csv schema (one row per arm x split)

| column | type | meaning |
|---|---|---|
| run_id | str | `<arm>-<split>-<UTC timestamp>` |
| arm | str | `qwen3.5-9b-lora` / `claude-opus-4-5` / `baseline-tfidf-lr` |
| status | str | `measured` or `modelled` |
| split | str | `val` (tuning only) or `test` (touched once) |
| n | int | tickets scored |
| correct | int | raw count correct |
| accuracy | float | correct / n |
| macro_f1 | float | mean F1 over 77 intents |
| fraud6_macro_f1 | float | mean F1 over the six fraud-adjacent intents |
| p50_latency_s, p99_latency_s | float | per-ticket wall time (client side) |
| ece | float | expected calibration error, 10 bins, top-label prob |
| conf_source | str | `softmax` (Qwen label prob), `verbalized` (Opus JSON), `predict_proba` (baseline) |
| router_threshold | float | chosen on val; blank on val rows |
| auto_routed, to_human | int | count at router_threshold |
| input_tokens, cache_write_tokens, cache_read_tokens, output_tokens | int | summed API usage (Opus only) |
| train_gpu_h, serve_gpu_h | float | GPU hours (Qwen only) |
| gpu_usd_per_h | float | rate used |
| labelling_usd | float | labels x sec/label / 3600 x $/h |
| cost_per_1k_full_usd | float | Opus at list rate, no cache; Qwen amortised |
| cost_per_1k_cached_usd | float | Opus with cached 77-label prefix |
| hardware | str | e.g. `CPU 8 vCPU Xeon, 15 GiB` / `1x RTX PRO 6000 96GB` |
| versions | str | key package versions |
| seed | int | 42 |

Per-ticket predictions go to `out/<arm>-<split>-preds.jsonl`: id, gold, pred, conf, latency_s, usage.
Those jsonl files are not committed. `make baseline` regenerates the baseline ones.
