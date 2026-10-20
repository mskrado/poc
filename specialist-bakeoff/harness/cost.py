"""Cost per 1,000 tasks. Every input is overridable from the CLI. Defaults are list prices / labelled proxies.

Opus 4.5 (platform.claude.com pricing, checked 2026-10-18): $5/M input, $25/M output,
  5-min cache write $6.25/M, cache read $0.50/M, Batch API = 50% off.
Labelling floor: $19.88/h (BLS figure supplied by the flow; labelled floor) x 27-29 s/label (labelled proxy).
"""
import argparse, json

def opus_per_1k(prefix_tok, var_in_tok, out_tok, cached=False, batch=False,
                p_in=5.0, p_out=25.0, p_cw=6.25, p_cr=0.50, calls_per_cache_write=1000, min_cache_tok=4096):
    """min_cache_tok: Opus 4.5 minimum cacheable prefix (Anthropic docs). Below it caching silently no-ops."""
    m = 0.5 if batch else 1.0
    if cached and prefix_tok < min_cache_tok:
        cached = False
    if not cached:
        per = (prefix_tok + var_in_tok) * p_in + out_tok * p_out
        return 1000 * per / 1e6 * m
    writes = 1000 / calls_per_cache_write
    tot = writes * prefix_tok * p_cw + (1000 - writes) * prefix_tok * p_cr \
        + 1000 * (var_in_tok * p_in + out_tok * p_out)
    return tot / 1e6 * m

def specialist_per_1k(train_gpu_h, gpu_rate, lifetime_tasks, serve_gpu_h_per_1k,
                      n_labels=0, sec_per_label=28.0, label_rate=19.88):
    labelling = n_labels * sec_per_label / 3600 * label_rate
    one_off = train_gpu_h * gpu_rate + labelling
    return {"labelling_usd": labelling, "one_off_usd": one_off,
            "per_1k_usd": one_off / lifetime_tasks * 1000 + serve_gpu_h_per_1k * gpu_rate}

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--prefix-tok", type=float, required=True); a.add_argument("--var-in-tok", type=float, required=True)
    a.add_argument("--out-tok", type=float, required=True)
    a.add_argument("--train-gpu-h", type=float, default=1.5); a.add_argument("--gpu-rate", type=float, default=2.49)
    a.add_argument("--lifetime-tasks", type=float, default=1_000_000); a.add_argument("--serve-gpu-h-per-1k", type=float, default=0.02)
    a.add_argument("--n-labels", type=int, default=9003); a.add_argument("--sec-per-label", type=float, default=28.0)
    a.add_argument("--label-rate", type=float, default=19.88)
    x = a.parse_args()
    print(json.dumps({
      "status": "modelled",
      "opus_full": opus_per_1k(x.prefix_tok, x.var_in_tok, x.out_tok),
      "opus_cached": opus_per_1k(x.prefix_tok, x.var_in_tok, x.out_tok, cached=True),
      "opus_cached_batch": opus_per_1k(x.prefix_tok, x.var_in_tok, x.out_tok, cached=True, batch=True),
      "specialist": specialist_per_1k(x.train_gpu_h, x.gpu_rate, x.lifetime_tasks, x.serve_gpu_h_per_1k,
                                      x.n_labels, x.sec_per_label, x.label_rate)}, indent=2))
