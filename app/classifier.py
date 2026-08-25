"""Failure classifier: Razorpay error codes/descriptions -> normalized FailureClass.

Deterministic rule table first; optional LLM fallback only for UNKNOWN text.
Every classification carries a confidence so downstream policy can be conservative.

Upgrade path: when Razorpay exposes Vulcan-derived failure signals (foundation
model announced Aug 2026; no public merchant API yet), this module is the single
swap point — see FUTURE_ROADMAP.md. Callers and confidence handling stay put.
The adapter is already wired: app/classifier_vulcan.py activates when
VULCAN_API_URL is set and degrades silently to these rules otherwise.
"""
from __future__ import annotations

from .classifier_vulcan import vulcan_classify
from .llm import chat_json
from .models import FailureClass

# code/description keywords, checked in order
_RULES: list[tuple[tuple[str, ...], FailureClass, float]] = [
    (("insufficient_funds", "insufficient funds", "no balance", "low balance"),
     FailureClass.INSUFFICIENT_FUNDS, 0.95),
    (("mandate_revoked", "mandate paused", "mandate expired", "emandate",
      "nach", "auto debit disabled", "subscription revoked"),
     FailureClass.MANDATE_ISSUE, 0.9),
    (("checkout_abandoned", "drop_off", "dropped off", "abandoned"),
     FailureClass.CUSTOMER_ABANDONMENT, 0.9),
    (("invoice_overdue", "overdue invoice", "receivable", "payment terms"),
     FailureClass.INVOICE_OVERDUE, 0.92),
    (("recurring_failed", "subscription_charge_failed", "auto debit failed",
      "renewal failed"),
     FailureClass.SUBSCRIPTION_FAILED, 0.88),
    (("authentication_failed", "authentication unavailable", "3ds", "otp"),
     FailureClass.SOFT_DECLINE_OTHER, 0.75),
    (("stolen_card", "card_stolen", "lost_card", "blocked_card", "card_blocked",
      "fraud", "do_not_honor", "do not honor", "restricted card"),
     FailureClass.HARD_DECLINE, 0.92),
    (("issuer_unavailable", "issuer unavailable", "issuer_timeout"),
     FailureClass.ISSUER_UNAVAILABLE, 0.85),
    (("timeout", "timed out", "network_error", "network error", "connection"),
     FailureClass.NETWORK_TIMEOUT, 0.8),
    (("card_declined", "payment_declined", "declined by bank"),
     FailureClass.SOFT_DECLINE_OTHER, 0.6),
    (("gateway_error", "gateway_error", "acquirer"),
     FailureClass.ISSUER_UNAVAILABLE, 0.7),
]

_SYSTEM = (
    "You classify failed payment reasons for an Indian payments platform. "
    "Reply with JSON: {\"failure_class\": one of INSUFFICIENT_FUNDS, NETWORK_TIMEOUT, "
    "ISSUER_UNAVAILABLE, SOFT_DECLINE_OTHER, HARD_DECLINE, MANDATE_ISSUE, UNKNOWN, "
    "\"confidence\": 0-1}. HARD_DECLINE means the instrument itself is blocked/fraud-flagged."
)


def classify(raw_code: str, description: str, method: str = "") -> tuple[FailureClass, float]:
    upstream = vulcan_classify(raw_code, description, method)
    if upstream is not None:
        return upstream
    text = f"{raw_code} {description}".lower().strip()
    for needles, cls, conf in _RULES:
        if any(n in text for n in needles):
            return cls, conf
    llm = chat_json(_SYSTEM, f"code={raw_code!r} description={description!r} method={method!r}")
    if llm and llm.get("failure_class") in FailureClass.__members__:
        return FailureClass(llm["failure_class"]), float(llm.get("confidence", 0.5))
    return FailureClass.UNKNOWN, 0.2
