"""Rough token-count estimation for comparing JSON vs TOON size.

This is a heuristic (word/number runs + individual punctuation characters
count as one token each) — it approximates how BPE tokenizers typically
split text, but it is NOT the exact tokenizer for any specific model. Good
enough for an at-a-glance size comparison, not for billing calculations.
"""

import re

_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def estimate_tokens(text):
    return len(_TOKEN_RE.findall(text))


def compare(json_text, toon_text):
    json_tokens = estimate_tokens(json_text)
    toon_tokens = estimate_tokens(toon_text)
    savings_pct = 0.0
    if json_tokens > 0:
        savings_pct = round((1 - toon_tokens / json_tokens) * 100, 1)
    return {
        "json_chars": len(json_text),
        "toon_chars": len(toon_text),
        "json_tokens": json_tokens,
        "toon_tokens": toon_tokens,
        "savings_pct": savings_pct,
    }
