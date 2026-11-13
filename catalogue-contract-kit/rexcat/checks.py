"""Six catalogue checks, modelled on the xfix AI Shopping Readiness Index definitions.
Each check returns ('pass'|'fail'|'could-not-judge', note)."""
import json
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

PASS, FAIL, CNJ = "pass", "fail", "could-not-judge"
AI_AGENTS = ["OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "PerplexityBot"]

CHALLENGE_MARKERS = ["cf-chl", "challenge-platform", "just a moment...", "attention required",
                     "px-captcha", "captcha-delivery", "_incapsula_resource", "access denied",
                     "are you a robot", "one moment, please", "request unsuccessful", "pardon our interruption"]

PRICE_RE = re.compile(
    r"(?:[$£€¥₹]|US\$|A\$|C\$|CA\$|AU\$|NZ\$|HK\$|kr|zł|CHF|KM|USD|GBP|EUR|AUD|CAD|BAM)\s?\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?"
    r"|\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?\s?(?:[$£€]|USD|GBP|EUR|AUD|CAD|kr|zł|CHF|KM|BAM)")

PRODUCT_LINK_RE = re.compile(r"(/products?/[^/?#]+|/p/[^?#]+|/prd/|product\.do|/dp/|-p\d{4,}\.html|/pd/|/item/|productpage\.\d+|/t/[^/?#]+/[^/?#]+|/[A-Z]{1,2}\d{4,}[A-Z0-9]*\.html)")


def soup_of(html):
    return BeautifulSoup(html or "", "html.parser")


def visible_text(soup):
    s = BeautifulSoup(str(soup), "html.parser")
    for t in s(["script", "style", "noscript", "template", "svg"]):
        t.decompose()
    return re.sub(r"\s+", " ", s.get_text(" ")).strip()


def is_challenge(resp):
    if resp is None:
        return True
    if resp.headers.get("cf-mitigated") == "challenge":
        return True
    # challenge/deny pages are small; a full product page can mention "captcha" in a script
    return len(resp.text) < 60000 and any(m in resp.text.lower() for m in CHALLENGE_MARKERS)


# (a) robots.txt allows the five AI agents on the product page
def check_robots_ai(robots_status, rp, product_url):
    if robots_status == "unreadable" or rp is None or not product_url:
        return CNJ, "robots.txt unreadable or no product page found"
    blocked = [a for a in AI_AGENTS if not rp.can_fetch(product_url, a)]
    if blocked:
        return FAIL, "disallowed: " + ",".join(blocked)
    return PASS, "missing robots.txt (allow all)" if robots_status == "missing" else "all five allowed"


# (f) product page served to an unfamiliar crawler (this kit's honest UA)
def check_served(resp):
    if resp is None:
        return CNJ, "no answer (network error/timeout)"
    if resp.status_code != 200:
        return FAIL, f"HTTP {resp.status_code}"
    if is_challenge(resp):
        return FAIL, "challenge page"
    return PASS, "HTTP 200"


def _page_ok(resp):
    return resp is not None and resp.status_code == 200 and not is_challenge(resp)


def jsonld_nodes(soup):
    """All JSON-LD objects in the raw HTML, flattened through @graph and lists."""
    out, bad = [], 0
    for tag in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = (tag.string or tag.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except ValueError:
            try:
                data = json.loads(re.sub(r"[\x00-\x1f]", " ", raw))
            except ValueError:
                bad += 1
                continue
        stack = [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
            elif isinstance(d, dict):
                out.append(d)
                if "@graph" in d:
                    stack.append(d["@graph"])
    return out, bad


def _types(node):
    t = node.get("@type", [])
    return [x.split("/")[-1] for x in (t if isinstance(t, list) else [t]) if isinstance(x, str)]


def _as_list(x):
    return x if isinstance(x, list) else ([] if x is None else [x])


def product_nodes(soup):
    nodes, bad = jsonld_nodes(soup)
    prods = [n for n in nodes if set(_types(n)) & {"Product", "ProductGroup", "IndividualProduct"}]
    return prods, bad


def _offer_fields(prod):
    price = avail = ship = False
    for off in _as_list(prod.get("offers")):
        if not isinstance(off, dict):
            continue
        offs = [off] + [o for o in _as_list(off.get("offers")) if isinstance(o, dict)]  # AggregateOffer.offers
        for o in offs:
            spec = [s for s in _as_list(o.get("priceSpecification")) if isinstance(s, dict)]
            if o.get("price") not in (None, "") or o.get("lowPrice") not in (None, "") or any(s.get("price") not in (None, "") for s in spec):
                price = True
            if o.get("availability"):
                avail = True
            if o.get("shippingDetails"):
                ship = True
    return price, avail, ship


def schema_fields(prod):
    """Field presence for one Product/ProductGroup node, looking into hasVariant for groups."""
    variants = [v for v in _as_list(prod.get("hasVariant")) if isinstance(v, dict)]
    candidates = [prod] + variants
    f = {"price": False, "availability": False, "brand": False, "identifier": False, "shipping": False}
    for c in candidates:
        p, a, s = _offer_fields(c)
        f["price"] |= p
        f["availability"] |= a
        f["shipping"] |= s
        b = c.get("brand")
        if (isinstance(b, dict) and (b.get("name") or "").strip()) or (isinstance(b, str) and b.strip()):
            f["brand"] = True
        # GTIN or SKU on the Product, or on one of its Offers (schema.org allows both)
        holders = [c] + [o for o in _as_list(c.get("offers")) if isinstance(o, dict)]
        for h in holders:
            if any(str(h.get(k) or "").strip() for k in ("gtin", "gtin8", "gtin12", "gtin13", "gtin14", "sku")):
                f["identifier"] = True
    return f


# (d) schema.org Product/Offer JSON-LD complete: price, availability, brand, identifier (+ shipping recorded)
def check_schema(resp):
    if not _page_ok(resp):
        return CNJ, "product page not served", None
    prods, bad = product_nodes(soup_of(resp.text))
    if not prods:
        return FAIL, "no Product JSON-LD" + (f" ({bad} block(s) failed to parse)" if bad else ""), False
    best = None
    for p in prods:
        f = schema_fields(p)
        if best is None or sum(f.values()) > sum(best.values()):
            best = f
    missing = [k for k in ("price", "availability", "brand", "identifier") if not best[k]]
    if missing:
        return FAIL, "missing: " + ",".join(missing), best["shipping"]
    return PASS, "price,availability,brand,identifier present", best["shipping"]


def product_name(soup):
    prods, _ = product_nodes(soup)
    for p in prods:
        if isinstance(p.get("name"), str) and p["name"].strip():
            return p["name"].strip()
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"].strip()
    return None


# (b) product text present in raw HTML, no JavaScript
def check_product_text(resp):
    if not _page_ok(resp):
        return CNJ, "product page not served"
    soup = soup_of(resp.text)
    text = visible_text(soup)
    h1 = soup.find("h1")
    h1t = re.sub(r"\s+", " ", h1.get_text(" ")).strip() if h1 else ""
    name = product_name(soup)
    words = len(text.split())
    name_seen = bool(name) and name.split("|")[0].split(" – ")[0].strip()[:40].lower() in text.lower()
    if (len(h1t) >= 3 or name_seen) and words >= 50:
        return PASS, f"h1/name in HTML, {words} visible words"
    return FAIL, f"h1={'yes' if h1t else 'no'}, name_in_text={'yes' if name_seen else 'no'}, {words} visible words"


# (c) visible price present in raw HTML, no JavaScript
def check_price(resp):
    if not _page_ok(resp):
        return CNJ, "product page not served"
    m = PRICE_RE.search(visible_text(soup_of(resp.text)))
    if m:
        return PASS, f"found '{m.group(0).strip()}'"
    return FAIL, "no currency amount in visible HTML text"


def product_links(html, base_url, product_url=None):
    soup = soup_of(html)
    host = urlsplit(base_url).netloc.replace("www.", "")
    shape = None
    if product_url:
        segs = [s for s in urlsplit(product_url).path.split("/") if s]
        if len(segs) >= 2:
            shape = "/" + "/".join(segs[:-1]) + "/"
    found = set()
    for a in soup.find_all("a", href=True):
        u = urljoin(base_url, a["href"]).split("#")[0]
        sp = urlsplit(u)
        if sp.netloc.replace("www.", "") != host:
            continue
        if PRODUCT_LINK_RE.search(sp.path) or (shape and sp.path.startswith(shape) and sp.path != shape):
            found.add(sp.path.rstrip("/"))
    return found


# (e) category page lists >= 5 products in HTML
def check_category(resp, product_url=None):
    if resp is None:
        return CNJ, "no category page found or no answer"
    if not _page_ok(resp):
        return CNJ, f"category page not served (HTTP {resp.status_code})"
    n = len(product_links(resp.text, resp.url, product_url))
    if n >= 5:
        return PASS, f"{n} product links"
    return FAIL, f"{n} product links"
