# copilot-two-arm

Two controlled studies of AI coding tools disagree: an arXiv preprint (Peng et al., Feb 2023) measured a 55.8% faster HTTP-server task with Copilot, and a METR arXiv preprint (July 2025) measured 19% more time for experienced developers on their own mature repos. This harness lets a team time both kinds of work on its own machines, with and without AI, and log how fast it *felt* next to how fast it *was*.

It is not a replication of either study.

## Arms
- **Arm A, greenfield:** write `server.py` (stdlib HTTP item store) from `SPEC.md`; 12 hidden acceptance checks.
- **Arm B, mature fix:** `inflection` 0.5.1 (MIT), pinned by sha256 from PyPI, with one seeded bug and `ISSUE.md`; graded by the project's own suite plus hidden regression checks.

Swap Arm B for a real issue from your own repo for a real answer: point `manifest.json` at your pinned tarball and seed patch.

## Run
```bash
pip install -e .            # or: pip install pytest matplotlib
python demo.py              # self-check: empty fails, reference passes
python -m twoarm start  --arm A --condition no_ai --workspace runs/a1 --who alice --forecast-pct -30
# ...work in runs/a1 ...
python -m twoarm finish --workspace runs/a1 --felt-pct -20
python -m twoarm readout    # results/readout.md + results/charts/readout.png
pytest -q
```
`forecast-pct` is asked before the run, `felt-pct` after (negative = faster with AI), the same two questions METR asked. Wall time is monotonic clock from `start` to `finish`; grading is excluded. The readout never blends arms and prints `n/a` for a ratio until both conditions have runs.

## Pilot in this repo
`results/runs.csv` holds a 2-run demo on one box (an AI agent, n=1 per arm, no no-AI runs). See `results/readout.md`. Small demo on my hardware, not a replication.

## Credits
Logging felt speed next to measured time per run: idea from Noah Solace (Labor & Society, roiscale.ai).

## License
MIT. `inflection` is MIT, Copyright (C) 2012-2020 Janne Vanhala, downloaded at run time, not vendored.
