"""Arm A inference: score all 77 labels by log-likelihood with the LoRA checkpoint (no free-text parsing).
Top-label probability = softmax over the 77 summed label log-probs -> conf_source=softmax.
NOT RUN in this kit. Needs your own GPU and a checkpoint you trained.
Refuses unless you pass --i-have-a-gpu.

  python arm_qwen_infer.py --i-have-a-gpu --ckpt ckpt/qwen-b77-lora --split val
One forward pass per ticket: 77 rows = prompt + candidate, right-padded.
"""
import argparse, json, math, sys, time
from common import load_splits, labels, system_prefix, user_msg, summarize, threshold_sweep
from results_io import append, dump_preds, run_id

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ckpt", default="")
    ap.add_argument("--base", default="Qwen/Qwen3.5-9B"); ap.add_argument("--split", choices=["val", "test"], required=True)
    ap.add_argument("--gpu-rate", type=float, default=2.49); ap.add_argument("--train-gpu-h", type=float)
    ap.add_argument("--i-have-a-gpu", action="store_true",
                    help="Required. Confirms this run is on your own GPU.")
    a = ap.parse_args()
    if not a.i_have_a_gpu:
        sys.exit("Refusing: the Qwen arm was not run for this kit. Pass --i-have-a-gpu to score on your own GPU.")
    if not a.ckpt:
        sys.exit("Refusing: pass --ckpt pointing at your LoRA checkpoint.")
    try:
        import torch
    except ImportError:
        sys.exit("Refusing: install requirements-arms.txt on a machine with a CUDA GPU.")
    if not torch.cuda.is_available():
        sys.exit("Refusing: no CUDA GPU is visible.")
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    tok = AutoTokenizer.from_pretrained(a.base)
    base = AutoModelForCausalLM.from_pretrained(a.base, torch_dtype=torch.bfloat16, device_map="cuda")
    model = PeftModel.from_pretrained(base, a.ckpt).merge_and_unload().eval()
    labs = labels(); _, val, test = load_splits(); rows = val if a.split == "val" else test
    cand_ids = [tok(json.dumps({"label": l}), add_special_tokens=False).input_ids for l in labs]
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    out, t_all = [], time.perf_counter()
    for r in rows:
        prompt = tok.apply_chat_template([{"role": "system", "content": system_prefix()},
                                          {"role": "user", "content": user_msg(r["text"])}],
                                         tokenize=False, add_generation_prompt=True)
        p = tok(prompt, add_special_tokens=False).input_ids
        seqs = [p + c for c in cand_ids]; L = max(map(len, seqs))
        ids = torch.full((len(seqs), L), pad); att = torch.zeros_like(ids)
        for i, s in enumerate(seqs): ids[i, :len(s)] = torch.tensor(s); att[i, :len(s)] = 1
        t0 = time.perf_counter()
        with torch.no_grad():
            lp = torch.log_softmax(model(ids.cuda(), attention_mask=att.cuda()).logits.float(), -1)
        scores = []
        for i, c in enumerate(cand_ids):
            pos = torch.arange(len(p) - 1, len(p) - 1 + len(c), device=lp.device)
            scores.append(lp[i, pos, torch.tensor(c, device=lp.device)].sum().item())
        dt = time.perf_counter() - t0
        m = max(scores); ps = [math.exp(s - m) for s in scores]; z = sum(ps)
        k = max(range(len(labs)), key=lambda i: scores[i])
        out.append(dict(id=r["id"], gold=r["label"], pred=labs[k], conf=ps[k] / z, latency_s=dt))
    serve_h = (time.perf_counter() - t_all) / 3600
    s = summarize(out); dump_preds(f"qwen-{a.split}-preds.jsonl", out)
    if a.split == "val":
        json.dump(threshold_sweep([o["conf"] for o in out], [int(o["gold"] == o["pred"]) for o in out]),
                  open("out/qwen-val-sweep.json", "w"), indent=1)
    append(dict(run_id=run_id("qwen3.5-9b-lora", a.split), arm="qwen3.5-9b-lora", status="measured", split=a.split,
                conf_source="softmax", train_gpu_h=a.train_gpu_h, serve_gpu_h=serve_h, gpu_usd_per_h=a.gpu_rate,
                hardware=torch.cuda.get_device_name(0), seed=42,
                **{k: v for k, v in s.items() if not isinstance(v, (dict, list))}))
    print(json.dumps({k: v for k, v in s.items() if k != "reliability"}, indent=1))

if __name__ == "__main__": main()
