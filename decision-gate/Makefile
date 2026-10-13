PY ?= .venv/bin/python

.PHONY: setup build models data run cases sweep test report article

setup build:   ## create .venv and install the pinned requirements
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

models:        ## pull the two models (Ollama >= 0.35; scripts/start_ollama.sh)
	ollama pull tev1:4b && ollama pull qwen3.5:4b-q4_K_M

data:          ## download Bitext and check the 50-ticket stratified sample
	$(PY) scripts/fetch_bitext_sample.py --check

run:           ## full run: sample, both modes, write results and charts
	$(PY) run.py

cases:         ## rerun only the 4 error-entry cases and the regex scanner
	$(PY) run.py --cases

sweep:         ## human-route counts at several thresholds, from shipped results
	$(PY) scripts/threshold_sweep.py

test:
	$(PY) -m pytest -q

report:        ## rebuild csv / summary / charts from results/raw.json (a live run writes that file)
	$(PY) run.py --report-only

article:
	$(PY) article/build_article.py
