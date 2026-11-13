"""Run the six checks on one store's frozen target URLs and return a result row."""
from datetime import datetime, timezone

from . import checks as C


def run_store(sess, store, product_url, category_url):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {"store": store, "product_url": product_url or "", "category_url": category_url or "",
           "timestamp_utc": ts}
    notes = []
    robots_status, rp, _ = sess.robots(product_url or store)
    row["robots_ai"], n = C.check_robots_ai(robots_status, rp, product_url)
    notes.append("a:" + n)

    prod = None
    if not product_url:
        notes.append("no product page found")
    elif sess.allowed_for_me(product_url) is not True:
        notes.append("robots.txt disallows this kit's UA on product page; not fetched")
    else:
        prod = sess.get(product_url)
    fetched = bool(product_url) and sess.allowed_for_me(product_url) is True
    if fetched:
        row["served_unfamiliar"], n = C.check_served(prod)
    else:
        row["served_unfamiliar"], n = C.CNJ, "not fetched"
    notes.append("f:" + n)

    row["product_text_html"], n = C.check_product_text(prod); notes.append("b:" + n)
    row["price_html"], n = C.check_price(prod); notes.append("c:" + n)
    row["schema_complete"], n, ship = C.check_schema(prod); notes.append("d:" + n)
    row["schema_shipping"] = "n/a" if ship is None else ("yes" if ship else "no")

    cat = None
    if category_url and sess.allowed_for_me(category_url) is True:
        cat = sess.get(category_url)
    row["category_lists_5"], n = C.check_category(cat, product_url); notes.append("e:" + n)
    row["notes"] = " | ".join(notes)
    return row


CHECK_COLUMNS = ["robots_ai", "product_text_html", "price_html", "schema_complete",
                 "category_lists_5", "served_unfamiliar"]
