"""Strip likely-PHI keys from arbitrary inbound payloads before persistence.

Conservative match: any key whose lowercased name *contains* one of the
sensitive substrings is removed. Recurses into nested dicts and lists.
Non-dict inputs are returned unchanged so callers can pass freely.
"""

from __future__ import annotations

from typing import Any

_SENSITIVE_SUBSTRINGS = (
    "ssn",
    "dob",
    "date_of_birth",
    "insurance",
    "medical_record",
    "mrn",
)


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in _SENSITIVE_SUBSTRINGS)


def scrub_phi(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: scrub_phi(v) for k, v in value.items() if not _is_sensitive(k)}
    if isinstance(value, list):
        return [scrub_phi(v) for v in value]
    return value
