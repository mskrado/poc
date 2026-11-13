"""Find one product page and one category page from the homepage (sitemap fallback for products)."""
import re
import time
from urllib.parse import urljoin, urlsplit

from .checks import PRODUCT_LINK_RE, is_challenge, soup_of

CATEGORY_RE = re.compile(r"(/collections/(?!all/?$|vendors|types)[^/?#]+/?$|/product-category/|/c/|/category/|/categories/|/shop/[^/?#]+/?$|/browse/category|/w/[^/?#]+|/(women|men|mens|womens|clothing|new-arrivals|tops|shirts|dresses)(/|$|\.html))", re.I)


def _same_host(u, base):
    return urlsplit(u).netloc.replace("www.", "") == urlsplit(base).netloc.replace("www.", "")


def links(html, base):
    out = []
    for a in soup_of(html).find_all("a", href=True):
        u = urljoin(base, a["href"]).split("#")[0]
        if u.startswith("http") and _same_host(u, base) and u not in out:
            out.append(u)
    return out


SKIP_RE = re.compile(r"gift|e-?card|/(mens|womens|men|women|kids|youth|all|sale)/?$", re.I)


def _is_product_path(path):
    return bool(PRODUCT_LINK_RE.search(path)) and not SKIP_RE.search(path)


def pick_product(urls):
    for u in urls:
        if _is_product_path(urlsplit(u).path):
            return u
    return None


STRONG_CATEGORY_RE = re.compile(r"(/collections/|/product-category/|/c/|/category/|/categories/|/w/|/browse/category|/shop/)", re.I)


def pick_category(urls):
    """First homepage link that looks like a category; platform category paths beat keyword paths."""
    ok = [u for u in urls if CATEGORY_RE.search(urlsplit(u).path)
          and not PRODUCT_LINK_RE.search(urlsplit(u).path) and "gift" not in u.lower()]
    strong = [u for u in ok if STRONG_CATEGORY_RE.search(urlsplit(u).path)]
    return (strong or ok or [None])[0]


def _locs(text):
    return re.findall(r"<loc>\s*(?:<!\[CDATA\[)?\s*([^<\s\]]+)", text)


def product_from_sitemap(sess, base, robots_text, budget=3):
    """Walk at most `budget` sitemap files: prefer sitemaps named like products, take the first
    product-looking URL (or, inside a product sitemap, the first URL with a 2+ segment path)."""
    maps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_text or "") or [urljoin(base, "/sitemap.xml")]
    queue = sorted(maps, key=lambda m: 0 if re.search(r"product|pdp", m, re.I) else 1)
    seen = 0
    while queue and seen < budget:
        sm = queue.pop(0)
        if sess.allowed_for_me(sm) is not True:
            continue
        r = sess.get(sm)
        seen += 1
        if r is None or r.status_code != 200:
            continue
        locs = _locs(r.text)
        pages = [l for l in locs if ".xml" not in l.lower()]
        child = [l for l in locs if ".xml" in l.lower()]
        for l in pages:
            if _is_product_path(urlsplit(l).path):
                return l
        if re.search(r"product|pdp", sm, re.I):
            deep = [l for l in pages if len([x for x in urlsplit(l).path.split("/") if x]) >= 2 and not SKIP_RE.search(l)]
            if deep:
                return deep[0]
        child.sort(key=lambda m: 0 if re.search(r"product|pdp", m, re.I) else 1)
        queue = child + queue
    return None


def discover(sess, home_url):
    """Return dict with product_url, category_url, home_status, method."""
    info = {"product_url": None, "category_url": None, "home_status": None, "method": ""}
    status, rp, robots_text = sess.robots(home_url)
    info["robots_status"] = status
    mine = sess.allowed_for_me(home_url)
    if mine is not True:
        info["method"] = ("robots.txt disallows this kit's UA on homepage" if mine is False
                          else "robots.txt unreadable (error, 5xx, 401/403/429 or HTML), so the kit does not crawl")
        return info
    r = sess.get(home_url)
    if r is not None and r.status_code == 429:
        time.sleep(10)
        r = sess.get(home_url)
    info["home_status"] = None if r is None else r.status_code
    info["home_challenge"] = bool(r is not None and r.status_code == 200 and is_challenge(r))
    urls = links(r.text, r.url) if (r is not None and r.status_code == 200) else []
    info["home_links"] = len(urls)
    info["product_url"] = pick_product(urls)
    info["category_url"] = pick_category(urls)
    info["method"] = "homepage links"
    if not info["product_url"]:
        info["product_url"] = product_from_sitemap(sess, home_url, robots_text)
        if info["product_url"]:
            info["method"] = "product from sitemap"
    return info
