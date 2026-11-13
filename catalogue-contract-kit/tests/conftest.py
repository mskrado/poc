import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixture_server import serve  # noqa: E402
from rexcat.discover import discover  # noqa: E402
from rexcat.fetch import PoliteSession  # noqa: E402
from rexcat.run import run_store  # noqa: E402


def _run(variant):
    httpd, base = serve(variant)
    try:
        sess = PoliteSession(min_interval=0.0, timeout=5)
        d = discover(sess, base)
        return d, run_store(sess, base, d["product_url"], d["category_url"])
    finally:
        httpd.shutdown()


@pytest.fixture(scope="session")
def pass_store():
    return _run("pass")


@pytest.fixture(scope="session")
def fail_store():
    return _run("fail")


@pytest.fixture(scope="session")
def blocked_store():
    return _run("blocked")
