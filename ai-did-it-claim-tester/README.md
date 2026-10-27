# AI Did It? Layoff Claim Test Kit

When a company says "AI now does the work," this kit tests that claim. It has four parts, each credited to its author:

1. **Worker & HR checklist** by Noah Solace: five checks when AI is the stated reason for a cut. *Templates and checklists, not legal advice; check your own jurisdiction and contract.*
2. **Board payback test** by Av Ledger: five questions, with payback = charges ÷ incremental annual savings. You run that calculation on your own numbers.
3. **Claim tester** by Rex Circuit: `sweep.py`, a confidence-threshold sweep that shows how much a model handles alone and how much still goes to a person.
4. **"Who does this now" map** by Zara Nova: `kit/who-does-this-now-map.csv`.

The full kit with all four parts is in `kit/layoff-claim-test-kit.pdf` (and `.html`).

## Run the claim tester

Runs on CPU in under a minute:

```bash
pip install scikit-learn datasets
python sweep.py
```

- **Data:** Banking77 (3,080 official test tickets), loaded from Hugging Face `legacy-datasets/banking77` (parquet).
- **Split:** 10% of train held out as validation, stratified, seed 42, giving 9,000 / 1,003 / 3,080.
- **Model:** TF-IDF on word 1–2-grams plus char 2–5-grams, then logistic regression with C=30.
- **Method:** pick a threshold on validation, then read the result on test.

## Measured results (test, 3,080 tickets)

Run on CPU only: 8 vCPU, 16 GiB RAM. Training took about 20 s. Cost: $0.

| Threshold | Handled by model | Accuracy on those | Wrong | Sent to a person |
|---|---|---|---|---|
| 0.00 | 3,080 (100%) | 91.0% | 278 | 0 |
| 0.45 | 2,877 (93.4%) | 94.3% | 163 | 203 (6.6%) |
| 0.65 | 2,639 (85.7%) | 97.0% | 80 | 441 (14.3%) |
| 0.85 | 2,235 (72.6%) | 98.6% | 31 | 845 (27.4%) |
| 0.95 | 1,706 (55.4%) | 99.4% | 11 | 1,374 (44.6%) |

The full sweep is in `results/sweep_results.csv`, and the chart is `results/sweep_chart.png`.

## To try it on your own task

Replace the data loading with a sample of your own tickets and their correct labels. Choose your threshold on a held-out set, then report what goes to a person at the accuracy you actually need.

One public dataset and one simple model is a starting point, not a verdict on any company.
