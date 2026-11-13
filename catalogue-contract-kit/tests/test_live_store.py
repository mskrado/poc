"""Point the six checks at your own store: STORE_URL=https://yourstore.example pytest tests/test_live_store.py
Skipped unless STORE_URL is set. Polite: obeys robots.txt for this kit's UA, 1 request/sec."""
import os

import pytest

from rexcat.discover import discover
from rexcat.fetch import PoliteSession
from rexcat.run import CHECK_COLUMNS, run_store

STORE = os.environ.get("STORE_URL")
pytestmark = pytest.mark.skipif(not STORE, reason="set STORE_URL to test your own store")


@pytest.fixture(scope="module")
def row():
    sess = PoliteSession()
    d = discover(sess, STORE)
    return run_store(sess, STORE, os.environ.get("PRODUCT_URL") or d["product_url"],
                     os.environ.get("CATEGORY_URL") or d["category_url"])


@pytest.mark.parametrize("check", CHECK_COLUMNS)
def test_check(row, check):
    assert row[check] == "pass", row["notes"]
