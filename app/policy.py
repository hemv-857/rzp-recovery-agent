"""Policy engine: the single gate every customer-facing action must pass.

Pure functions over (case, proposed_time, config). No IO — fully unit-testable.
Outcomes: EXECUTE now | DEFER to a concrete future time | BLOCK permanently.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .models import CaseStatus, Decision, Group, RecoveryCase

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc


@dataclass
class PolicyDecision:
    decision: Decision
    reason: str
    execute_at: datetime | None = None      # set when DEFER
    context: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "execute_at": self.execute_at.isoformat() if self.execute_at else None,
        }


def _in_quiet_hours(local_hour_float: float, window: tuple[int, int]) -> bool:
    start_h, end_h = window
    if start_h <= end_h:
        return start_h <= local_hour_float < end_h
    return local_hour_float >= start_h or local_hour_float < end_h   # wraps midnight


def next_quiet_hours_open(proposed: datetime, window: tuple[int, int]) -> datetime:
    """Earliest UTC instant at/after `proposed` outside the quiet window (IST)."""
    local = proposed.astimezone(IST)
    h = local.hour + local.minute / 60 + local.second / 3600
    if not _in_quiet_hours(h, window):
        return proposed
    _, end_h = window
    day_start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    open_today = day_start + timedelta(hours=end_h)
    if local < open_today:                       # early morning inside a wrapping window
        return open_today.astimezone(UTC)
    return (day_start + timedelta(days=1, hours=end_h)).astimezone(UTC)


def evaluate(
    case: RecoveryCase,
    proposed: datetime,
    cfg: dict[str, Any],
    action_is_contact: bool = True,
    money_action: bool = False,
    now: datetime | None = None,
) -> PolicyDecision:
    p = cfg["policy"]
    now = now or proposed

    if case.status in (CaseStatus.RECOVERED, CaseStatus.WRITTEN_OFF):
        return PolicyDecision(Decision.BLOCK, f"case_{case.status.value}")

    if case.customer.opted_out:
        return PolicyDecision(Decision.BLOCK, "customer_opted_out")

    # cap bounds AUTOMATED MONEY MOVEMENT only; reminders/escalation routing
    # are low-risk and must not strand high-value receivables
    if (
        money_action
        and case.amount > p["auto_action_cap_paise"]
        and not case.approved_human
    ):
        return PolicyDecision(
            Decision.DEFER, "above_auto_action_cap_needs_human_approval",
            context={"requires": "human_approval"},
        )

    if case.attempts_in_window(p["attempt_window_hours"], now) >= p["max_attempts_per_case"]:
        return PolicyDecision(
            Decision.BLOCK, "attempt_cap_reached",
            context={"attempts": len(case.attempt_times), "cap": p["max_attempts_per_case"]},
        )

    if case.attempt_times:
        last = max(datetime.fromisoformat(t) for t in case.attempt_times)
        cooldown_end = last + timedelta(minutes=p["cooldown_minutes"])
        if proposed < cooldown_end:
            return PolicyDecision(
                Decision.DEFER, "cooldown", execute_at=cooldown_end,
                context={"cooldown_minutes": p["cooldown_minutes"]},
            )

    horizon_end = datetime.fromisoformat(case.created_at) + timedelta(hours=p["case_expiry_hours"])
    if proposed >= horizon_end:
        return PolicyDecision(Decision.BLOCK, "past_case_expiry")

    if action_is_contact:
        opened = next_quiet_hours_open(proposed, tuple(p["quiet_hours_ist"]))
        if opened != proposed:
            return PolicyDecision(
                Decision.DEFER, "quiet_hours_ist", execute_at=opened,
                context={"quiet_window_ist": p["quiet_hours_ist"]},
            )

    return PolicyDecision(Decision.EXECUTE, "policy_clear")


def economic_stop(
    case: RecoveryCase,
    predicted_recovery_prob: float,
    action_cost_paise: int = 500,       # ~₹5 per action (channel cost + nuisance)
    multiplier: float = 3.0,             # expected recovery >= multiplier * cost
) -> bool:
    """Return True if the action is not economically worth executing.

    Recoup-style: stop chasing when expected_recovery < multiplier * action_cost.
    This prevents value-destroying recovery attempts on small subscriptions
    where the human/collection time costs more than the revenue.
    """
    expected_recovery = predicted_recovery_prob * case.amount
    return expected_recovery < multiplier * action_cost_paise


def should_write_off(case: RecoveryCase, now: datetime, cfg: dict[str, Any]) -> bool:
    created = datetime.fromisoformat(case.created_at)
    final_window = timedelta(hours=cfg["policy"]["final_followup_hours"])
    if now - created < final_window:
        return False
    if case.group is Group.CONTROL:
        return True
    gate = evaluate(case, now, cfg, action_is_contact=False, now=now)
    return gate.decision is Decision.BLOCK
