"""Arm B: Claude Opus 4.5 zero-shot. NOT RUN in this kit.
Needs your own ANTHROPIC_API_KEY and an explicit --i-have-approval flag (paid calls).
Cacheable 77-label prefix in the system block (cache_control ephemeral). Logs usage + client latency.
CACHING CAVEAT: Opus 4.5 minimum cacheable prompt = 4,096 tokens (Anthropic docs, 2026-10-20).
This ~431-token prefix is below it, so cache_control is silently ignored (cache fields = 0).
The "cached" cost column is therefore n/a for zero-shot; it is still computed from the logged usage.
Confidence is VERBALIZED (the API exposes no logprobs) -> conf_source=verbalized; calibrate with care.

  pip install -r requirements-arms.txt
  python arm_opus.py --split val --limit 20 --i-have-approval   # smoke test first
"""
import argparse, json, os, sys, time
from common import load_splits, labels, system_prefix, user_msg, summarize, threshold_sweep
from results_io import append, dump_preds, run_id

MODEL = "claude-opus-4-5-20251101"

def parse(txt, labs):
    try:
        j = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
        lab = j.get("label", ""); c = float(j.get("confidence", 0))
    except Exception:
        lab, c = "", 0.0
    return (lab if lab in labs else "__invalid__"), max(0.0, min(1.0, c))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--split", choices=["val", "test"], required=True)
    ap.add_argument("--limit", type=int); ap.add_argument("--i-have-approval", action="store_true")
    a = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY") or not a.i_have_approval:
        sys.exit("Refusing: set ANTHROPIC_API_KEY and pass --i-have-approval (paid calls). The Opus arm was not run for this kit.")
    try:
        import anthropic
    except ImportError:
        sys.exit("Refusing: install the optional arms requirements (pip install -r requirements-arms.txt).")
    cli = anthropic.Anthropic(); labs = set(labels())
    train, val, test = load_splits(); rows = (val if a.split == "val" else test)[: a.limit]
    sysblk = [{"type": "text", "text": system_prefix(), "cache_control": {"type": "ephemeral"}}]
    out, U = [], dict(input_tokens=0, cache_write_tokens=0, cache_read_tokens=0, output_tokens=0)
    for r in rows:
        t0 = time.perf_counter()
        m = cli.messages.create(model=MODEL, max_tokens=40, temperature=0, system=sysblk,
                                messages=[{"role": "user", "content": user_msg(r["text"])}])
        dt = time.perf_counter() - t0
        u = m.usage; usage = dict(input_tokens=u.input_tokens,
                                  cache_write_tokens=u.cache_creation_input_tokens or 0,
                                  cache_read_tokens=u.cache_read_input_tokens or 0, output_tokens=u.output_tokens)
        for k in U: U[k] += usage[k]
        pred, conf = parse(m.content[0].text, labs)
        out.append(dict(id=r["id"], gold=r["label"], pred=pred, conf=conf, latency_s=dt, usage=usage))
    s = summarize(out); dump_preds(f"opus-{a.split}-preds.jsonl", out)
    if a.split == "val":
        json.dump(threshold_sweep([o["conf"] for o in out], [int(o["gold"] == o["pred"]) for o in out]),
                  open("out/opus-val-sweep.json", "w"), indent=1)
    n = len(out)
    actual_per_1k = (U["input_tokens"]*5 + U["cache_write_tokens"]*6.25 + U["cache_read_tokens"]*0.5
                     + U["output_tokens"]*25) / 1e6 / n * 1000
    full_per_1k = ((U["input_tokens"]+U["cache_write_tokens"]+U["cache_read_tokens"])*5 + U["output_tokens"]*25)/1e6/n*1000
    append(dict(run_id=run_id("claude-opus-4-5", a.split), arm="claude-opus-4-5", status="measured", split=a.split,
                conf_source="verbalized", cost_per_1k_full_usd=full_per_1k, cost_per_1k_cached_usd=actual_per_1k,
                hardware="Anthropic API", versions=f"anthropic {anthropic.__version__}", seed=42, **U,
                **{k: v for k, v in s.items() if not isinstance(v, (dict, list))}))
    print(json.dumps({k: v for k, v in s.items() if k != "reliability"}, indent=1))

if __name__ == "__main__": main()
