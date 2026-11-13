"""The kit's own contract tests, against local fixture stores. No network needed."""
from rexcat.run import CHECK_COLUMNS


def test_pass_store_passes_all_six(pass_store):
    d, row = pass_store
    assert d["product_url"].endswith("/products/oxford-shirt.html")
    assert d["category_url"].endswith("/collections/shirts.html")
    assert {c: row[c] for c in CHECK_COLUMNS} == {c: "pass" for c in CHECK_COLUMNS}, row["notes"]
    assert row["schema_shipping"] == "yes"


def test_fail_store_breaks_five_of_six(fail_store):
    _, row = fail_store
    assert row["robots_ai"] == "fail" and "ChatGPT-User" in row["notes"]
    assert row["product_text_html"] == "fail"      # text only appears after JS runs
    assert row["price_html"] == "fail"             # price only in a script
    assert row["schema_complete"] == "fail" and "brand" in row["notes"] and "identifier" in row["notes"]
    assert row["category_lists_5"] == "fail"       # 2 links in HTML, the rest by JS
    assert row["served_unfamiliar"] == "pass"
    assert row["schema_shipping"] == "no"


def test_blocked_store_fails_served_and_judges_nothing_else(blocked_store):
    _, row = blocked_store
    assert row["served_unfamiliar"] == "fail" and "HTTP 403" in row["notes"]
    for c in ("product_text_html", "price_html", "schema_complete"):
        assert row[c] == "could-not-judge"
    assert row["robots_ai"] == "pass"
