"""Optional Vulcan-backed classification provider.

Razorpay's Vulcan foundation model (announced Aug 18 2026) has no public
merchant API yet. This adapter implements an *assumed* contract, gated OFF by
default: set VULCAN_API_URL (+ optional VULCAN_API_KEY) and every classification
tries Vulcan first, degrading to the deterministic rule table on disable /
error / timeout / malformed response. The assumed request/response shape lives
in this one function, so adapting the real alpha contract is a one-file diff.

Assumed contract (documented guess, adjust when alpha lands):
    POST {url}  {"raw_error_code": ..., "error_description": ..., "method": ...}
    -> 200 {"failure_class": "<FailureClass member>", "confidence": 0..1}
"""
from __future__ import annotations

import os

import httpx

from .models import FailureClass


def _post(url: str, **kw) -> httpx.Response:
    return httpx.post(url, **kw)


def vulcan_classify(
    raw_code: str, description: str, method: str = ""
) -> tuple[FailureClass, float] | None:
    """(FailureClass, confidence) from Vulcan, or None = unavailable.

    None is the contract: callers fall through to deterministic rules without
    knowing why (disabled, slow, down, bad payload — all identical downstream).
    """
    url = os.getenv("VULCAN_API_URL", "")
    if not url:
        return None
    headers = {}
    if os.getenv("VULCAN_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['VULCAN_API_KEY']}"
    try:
        r = _post(url, json={
            "raw_error_code": raw_code,
            "error_description": description,
            "method": method,
        }, headers=headers, timeout=2)          # must fit inside a live tick loop
        data = r.json()
        cls = FailureClass(data["failure_class"])     # raises on unknown member
        conf = min(max(float(data["confidence"]), 0.0), 1.0)
        return cls, conf
    except Exception:
        return None
