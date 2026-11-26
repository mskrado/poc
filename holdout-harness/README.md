# holdout-harness

> **Article:** One Airline Reports 3–5% From AI Pricing. Zero Carriers Published Holdout Results. Here Is the Harness.  
> *roiscale.ai (Builder Lab) — Split-route and booking-cohort holdouts for an AI pricing or booking flow, in plain Python 3 (stdlib only; matplotlib optional for the chart).*

**Everything the bundled CLI prints is synthetic test data.** The generator invents a network of routes and sessions with a known true lift, a network-wide fare move, and a spillover effect, so you can see which estimator recovers the truth. None of it is carrier data.

## Reproduce

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install ".[test]" && pytest -q && holdout-harness run --seed 20261125 --out results/
```

Optional chart (`matplotlib>=3.7`):

```bash
pip install ".[chart]" && holdout-harness run --seed 20261125 --out results/ --chart
```

## Tested environment

Clean-machine verification (`prove_clean.sh`) from a fresh copy and fresh virtualenv:

| | |
|---|---|
| Python | 3.13.5 |
| pip | 25.1.1 |
| pytest | 9.2.0 |
| Hardware | 8 vCPU Xeon, 15 GiB RAM, CPU only |
| Tests | 21/21 tests pass |
| Reproducibility | Byte-identical `results.csv` across two runs (`sha256`: `8989494656570c76ded03ff2d567c0521d05b212ea7b3110ecc11911d3d78a4c`) |

## Layout

```
holdout-harness/
  src/
    holdout_harness/
      __init__.py      # version, synthetic label, public exports
      bucketing.py     # salted SHA-256 bucketing and market-level assignment
      spillover.py     # mixed_markets() and cross_bucket_customers() guards
      stats.py         # Welch CI (incomplete-beta t quantile), bootstrap CI, CUPED, MDE/power
      synth.py         # synthetic route panel and booking-session generators
      cli.py           # CLI entry point writing results.csv, summary.md, optional chart.png
  tests/
    test_bucketing.py
    test_spillover.py
    test_stats.py
    test_cli.py
  pyproject.toml
  prove_clean.sh
  LICENSE
  README.md
```

## What's inside

| Module | Does |
|---|---|
| `bucketing.py` | Salted SHA-256 bucketing (stable across machines, never `hash()`); `assign_routes_by_market` hashes the market so competing routes share an arm |
| `spillover.py` | `mixed_markets` (treated and control routes in one market) and `cross_bucket_customers` (one traveller seen in both arms) |
| `stats.py` | Welch CI (t quantile via incomplete beta continued fraction, no SciPy), seeded percentile bootstrap for relative lift, CUPED, `mde` and `n_per_arm` power helpers |
| `synth.py` | Synthetic route panel (86 routes in 48 markets, 28 pre days + 28 test days) and synthetic booking sessions (60,000 travellers, 82,448 sessions) |
| `cli.py` | `holdout-harness run`: writes `results.csv`, `summary.md`, optional `chart.png` |

## Sample output (synthetic test data)

Running `holdout-harness run --seed 20261125 --out results/` produces `results.csv` and `summary.md` with every row labelled `synthetic test data`:

```
- seed: 20261125  salt: pf-20261121  true lift (synthetic): 2.00%  network-wide fare move (synthetic): 10.00%  spillover steal (synthetic): 4.00%
- routes: 86 in 48 markets; sessions: 82448

| design | estimator | lift | 95% CI | true | flags |
|---|---|---|---|---|---|
| split-route (market-hashed) | naive pre/post, treated routes only | +12.50% | none | +2.00% | mixed_markets=0 |
| split-route (market-hashed) | holdout diff-in-means, Welch 95% CI | +4.65% | -19.54% to +28.85% | +2.00% | mixed_markets=0 |
| split-route (market-hashed) | holdout + CUPED (log revenue), Welch 95% CI | +1.79% | +0.42% to +3.18% | +2.00% | mixed_markets=0 |
| split-route (market-hashed) | holdout on test/pre ratio, bootstrap 95% CI | +1.80% | +0.51% to +3.14% | +2.00% | mixed_markets=0 |
| split-route (route-hashed, leaky) | holdout on test/pre ratio, bootstrap 95% CI | +7.44% | +5.52% to +9.56% | +2.00% | mixed_markets=18 |
| booking cohort (session-hashed) | all sessions, Welch 95% CI | -24.17% | -29.43% to -18.92% | +2.44% | cross_bucket_customers=9317 |
| booking cohort (session-hashed) | flagged customers excluded, Welch 95% CI | +2.64% | -3.91% to +9.18% | +2.44% | excluded_customers=9317 |
```

## Using it on your own data

1. Map each route to the market it competes in (city pair, including alternate airports). Call `assign_routes_by_market(route_to_market, salt)` once, store the result, and freeze the salt for the test.
2. Run `mixed_markets(arm, route_to_market)` before launch. It must return `[]`.
3. For session-level tests, log a stable customer key next to the session arm and run `cross_bucket_customers` on the bookings. Report the count and the estimate with and without them.
4. Read lift on the test/pre ratio (bootstrap) or with CUPED on the pre-period metric, not on raw route revenue: route size swamps everything else.
5. Run `mde()` with your own pre-period spread *before* you start, so you know whether your route count can see the lift you're hoping for.

## Known limits

- Every CLI figure is **synthetic test data** from `synth.py`. The generator, its effect sizes, and its spillover model are author assumptions; a harness recovering effects from its own generator checks the plumbing, not the world.
- `mde` and `n_per_arm` use the normal approximation.
- No time-series correction beyond pre-period adjustment; long tests with drifting seasonality need more.

## License

MIT — see [LICENSE](LICENSE).
