"""Intervention selector: given a case + policy state, pick the NEXT single best
action and its schedule time. The agent loop re-plans after every outcome —
no fixed scripts, each step is reasoned from current state."""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .models import ActionType, FailureClass, Intervention, RecoveryCase
from .policy import economic_stop
from .promisetopay import PromiseTracker

IST = ZoneInfo("Asia/Kolkata")


def _salary_aligned_slot(cfg: dict, now: datetime) -> datetime:
    """Next 10:00 IST on/after the nearest salary-cycle day (e.g. 1st or 5th).
    Empty cycle config -> generic next-morning slot."""
    days = sorted(cfg["retry"].get("salary_cycle_days") or [])
    local = now.astimezone(IST)

    def slot(y: int, m: int, d: int) -> datetime:
        last = calendar.monthrange(y, m)[1]
        return datetime(y, m, min(d, last), 10, 0, tzinfo=IST)

    def morning(offset_days: int = 0) -> datetime:
        base = local + timedelta(days=offset_days)
        cand = base.replace(hour=10, minute=0, second=0, microsecond=0)
        return cand if cand > local else morning(offset_days + 1)

    if not days:
        return morning()
    y, m = local.year, local.month
    for d in days:
        cand = slot(y, m, d)
        if cand > local:
            return cand
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return slot(ny, nm, days[0])


def _contact_ladder(case: RecoveryCase, cfg: dict) -> ActionType:
    """Channel escalation by contact index: WhatsApp -> SMS -> email."""
    order = [
        (ActionType.NUDGE_WHATSAPP, "whatsapp"),
        (ActionType.NUDGE_SMS, "sms"),
        (ActionType.NUDGE_EMAIL, "email"),
    ]
    enabled = [c for c in order if cfg["channels"][c[1]]["enabled"]] or [order[2]]
    return enabled[min(len(case.attempt_times), len(enabled) - 1)][0]


def _mk(case: RecoveryCase, at: datetime, action_type: ActionType,
        reasoning: dict) -> Intervention:
    return Intervention(
        case_id=case.case_id,
        action_type=action_type,
        scheduled_at=at.astimezone(tz=IST).isoformat(),
        reasoning=reasoning,
    )


def _promise_adjusted_ev(case: RecoveryCase, base_ev: float) -> float:
    """Adjust expected value based on customer's promise-to-pay track record.
    
    Broken promises reduce EV by 50% (as in agastyasharma20's implementation).
    Kept promises increase confidence slightly.
    """
    if not case.promised_at:
        return base_ev
    
    tracker = PromiseTracker()
    # In real usage, we'd look up the customer's promise history
    # For now, we use the case's own promise state as a signal
    if case.promise_due:
        # This case has an active promise - trust it moderately
        return base_ev * 1.1
    # Check if this customer has broken promises in history
    # (would need cross-case lookup in store - simplified here)
    return base_ev * 0.5  # broken promise penalty


