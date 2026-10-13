"""Deterministic checks and parsers. These are code, not scores."""
from __future__ import annotations

import re

# --- error-string scanner -------------------------------------------------
# A plain regex over text entering the prompt. It catches KNOWN error shapes.
# It does not check whether any claim in the answer is true.
ERROR_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r"\bERROR\b",
    r"\b(?:HTTP\s*)?[45]\d\d\b[^\n]{0,40}(?:Error|Unavailable|Timeout|Gateway|Required|Not Found|Forbidden)",
    r"\b(?:timeout|timed out)\b",
    r"\bException\b|\bHTTPError\b",
    r"\bnot found\b",
]
_ERR = re.compile("|".join(ERROR_PATTERNS), re.IGNORECASE)


def error_scanner(text: str) -> bool:
    return bool(_ERR.search(text or ""))


# --- chat-prose parsers -----------------------------------------------------
def parse_category(text: str, categories: list[str]) -> str:
    t = text or ""
    names = "|".join(categories)
    m = re.search(rf"categor\w*[^A-Za-z\n]{{0,12}}\**\s*({names})\b", t, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    hits = [(mm.start(), mm.group(1).upper()) for mm in re.finditer(rf"\b({names})\b", t, re.IGNORECASE)]
    return min(hits)[1] if hits else ""


def parse_intent(text: str, intents: list[str]) -> str:
    t = (text or "").lower()
    pats = {i: re.compile(r"\b" + re.escape(i).replace("_", r"[_ ]") + r"\b") for i in intents}
    m = re.search(r"intent[^\n]{0,80}", t)
    if m:
        seg = m.group(0)
        hits = [(p.search(seg).start(), i) for i, p in pats.items() if p.search(seg)]
        if hits:
            return min(hits)[1]
    hits = [(p.search(t).start(), i) for i, p in pats.items() if p.search(t)]
    return min(hits)[1] if hits else ""


_ROUTE_WORDS = {
    "small_model": r"small[_ ]model",
    "frontier": r"frontier(?:[_ ]model)?",
    "human": r"\bhuman(?:[_ ]agent)?\b",
}


def parse_route(text: str) -> str:
    t = (text or "").lower()
    m = re.search(r"handler[^\n]{0,80}", t)
    for seg in ([m.group(0)] if m else []) + [t]:
        hits = [(re.search(p, seg).start(), k) for k, p in _ROUTE_WORDS.items() if re.search(p, seg)]
        if hits:
            return min(hits)[1]
    return ""


def parse_agent_action(text: str) -> str:
    t = (text or "").strip().upper()
    for k in ("ESCALATE", "ANSWER", "RETRY"):
        if t.startswith(k):
            return k
    for k in ("ESCALATE", "RETRY", "ANSWER"):
        if k in t:
            return k
    return "RETRY"  # an unparseable reply is treated as "keep going", like most naive harnesses


def matches(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text or "", re.IGNORECASE))
