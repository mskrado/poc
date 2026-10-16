# Delivery Readiness Check (scored)

Run before an AI coding pilot scales beyond its first team. Score each item 0 (fail), 1 (partial) or 2 (pass). Capability names and page references are from DORA, *State of AI-assisted Software Development 2025*, v. 2025.2 (https://dora.dev/research/2025/dora-report/). Thresholds marked "team-set" or "default" are this blueprint's starting points, not DORA benchmarks.

## A. Review (DORA capability: Working in small batches, report p. 58)
| # | Item | Pass (2) | Fail (0) |
|---|---|---|---|
| A1 | Batch size is measured | Median lines per change and changes per release reported weekly | Not measured |
| A2 | Batch ceiling exists for AI-assisted changes | Team-set ceiling written down and enforced in CI or review | No ceiling |
| A3 | Every change is reviewed before merge | 100% of merges have an approving review | Any unreviewed path to production |
| A4 | Oversized diffs are split | Over-ceiling PRs are split or rejected, logged | Waved through |

## B. Rollback (DORA capability: Strong version control practices, pp. 56–57, 64)
| # | Item | Pass (2) | Fail (0) |
|---|---|---|---|
| B1 | Frequent commits | Commits to trunk or short-lived branches daily | Long-lived branches as the norm |
| B2 | Revert drill | Revert of a production deploy rehearsed within a team-set window (default 30 days, not a DORA figure), time recorded | Never rehearsed |
| B3 | One-step rollback | Any deploy can be rolled back with one documented command or button | Manual, multi-step |

## C. Measurement (DORA capability: Quality internal platform, p. 64; metric definitions p. 13)
| # | Item | Pass (2) | Fail (0) |
|---|---|---|---|
| C1 | Deploy record contract | Every deploy writes `deploy_id, commit_time, deploy_time, failed, ai_assisted` | No per-deploy record |
| C2 | Baseline exists | CFR and lead time computed for a window before the pilot scaled (>=20 deploys) | No baseline |
| C3 | AI split | Metrics reported split by `ai_assisted` | Aggregate only |
| C4 | Stop threshold | Named owner and numeric CFR/lead-time stop threshold set in advance | No owner or threshold |

## D. Policy (DORA capability: Clear and communicated AI stance, p. 64)
| # | Item | Pass (2) | Fail (0) |
|---|---|---|---|
| D1 | Written AI policy | Permitted tools and usage written and shared with every engineer | Unwritten or unknown |

## Scoring
- Maximum 24. **Ready to scale:** >= 20 with no 0 in A3, B2, C1 or C4.
- **Fix first:** 12–19, or any 0 in A3, B2, C1, C4.
- **Not ready:** < 12.
- Gate cut-offs are this blueprint's defaults; DORA publishes no readiness score.

## Running the measurement
`python3 delivery_metrics.py your_deploys.csv --max-cfr <team-set> --max-lead-hours <team-set>`
Exit 0 = both checks pass, 1 = a check fails, 2 = bad input. `failed` = the deploy needed immediate intervention (rollback or hotfix), DORA's change fail rate definition.

## Not covered
Rework rate, deployment frequency and failed deployment recovery time (DORA p. 13), and the other three capabilities (healthy data ecosystems, AI-accessible internal data, user-centric focus).
