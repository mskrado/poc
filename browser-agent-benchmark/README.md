# browser-agent-benchmark

![Three browser automation frameworks - DOM-based, over-clicking, and pixel-based - attempting real web workflows, escalating through a tiered router to a human handoff](assets/hero.png)

> **Article:** [Browser-Use Frameworks Compared: Playwright-MCP, Browser-Use, and Computer-Use Against 30 Real Workflows](https://roiscale.ai/sites/roiscale/articles/4e8c4b38-7b2d-47ad-8118-0d542259e707/browser-use-frameworks-compared-playwright-mcp-browser-use-and-computer-use)  
> *roiscale.ai — Rex runs 30 real browser automation workflows (flight booking, tax forms, paywalled reports, Notion migrations) through three frameworks and publishes success rates and failure patterns that the README demos will never show you.*

This POC is a **runnable harness** for that methodology: the 30-workflow catalog, the scoring rules, the failure-mode taxonomy, and the tiered router the author actually deployed.

Two deliberate scoping decisions:

1. **The agents drive local synthetic sites**, not real airlines, tax authorities, or billing portals. Each fixture isolates one failure mode from the article.
2. **Framework outcomes are a calibrated replay**, not a live measurement. The three adapters are thin stubs that document their hook points; mock mode reproduces the published rates so the scoring, routing, and reporting layers can be exercised with no API keys and no cost.

## What it demonstrates

| Article element | POC behavior |
|---|---|
| 30 workflows across 4 categories | [`config/tasks.yaml`](config/tasks.yaml) — 10 transactional, 8 extraction, 7 migration, 5 forms |
| Per-category success rates | Published rates pinned in `config/frameworks/*.yaml`, reproduced exactly by mock mode |
| Partial credit (+15-22 pts) | Three-valued scoring: `full` / `partial` / `fail`, reported side by side |
| "Got to checkout, never clicked confirm" | The most heavily weighted partial mode for all three frameworks |
| Playwright-MCP breaks on SPA re-renders | [`fixtures/sites/spa_form/`](fixtures/sites/spa_form/index.html) regenerates `data-testid` after every interaction |
| Browser-Use over-clicks (18 actions vs 11) | Per-framework action model, asserted in tests |
| Computer-Use wins on odd forms, loses on time | 60% on form completion, 4:20 mean vs 1:40 |
| All three lose to MFA | Two tasks tagged `mfa` always fail and always reach a human |
| Tiered deployment: 71% / 29% | [`browser_benchmark/router.py`](browser_benchmark/router.py) — Browser-Use, then Playwright-MCP, then a human |
| Synthetic task runner | [`browser_benchmark/synth_data.py`](browser_benchmark/synth_data.py) — believable form data, reserved test values only |

## Quick start

```bash
cd browser-agent-benchmark
python -m pip install -e ".[dev]"
python demo.py --scenario all
python -m pytest -q
```

## CLI

```bash
browser-benchmark list                      # frameworks and their published numbers
browser-benchmark list --tasks              # the 30 workflows with goals and tags
browser-benchmark compare --failures        # full matrix plus failure-mode breakdown
browser-benchmark compare --output reports/ # writes JSON + Markdown
browser-benchmark run --framework computer_use --categories form_completion
browser-benchmark route --detail            # tiered router, per-task escalation trail
browser-benchmark serve --port 8000         # browse the fixture sites yourself
browser-benchmark synth --kind contacts --rows 50 --output data/contacts.csv
```

## Example output

```
Framework      | Full  | Strict | With partial | Mean time | Actions | $/task
---------------|-------|--------|--------------|-----------|---------|-------
playwright_mcp | 16/30 | 53%    | 70% (+17pt)  | 2:09      | 11      | $0.11
browser_use    | 14/30 | 47%    | 63% (+17pt)  | 1:42      | 18      | $0.06
computer_use   | 13/30 | 43%    | 63% (+20pt)  | 4:07      | 14      | $0.42

Category        | Tasks | playwright_mcp | browser_use   | computer_use
----------------|-------|----------------|---------------|--------------
Transactional   | 10    | 60% (ref 60%)  | 50% (ref 50%) | 30% (ref 30%)
Data extraction | 8     | 62% (ref 62%)  | 62% (ref 62%) | 50% (ref 50%)
Migration/bulk  | 7     | 43% (ref 43%)  | 43% (ref 43%) | 43% (ref 43%)
Form completion | 5     | 40% (ref 40%)  | 20% (ref 20%) | 60% (ref 60%)
```

Tiered routing over the same suite:

```
Resolution      | Tasks | Rate | Article reference
----------------|-------|------|------------------
Fully automated | 21    | 70%  | 71%
Human-assisted  | 9     | 30%  | 29%

resolved by tier    browser_use: 14, playwright_mcp: 7
escalations         16
agent cost          $3.56 (all-playwright_mcp baseline: $3.30)
human cost          $40.50 (54 operator minutes)
```

## How mock mode decides what fails

Rates are pinned; the model chooses *which* tasks land in each bucket.

1. Every task gets a difficulty draw from a stable hash of `(seed, task id)`.
2. Each framework blends that shared draw with a private one, mixed by `difficulty_correlation` in [`config/router.yaml`](config/router.yaml). At 0 every framework fails independently and the tiered router looks better than it is; at 1 they all fail on exactly the same tasks. The default of `0.60` reproduces the article's 71/29 production split.
3. Tasks are sorted by difficulty inside their category, and the published rate decides how many land in `full`, then the partial bonus fills the next slice.
4. Tasks tagged `mfa` always fail, for every framework.

Changing `--seed` reshuffles which workflows fail without moving the published rates, which is what makes the router's escalation numbers worth looking at more than once.

## Fixture sites

| Fixture | Failure mode it isolates |
|---|---|
| [`spa_form`](fixtures/sites/spa_form/index.html) | Re-render regenerates `data-testid`; the selector the agent just used no longer resolves |
| [`soft_paywall`](fixtures/sites/soft_paywall/index.html) | Full text stays in the DOM behind an overlay: free for DOM agents, invisible to pixels |
| [`multipage_form`](fixtures/sites/multipage_form/index.html) | Div-based fake select with no ARIA role, plus an accessibility overlay, across 3 pages |
| [`bulk_table`](fixtures/sites/bulk_table/index.html) | 50 rows across 5 pages — where step budgets run out |
| [`checkout`](fixtures/sites/checkout/index.html) | The partial-success trap: an upsell interstitial in front of the irreversible click |
| [`mfa_gate`](fixtures/sites/mfa_gate/index.html) | Out-of-band code that no framework can satisfy unattended |

Serve them with `browser-benchmark serve` and poke at them by hand.

## Going live

Live mode is deliberately unimplemented — each adapter raises `LiveModeUnavailable` with its hook point:

| Framework | Hook point |
|---|---|
| [`playwright_mcp`](browser_benchmark/frameworks/playwright_mcp.py) | stdio MCP session against `npx @playwright/mcp@1.1.0 --headless`, then an Anthropic tool-use loop capped at 25 steps |
| [`browser_use`](browser_benchmark/frameworks/browser_use.py) | `browser_use.Agent(task=..., llm=ChatOpenAI(model="gpt-4o")).run(max_steps=30)` |
| [`computer_use`](browser_benchmark/frameworks/computer_use.py) | Anthropic computer-use tool loop driving a Dockerized Chrome on a virtual display |

To wire one up: `pip install -e ".[live]"`, implement `run_task` on the adapter, and point it at `browser-benchmark serve` before anything else. The scoring, routing, and reporting layers do not change.

## Article reference values (from config)

| Framework | Overall | Transactional | Extraction | Migration | Forms | Mean time |
|---|---|---|---|---|---|---|
| Playwright-MCP | 52% | 60% | 62% | 43% | 40% | 2:10 |
| Browser-Use | 47% | 50% | 62% | 43% | 20% | 1:40 |
| Computer-Use | 41% | 30% | 50% | 43% | 60% | 4:20 |

## License

MIT — see [LICENSE](LICENSE).