def select_next_action(
    case: RecoveryCase, cfg: dict, now: datetime
) -> Intervention | None:
    cls = case.failure_class
    contact_n = len(case.attempt_times)
    r = cfg["retry"]

    # Explicit NO_ACTION: evaluate all candidates, if max net EV <= 0, do nothing
    # Mirrors modiviveks' explicit NO_ACTION when all actions have negative EV
    from .recovery_model import predict_recovery
    from .policy import economic_stop

    candidates = [
        ActionType.RETRY_PAYMENT_LINK,
        ActionType.RETRY_CHARGE,
        ActionType.NUDGE_WHATSAPP,
        ActionType.NUDGE_SMS,
        ActionType.NUDGE_EMAIL,
        ActionType.NUDGE_VOICE,
        ActionType.ESCALATE_HUMAN,
    ]

    cost_map = {
        ActionType.RETRY_PAYMENT_LINK: 500,
        ActionType.RETRY_CHARGE: 200,
        ActionType.NUDGE_WHATSAPP: 800,
        ActionType.NUDGE_SMS: 300,
        ActionType.NUDGE_EMAIL: 100,
        ActionType.NUDGE_VOICE: 2000,
        ActionType.ESCALATE_HUMAN: 5000,
    }

    best_ev = -1
    best_action = None
    for act in candidates:
        pred = predict_recovery(case, act, contact_n, now.isoformat(), cfg)
        ev = pred.probability * case.amount
        cost = cost_map.get(act, 500)
        net_ev = ev - cost
        if net_ev > best_ev:
            best_ev = net_ev
            best_action = act

    if best_ev <= 0:
        return None  # Explicit NO_ACTION: all actions have negative net EV

    # Economic stopping rule (Recoup-style): stop when expected_recovery < 3x action_cost
    if economic_stop(case, predicted_recovery_prob=0.3):
        return None

    if cls is FailureClass.NETWORK_TIMEOUT:
        kind = (
            ActionType.RETRY_CHARGE
            if case.method in ("emandate", "nach") and case.subscription_id
            else ActionType.RETRY_PAYMENT_LINK
        )
        return _mk(case, now + timedelta(minutes=r["network_timeout_backoff_min"]), kind, {
            "strategy": "quick_transient_retry",
            "delay_min": r["network_timeout_backoff_min"],
            "why": "transient network failure recovers with short backoff",
        })

    if cls is FailureClass.ISSUER_UNAVAILABLE:
        return _mk(case, now + timedelta(minutes=r["issuer_unavailable_backoff_min"]),
                   ActionType.RETRY_CHARGE, {
            "strategy": "issuer_backoff_retry",
            "delay_min": r["issuer_unavailable_backoff_min"],
            "why": "bank/gateway temporarily unavailable; retry after backoff",
        })

    if cls is FailureClass.INSUFFICIENT_FUNDS:
        aligned = _salary_aligned_slot(cfg, now)
        soon = (aligned - now) <= timedelta(days=3)
        when = aligned if soon else now + timedelta(hours=2)
        return _mk(case, when, _contact_ladder(case, cfg), {
            "strategy": "salary_cycle_retry" if soon else "early_nudge_then_salary_retry",
            "salary_slot_ist": aligned.isoformat(),
            "why": "insufficient funds recover best near salary credit dates",
        })

    if cls is FailureClass.HARD_DECLINE:
        return _mk(case, now + timedelta(hours=1), _contact_ladder(case, cfg), {
            "strategy": "alternate_instrument",
            "why": "instrument blocked/fraud-flagged: never auto-retry same instrument, "
                   "offer UPI/alternate via link",
        })

    if cls is FailureClass.CARD_EXPIRED:
        return _mk(case, now + timedelta(hours=2), _contact_ladder(case, cfg), {
            "strategy": "card_update",
            "why": "expired card: prompt customer to update card details via payment link",
        })

    if cls is FailureClass.GATEWAY_TIMEOUT:
        return _mk(case, now + timedelta(minutes=r.get("gateway_timeout_backoff_min", 15)),
                   ActionType.RETRY_CHARGE, {
            "strategy": "gateway_retry",
            "why": "gateway timeout: retry charge after brief backoff",
        })

    if cls is FailureClass.PRICE_SHOCK:
        return _mk(case, now + timedelta(hours=4), _contact_ladder(case, cfg), {
            "strategy": "price_clarification",
            "why": "unexpected amount: clarify billing with customer, offer discount if applicable",
        })

    if cls is FailureClass.OVERDUE_GENUINE:
        return _mk(case, now + timedelta(hours=2), ActionType.NUDGE_VOICE, {
            "strategy": "genuine_overdue_voice",
            "why": "genuinely overdue receivable: Hinglish voice call + payment link",
        })

    if cls is FailureClass.MANDATE_ISSUE:
        return _mk(case, now + timedelta(hours=1), _contact_ladder(case, cfg), {
            "strategy": "mandate_reauth",
            "why": "auto-debit needs customer re-authorization before any charge",
        })

    if cls is FailureClass.CUSTOMER_ABANDONMENT:
        delays = [timedelta(hours=1), timedelta(hours=24), timedelta(days=3)]
        return _mk(case, now + delays[min(contact_n, 2)], _contact_ladder(case, cfg), {
            "strategy": "abandoned_checkout_recovery", "contact_index": contact_n,
            "why": "gentle reminder ladder for incomplete checkout intent",
        })

    if cls is FailureClass.INVOICE_OVERDUE:
        # B2B receivables: polite -> firm -> final notice -> human escalation
        # cadence sized to resolve inside the automated follow-up window
        if contact_n >= 3:
            return _mk(case, now + timedelta(hours=2), ActionType.ESCALATE_HUMAN, {
                "strategy": "receivables_escalation", "contact_index": contact_n,
                "why": "automated ladder exhausted; routing to finance ops for "
                       "relationship-aware follow-up (compliant escalation)",
            })
        stage_delays = [timedelta(hours=2), timedelta(days=1), timedelta(days=3)]
        # final notice on high-value receivables goes out as a Hinglish voice call
        if contact_n == 2 and case.amount >= cfg["retry"]["voice_min_amount_paise"]:
            action_type = ActionType.NUDGE_VOICE
        else:
            action_type = _contact_ladder(case, cfg)
        return _mk(case, now + stage_delays[contact_n], action_type, {
            "strategy": f"receivables_ladder_stage_{contact_n + 1}",
            "days_overdue": case.loss_age_days,
            "why": "B2B dunning etiquette: escalating tone with payment link at each stage"
                   + ("; high-value case earns a human-voice touch"
                      if action_type is ActionType.NUDGE_VOICE else ""),
        })

    if cls is FailureClass.SUBSCRIPTION_FAILED:
        if contact_n == 0:
            return _mk(case, now + timedelta(hours=6), ActionType.RETRY_CHARGE, {
                "strategy": "dunning_grace_retry",
                "why": "recurring charge often succeeds on re-presentment within grace window",
            })
        if contact_n == 1:
            return _mk(case, now + timedelta(hours=24), ActionType.NUDGE_WHATSAPP, {
                "strategy": "dunning_reauth",
                "why": "second failure usually means mandate/card issue; re-auth first",
            })
        return _mk(case, now + timedelta(days=2), ActionType.NUDGE_EMAIL, {
            "strategy": "dunning_retention_offer",
            "why": "offer pause/downgrade instead of churn; last automated touch",
        })

    if cls is FailureClass.LATE_AUTH:
        # Late auth: authorized but capture failed — retry charge immediately
        # (authorization window is time-limited, typically 24-72h)
        if contact_n == 0:
            return _mk(case, now + timedelta(minutes=30), ActionType.RETRY_CHARGE, {
                "strategy": "late_auth_capture",
                "why": "payment authorized but not captured; retry within auth window",
            })
        if contact_n == 1:
            return _mk(case, now + timedelta(hours=2), ActionType.NUDGE_WHATSAPP, {
                "strategy": "late_auth_reauth",
                "why": "capture failed twice; ask customer to re-authorize via payment link",
            })
        return _mk(case, now + timedelta(hours=6), ActionType.ESCALATE_HUMAN, {
            "strategy": "late_auth_escalation",
            "why": "auth window closing; human ops to coordinate with bank",
        })

    # UNKNOWN: most conservative — email only
    return _mk(case, now + timedelta(hours=4), ActionType.NUDGE_EMAIL, {
        "strategy": "conservative_unknown",
        "why": "unclassified failure: lowest-cost channel first, no auto charge",
    })
