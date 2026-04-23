"""4-layer prompt joiner: style + character + page + scene (+ suffix)."""
from __future__ import annotations


def _clean(s: str) -> str:
    # strip whitespace + trailing commas that users/LLMs sometimes add
    return s.strip().rstrip(",").strip()


def _join(parts: list[str]) -> str:
    return ", ".join(p for p in (_clean(x) for x in parts) if p)


def build_prompt_pair(
    *,
    style: dict,
    character: dict,
    page: dict,
    scene: dict,
    positive_suffix: str = "",
    negative_suffix: str = "",
) -> tuple[str, str]:
    """Return (positive, negative) concatenated prompts.

    Each layer dict has "positive" and "negative" keys. Empty / whitespace-only
    layers are skipped. Parts are joined with ", ".
    """
    pos = _join([style["positive"], character["positive"], page["positive"],
                 scene["positive"], positive_suffix])
    neg = _join([style["negative"], character["negative"], page["negative"],
                 scene["negative"], negative_suffix])
    return pos, neg
