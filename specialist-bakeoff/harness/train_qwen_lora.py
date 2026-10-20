"""Arm A training: Qwen3.5-9B LoRA SFT with TRL + PEFT. NOT RUN in this kit.
Needs your own GPU. Refuses unless you pass --i-have-a-gpu.
bf16 base (~18 GB weights) fits without quantization. Train on the train split only (val held out).

  pip install -r requirements-arms.txt
  python train_qwen_lora.py --i-have-a-gpu --out ckpt/qwen-b77-lora
"""
import argparse, json, sys, time
from common import load_splits, system_prefix, user_msg

def to_chat(r):
    return {"messages": [{"role": "system", "content": system_prefix()},
                         {"role": "user", "content": user_msg(r["text"])},
                         {"role": "assistant", "content": json.dumps({"label": r["label"]})}]}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="Qwen/Qwen3.5-9B")
    ap.add_argument("--out", default="ckpt/qwen-b77-lora"); ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--i-have-a-gpu", action="store_true",
                    help="Required. Confirms this run is on your own GPU.")
    a = ap.parse_args()
    if not a.i_have_a_gpu:
        sys.exit("Refusing: the Qwen arm was not run for this kit. Pass --i-have-a-gpu to train on your own GPU.")
    try:
        import torch
    except ImportError:
        sys.exit("Refusing: install requirements-arms.txt on a machine with a CUDA GPU.")
    if not torch.cuda.is_available():
        sys.exit("Refusing: no CUDA GPU is visible.")
    from datasets import Dataset
    from peft import LoraConfig
    from trl import SFTConfig, SFTTrainer
    train, val, _ = load_splits()
    ds_tr = Dataset.from_list([to_chat(r) for r in train]); ds_va = Dataset.from_list([to_chat(r) for r in val])
    peft_cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
    cfg = SFTConfig(output_dir=a.out, num_train_epochs=a.epochs, per_device_train_batch_size=16,
                    gradient_accumulation_steps=1, learning_rate=2e-4, lr_scheduler_type="cosine",
                    warmup_ratio=0.03, bf16=True, logging_steps=20, eval_strategy="epoch", save_strategy="epoch",
                    assistant_only_loss=True, max_length=1024, seed=42, report_to="none",
                    model_init_kwargs={"torch_dtype": "bfloat16"})
    t0 = time.time()
    tr = SFTTrainer(model=a.model, args=cfg, train_dataset=ds_tr, eval_dataset=ds_va, peft_config=peft_cfg)
    tr.train(); tr.save_model(a.out)
    h = (time.time() - t0) / 3600
    json.dump({"train_gpu_h": h, "n_train": len(train), "epochs": a.epochs}, open(f"{a.out}/train_meta.json", "w"))
    print(f"train_gpu_h={h:.3f}")

if __name__ == "__main__": main()
