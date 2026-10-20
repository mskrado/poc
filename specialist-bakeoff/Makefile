# Banking77 specialist bake-off.
# `make baseline` is CPU-only and free. The Qwen and Opus targets refuse
# unless you opt in on your own GPU or with your own Anthropic key.

PYTHON ?= python3
SPLIT ?= val

.PHONY: baseline opus qwen-train qwen-infer cost

.venv/bin/python: requirements.txt
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -r requirements.txt

baseline: .venv/bin/python
	cd harness && ../.venv/bin/python baseline_tfidf.py

# Refuses without ANTHROPIC_API_KEY and I_HAVE_APPROVAL=1.
# harness/arm_opus.py also refuses unless the key is set and --i-have-approval is passed.
opus: .venv/bin/python
	@test -n "$$ANTHROPIC_API_KEY" || { echo "Refusing: set ANTHROPIC_API_KEY. The Opus arm was not run for this kit."; exit 1; }
	@test "$(I_HAVE_APPROVAL)" = "1" || { echo "Refusing: pass I_HAVE_APPROVAL=1 to confirm paid calls (arm_opus.py --i-have-approval)."; exit 1; }
	cd harness && ../.venv/bin/python arm_opus.py --split $(SPLIT) $(if $(LIMIT),--limit $(LIMIT),) --i-have-approval

qwen-train:
	@test "$(I_HAVE_A_GPU)" = "1" || { echo "Refusing: the Qwen arm was not run. Pass I_HAVE_A_GPU=1 to train on your own GPU."; exit 1; }
	cd harness && $(PYTHON) train_qwen_lora.py --i-have-a-gpu $(if $(OUT),--out $(OUT),)

qwen-infer:
	@test "$(I_HAVE_A_GPU)" = "1" || { echo "Refusing: the Qwen arm was not run. Pass I_HAVE_A_GPU=1 to score on your own GPU."; exit 1; }
	@test -n "$(CKPT)" || { echo "Refusing: set CKPT to your LoRA checkpoint."; exit 1; }
	cd harness && $(PYTHON) arm_qwen_infer.py --i-have-a-gpu --ckpt $(CKPT) --split $(SPLIT)

# Modelled cost from token counts you supply. Does not call an API.
cost: .venv/bin/python
	@test -n "$(PREFIX_TOK)" && test -n "$(VAR_IN_TOK)" && test -n "$(OUT_TOK)" || { echo "Refusing: pass PREFIX_TOK, VAR_IN_TOK, and OUT_TOK. This kit has no measured arm token counts."; exit 1; }
	cd harness && ../.venv/bin/python cost.py --prefix-tok $(PREFIX_TOK) --var-in-tok $(VAR_IN_TOK) --out-tok $(OUT_TOK)
