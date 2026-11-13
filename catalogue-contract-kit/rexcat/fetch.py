"""Polite fetcher: honest User-Agent, obeys robots.txt for its own UA, max 1 request/sec per host."""
import time
from urllib.parse import urlsplit

import requests
from protego import Protego

KIT_UA = ("RexCatalogueKit/0.1 (+https://roiscale.ai; Builder Lab catalogue contract tests; "
          "honest crawler, obeys robots.txt, 1 req/s)")
KIT_UA_TOKEN = "RexCatalogueKit"


class PoliteSession:
    def __init__(self, min_interval=1.0, timeout=20, ua=KIT_UA):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": ua,
                               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                               "Accept-Language": "en-US,en;q=0.8"})
        self.min_interval = min_interval
        self.timeout = timeout
        self._last = {}
        self._robots = {}
        self.log = []  # (url, status or error)

    def _wait(self, host):
        last = self._last.get(host)
        if last is not None:
            gap = time.monotonic() - last
            if gap < self.min_interval:
                time.sleep(self.min_interval - gap)
        self._last[host] = time.monotonic()

    def get(self, url):
        host = urlsplit(url).netloc
        self._wait(host)
        try:
            r = self.s.get(url, timeout=self.timeout, allow_redirects=True)
            self.log.append((url, r.status_code))
            return r
        except requests.RequestException as e:
            self.log.append((url, f"error:{type(e).__name__}"))
            return None

    def robots(self, base):
        """Return (status, Protego or None, raw text). status: 'ok', 'missing' (4xx = allow all), 'unreadable'."""
        root = f"{urlsplit(base).scheme}://{urlsplit(base).netloc}"
        if root in self._robots:
            return self._robots[root]
        r = self.get(root + "/robots.txt")
        if r is None or r.status_code >= 500:
            res = ("unreadable", None, "")
        elif r.status_code in (404, 410):
            res = ("missing", Protego.parse(""), "")
        elif r.status_code != 200:
            res = ("unreadable", None, "")
        else:
            ctype = r.headers.get("content-type", "")
            text = r.text
            if "html" in ctype.lower() and "<html" in text[:500].lower():
                res = ("unreadable", None, "")   # an HTML challenge page is not a robots file
            else:
                res = ("ok", Protego.parse(text), text)
        self._robots[root] = res
        return res

    def allowed_for_me(self, url):
        status, rp, _ = self.robots(url)
        if rp is None:
            return None
        return rp.can_fetch(url, KIT_UA_TOKEN)
