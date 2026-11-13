# Catalogue Contract Kit (Rex Circuit · Builder Lab, roiscale.ai)

Six pytest checks for the parts of a store catalogue a shopping agent's reader depends on.
Check definitions are modelled on the published definitions of the xfix AI Shopping Readiness
Index (https://xfix.ai/ux/research/ai-shopping-index/apparel/); the code is mine, not theirs.

| # | Check | Pass when |
|---|---|---|
| a | robots.txt lets AI agents in | robots.txt allows OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User and PerplexityBot on the product URL (404/410 robots = allow all) |
| b | product text without JS | raw HTML has a product `<h1>` (or the Product name in visible text) and at least 50 visible words, scripts stripped |
| c | price without JS | a currency amount appears in the visible raw-HTML text, scripts stripped |
| d | Product schema complete | a JSON-LD Product/ProductGroup declares price, availability, brand and an identifier (GTIN or SKU, on the Product, a variant or an Offer). Shipping (`shippingDetails`) is recorded, not required |
| e | category page lists products | a category page linked from the homepage has at least 5 distinct product links in its HTML |
| f | served to an unfamiliar crawler | the product page answers HTTP 200 to this kit's own User-Agent, and isn't a challenge page |

Each check returns `pass`, `fail` or `could-not-judge`.

## Reproduce (one command, no network)

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python -m pytest -q
```

Expected: `3 passed, 6 skipped`. The three fixture tests serve local static stores
(`fixtures/pass`, `fixtures/fail`, and a `blocked` variant that answers 403) on 127.0.0.1.
The six skipped tests are the live-store tests.

## Test your own store

```bash
STORE_URL=https://yourstore.example python -m pytest -q tests/test_live_store.py
# optional: PRODUCT_URL=... CATEGORY_URL=... to pin the pages
```

## Rerun the 20-store scan

```bash
python run_stores.py discover   # one product + one category page per store -> results/targets.json
python run_stores.py run 1      # -> results/results.csv
python run_stores.py run 2      # same frozen URLs, later the same day
python run_stores.py compare    # -> results/confirmed.csv (a result counts only if both runs agree)
python chart.py                 # -> results/rex-catalogue-checks-chart.png
```

## Crawling rules the kit follows

- Honest User-Agent: `RexCatalogueKit/0.1 (+https://roiscale.ai; ...)`. No browser spoofing.
- Obeys robots.txt for its own UA. If robots.txt can't be read (error, 401/403/429/5xx, or an HTML page
  instead of a robots file) it does not crawl that store at all, and every check is `could-not-judge`.
- At most 1 request per second per host, one retry after 10 s on a 429 homepage, and a handful of pages per
  store: robots.txt, homepage, up to 3 sitemap files (only when the homepage has no product link),
  one product page, one category page.

## Known limits

- One product page and one category page per store. A store with uneven pages can score differently on another page.
- Discovery takes the first product-looking link (gift cards skipped). On two stores that was a non-garment item.
- The "served" check only says the store blocked *this* unfamiliar crawler. It says nothing about how the store
  treats named AI assistants, which may be allowed by CDN rules nobody outside can see.
- The price regex covers $, £, €, ¥, ₹, kr, zł, CHF, KM and common ISO codes; other currencies may read as fail.
- No JavaScript is run, on purpose. No checkout is attempted.

Python 3.13.5, versions pinned in `requirements.txt` (full lock in `requirements-lock.txt`).

## Results in this folder (Nov 13, 2026)

- `stores.csv`: the 20 stores and why each was picked (selection locked 2026-11-13 17:38 UTC, before any check ran).
- `results/targets.json`: the frozen product and category URL per store, from `discover`.
- `results/results.csv`: both runs, one row per store per run, with a UTC timestamp per store.
  Run 1: 2026-11-13 17:51:35–17:52:44 UTC. Run 2: 2026-11-13 18:11:53–18:13:08 UTC.
- `results/confirmed.csv`: per store and check, run 1, run 2, and `confirmed` (the result if both runs agree, else `changed`).
- `results/rex-catalogue-checks-chart.png`: drawn by `chart.py` from `results.csv`.
- `results/run*-log.json`, `discover-log.json`: every request the kit made and the HTTP status it got.
- `results/pilot-run0-*.csv/json`: a pilot run before I fixed three kit bugs (the price regex missed `KM`,
  identifiers on an Offer were ignored, discovery picked gift cards). Kept for transparency; not reported.

Run from one box: Debian 13, Python 3.13.5, 8 vCPU Intel Xeon, 15 GiB RAM, one IP address.
