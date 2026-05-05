"""Normalize messy user text about treatments into canonical keys used by
BookingRoute.normalized_treatment_key."""

from __future__ import annotations

import re
from typing import Iterable, Optional

# Canonical key -> list of lowercase substrings/aliases to match.
# Longest / most specific aliases first; short single words last.
TREATMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "laser_hair_removal": ("laser hair removal", "lhr", "hair removal", "laser hair"),
    "chemical_peel": ("chemical peel", "peel"),
    "microneedling": ("microneedling", "micro needling", "microneedle", "rf microneedling"),
    "hydrafacial": ("hydrafacial", "hydra facial", "hydra-facial"),
    "botox": ("botox", "dysport", "xeomin", "jeuveau", "tox"),
    "filler": (
        "filler",
        "fillers",
        "dermal filler",
        "lip filler",
        "cheek filler",
        "juvederm",
        "restylane",
    ),
    "consultation_general": (
        "consultation",
        "consult",
        "just looking",
        "not sure",
        "learn more",
        "info",
    ),
}


def normalize_treatment(text: Optional[str]) -> Optional[str]:
    """Return a canonical treatment key or None if nothing confident matched."""
    if not text:
        return None
    lower = text.lower().strip()
    if not lower:
        return None

    # Prefer the longest alias match across all treatments.
    best_key: Optional[str] = None
    best_len = 0
    for key, aliases in TREATMENT_ALIASES.items():
        for alias in aliases:
            if alias in lower and len(alias) > best_len:
                best_key = key
                best_len = len(alias)
    return best_key


def detect_treatment_keys(text: str) -> list[str]:
    """Return every matched canonical key (for analytics / extraction)."""
    lower = text.lower()
    keys: list[str] = []
    for key, aliases in TREATMENT_ALIASES.items():
        if any(a in lower for a in aliases):
            keys.append(key)
    return keys


_WORD_RE = re.compile(r"[a-z][a-z_]+")


def slugify_treatment_key(value: str) -> str:
    """Helper for admin UI — create a safe key when the user adds a treatment."""
    lower = value.lower().strip().replace("-", "_").replace(" ", "_")
    # Keep only alphanumeric + underscore
    return "_".join(_WORD_RE.findall(lower)) or "custom"
