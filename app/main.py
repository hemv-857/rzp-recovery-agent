"""FastAPI surface: Razorpay webhook receiver, human-in-the-loop approvals,
scheduler tick, and read-only audit/report endpoints."""
from __future__ import annotations

import os
import re
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agent import ingest_failure, mark_recovered, plan_and_schedule, write_off
from .executor import ChannelAdapter, VoiceProvider, execute_action
from .measure import build_report, fmt_rupees
from .models import (
    ActionType,
    AuditEvent,
    Customer,
    FailedPayment,
    Intervention,
)
from .promisetopay import Intent, parse_reply
from .ratelimit import RateLimiter, limit_from_env
from .razorpay_client import client

app = FastAPI(
    title="Razorpay Revenue Recovery Agent",
    version="0.2.0",
    description=(
        "Closes the loop from revenue at risk to *measured* money recovered: "
        "failure-aware strategy selection, a pure-function compliance gate in front "
        "of every action, promise-to-pay handling over inbound replies, human "
        "escalation as the terminal path, and incremental lift measured against a "
        "randomized control group. Browse these docs, then `GET /report` and "
        "`GET /audit/{case_id}` for live numbers and reasoning chains."
    ),
    openapi_tags=[
        {"name": "webhooks", "description": "Razorpay events in; signed payloads only"},
        {"name": "cases", "description": "Human-in-the-loop case operations"},
        {"name": "scheduler", "description": "Due-action execution (cron hits this)"},
        {"name": "inbound", "description": "Customer replies: STOP / paid / promises"},
        {"name": "reporting", "description": "Incremental-lift report and audit trails"},
        {"name": "tools", "description": "Merchant-facing estimates"},
    ],
)

_STATIC = Path(__file__).parent / "static"
if _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")


def _cfg() -> dict:
    # read at call time so RECOVERY_CONFIG/RECOVERY_DB can be set per-process
    return yaml.safe_load(Path(os.getenv("RECOVERY_CONFIG", "config.yaml")).read_text())


def _store():
    from .store import Store
    # multi-tenant: X-Merchant-Id header routes to recovery_<tenant>.db; each
    # tenant is a fully isolated SQLite file ("default" uses the base path).
    # Webhook senders that can't set headers land in "default", or deploy one
    # receiver per merchant account.
    base = Path(os.getenv("RECOVERY_DB", "recovery.db"))
    tid = re.sub(r"[^A-Za-z0-9_-]", "", _tenant.get())[:32]
    if not tid or tid == "default":
        return Store(base)
    return Store(base.with_name(f"{base.stem}_{tid}{base.suffix}"))


_tenant: ContextVar[str] = ContextVar("tenant", default="default")


@app.middleware("http")
async def tenant_routing(request: Request, call_next):
    raw = request.headers.get("X-Merchant-Id", "")
    _tenant.set(raw[:64])          # sanitized at use, never trusted raw
    return await call_next(request)


# registered last = outermost = rejects before any other work happens
_limiter = RateLimiter(limit_from_env())


@app.middleware("http")
async def rate_limiting(request: Request, call_next):
    ip = (request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
          or (request.client.host if request.client else "unknown"))
    allowed, retry_after = _limiter.check(ip)
    if not allowed:
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429,
                            headers={"Retry-After": str(retry_after)})
    return await call_next(request)


def _require_agent_token(x_agent_token: str = Header("")) -> None:
    """Shared-secret guard for operator endpoints (/tick, approvals, opt-outs).
    Set AGENT_API_TOKEN in production; unset = open, for local dev only."""
    expected = os.getenv("AGENT_API_TOKEN", "")
    if expected and x_agent_token != expected:
        raise HTTPException(401, "invalid or missing X-Agent-Token")


@app.post(
    "/webhooks/razorpay",
    tags=["webhooks"],
    responses={200: {"content": {"application/json": {"examples": {
        "ingested": {
            "summary": "payment.failed accepted",
            "value": {"status": "ingested", "case_id": "case_9f2a1c3d4e5b"},
        },
        "recovered": {
            "summary": "payment_link.paid confirms recovery (idempotent)",
            "value": {"status": "recovered", "case_id": "case_9f2a1c3d4e5b"},
        },
    }}}},
        400: {"description": "invalid webhook signature"},
    },
)
async def razorpay_webhook(
    request: Request, x_razorpay_signature: str = Header("")
) -> JSONResponse:
    body = await request.body()
    if client.webhook_secret and not client.verify_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="invalid signature")

    event = await request.json()
    etype: str = event.get("event", "")
    store = _store()
    cfg = _cfg()

    if etype == "payment.failed":
        p = event["payload"]["payment"]["entity"]
        fp = FailedPayment(
            payment_id=p["id"],
            order_id=p.get("order_id", ""),
            amount=p["amount"],
            method=p.get("method", "card"),
            raw_error_code=p.get("error_code", "") or "",
            error_description=p.get("error_description", "") or "",
            customer=Customer(
                customer_id=p.get("customer_id") or f"cust_{p['id'][-8:]}",
                name=(p.get("notes") or {}).get("name", ""),
                phone=(p.get("notes") or {}).get("phone", ""),
                email=(p.get("notes") or {}).get("email", ""),
            ),
            source="live_test_mode",
        )
        case = store.get_case_by_payment(fp.payment_id)
        if case is None:
            case = ingest_failure(fp, store, cfg)
            if case.amount > cfg["policy"]["auto_action_cap_paise"]:
                # money actions above the cap wait for a human — make sure one hears about it
                from .notifier import case_line, notify
                notify(f":rocket: recovery-agent — high-value case awaiting "
                       f"human approval: {case_line(case)}")
        plan_and_schedule(case, cfg, datetime.now(timezone.utc), store)
        return {"status": "ingested", "case_id": case.case_id}

    if etype == "payment_link.paid":
        pl = event["payload"]["payment_link"]["entity"]
        case = store.get_case_by_reference(pl.get("reference_id", ""))
        if not case:
            store.append_audit(AuditEvent(
                actor="webhook", event_type="ignored.payment_link_paid_no_case",
                payload={"reference_id": pl.get("reference_id", "")},
            ))
            return {"status": "no_matching_case"}
        # payment id lives in payload.payment.entity on current webhooks;
        # older shapes nest it under payment_link.entity.payments[]
        pay_ent = event.get("payload", {}).get("payment", {}).get("entity", {})
        payment_id = (
            pay_ent.get("id")
            or next(iter(pl.get("payments") or []), {})
        )
        if isinstance(payment_id, dict):
            payment_id = payment_id.get("id", "plink_paid")
        paid_at = event.get("created_at")
        mark_recovered(
            case, payment_id or "plink_paid", pl["amount"],
            datetime.fromtimestamp(paid_at, tz=timezone.utc).isoformat()
            if paid_at else datetime.now(timezone.utc).isoformat(),
            store, via="webhook",
        )
        return {"status": "recovered", "case_id": case.case_id}

    store.append_audit(AuditEvent(actor="webhook", event_type=f"ignored.{etype}",
                                  payload={"event": etype}))
    return {"status": f"ignored:{etype}"}


@app.post("/cases/{case_id}/approve", tags=["cases"])
def approve_case(case_id: str, x_agent_token: str = Header("")) -> dict:
    """Human approval for above-cap auto actions (audit-logged)."""
    _require_agent_token(x_agent_token)
    store = _store()
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(404, "case not found")
    case.approved_human = True
    case.touch()
    store.upsert_case(case)
    store.append_audit(AuditEvent(
        actor="human", event_type="case.approved", case_id=case_id,
        payload={"approved_by": "operator", "cap_override": True},
    ))
    return {"status": "approved", "case_id": case_id}


@app.post("/cases/{case_id}/opt_out", tags=["cases"])
def opt_out(case_id: str, x_agent_token: str = Header("")) -> dict:
    _require_agent_token(x_agent_token)
    store = _store()
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(404, "case not found")
    case.customer.opted_out = True
    case.touch()
    store.upsert_case(case)
    store.append_audit(AuditEvent(actor="human", event_type="customer.opted_out",
                                  case_id=case_id, payload={}))
    write_off(case, "customer_opted_out", store)
    return {"status": "opted_out", "case_id": case_id}


@app.post("/tick", tags=["scheduler"])
def tick(x_agent_token: str = Header("")) -> dict:
    """Run all due scheduled actions. In production a cron hits this every minute."""
    _require_agent_token(x_agent_token)
    now = datetime.now(timezone.utc)
    store = _store()
    cfg = _cfg()
    channels = ChannelAdapter()
    voice = VoiceProvider()
    ran = 0
    for action in store.due_actions(now.isoformat()):
        case = store.get_case(action.case_id)
        if not case or case.status.value in ("recovered", "written_off"):
            store.supersede_scheduled(action.case_id)   # don't leave stale scheduled rows
            continue
        execute_action(action, case, cfg, store, channels, now, voice=voice)
        ran += 1
    return {"executed": ran}


@app.post("/inbound/reply", tags=["inbound"])
async def inbound_reply(request: Request) -> dict:
    """Customer replies to a recovery SMS/WhatsApp (BSP webhook: {from, text}).

    Intents: STOP -> opt-out | PAID -> recover | 'kal'/'25 tarikh'/... ->
    promise-to-pay (pauses the ladder, schedules a check) | refuse -> close |
    anything else -> ignored but audited.
    """
    body = await request.json()
    text = str(body.get("text", ""))
    phone = str(body.get("from", body.get("wa_id", "")))
    parsed = parse_reply(text)

    store = _store()
    case = store.get_case_by_customer_phone(phone)
    if not case:
        return {"status": "no_active_case", "intent": parsed.intent.value}

    store.append_audit(AuditEvent(
        actor="customer", event_type="inbound.reply", case_id=case.case_id,
        payload={"text": text, "intent": parsed.intent.value,
                 "due": parsed.due.isoformat() if parsed.due else None},
    ))

    if parsed.intent is Intent.OPT_OUT:
        case.customer.opted_out = True
        case.touch()
        store.upsert_case(case)
        write_off(case, "customer_opted_out", store)
        return {"status": "opted_out"}

    if parsed.intent is Intent.ALREADY_PAID:
        mark_recovered(case, "manual_confirmation", case.amount,
                       datetime.now(timezone.utc).isoformat(), store,
                       via="customer_reply")
        return {"status": "recovered"}

    if parsed.intent is Intent.PROMISE:
        due_utc = parsed.due.astimezone(timezone.utc)
        case.promised_at = datetime.now(timezone.utc).isoformat()
        case.promise_due = due_utc.isoformat()
        case.touch()
        store.upsert_case(case)
        store.supersede_scheduled(case.case_id)     # pause dunning while promise active
        check_time = due_utc + timedelta(hours=6)   # grace before declaring it broken
        action = Intervention(
            case_id=case.case_id, action_type=ActionType.CHECK_PROMISE,
            scheduled_at=check_time.isoformat(),
            reasoning={"strategy": "promise_to_pay_followup",
                       "parsed_from": parsed.note},
        )
        store.save_action(action)
        store.append_audit(AuditEvent(
            actor="agent", event_type="promise.scheduled_check", case_id=case.case_id,
            payload={"due": case.promise_due, "check_at": check_time.isoformat()},
        ))
        return {"status": "promise_recorded", "due": case.promise_due}

    if parsed.intent is Intent.REFUSED:
        write_off(case, "customer_refused", store)
        return {"status": "closed_refused"}

    return {"status": "ignored", "intent": parsed.intent.value}


@app.get(
    "/audit/{case_id}",
    tags=["reporting"],
    responses={200: {"content": {"application/json": {"example": {
        "case_id": "case_9f2a1c3d4e5b",
        "events": [
            {"event_id": "evt_1", "ts": "2026-08-20T06:05:00+00:00",
             "actor": "classifier", "event_type": "case.created",
             "payment_id": "pay_x", "classified_as": "INSUFFICIENT_FUNDS",
             "confidence": 0.95, "group": "treatment"},
            {"event_id": "evt_2", "ts": "2026-08-20T06:05:00+00:00",
             "actor": "selector", "event_type": "action.scheduled",
             "strategy": "salary_cycle_retry",
             "why": "insufficient funds recover best near salary credit dates"},
            {"event_id": "evt_3", "ts": "2026-08-21T04:30:00+00:00",
             "actor": "policy", "event_type": "action.executed",
             "decision": "execute", "reason": "policy_clear"},
        ]}}},
        404: {"description": "case not found"},
    }},
)
def audit(case_id: str) -> dict:
    store = _store()
    if not store.get_case(case_id):
        raise HTTPException(404, "case not found")
    return {"case_id": case_id, "events": store.audit_for(case_id)}


@app.get("/report", tags=["reporting"])
def report() -> dict[str, Any]:
    store = _store()
    return build_report(store.all_cases(), store.actions_rows(), _cfg())


@app.get(
    "/calculator",
    tags=["tools"],
    responses={200: {"content": {"application/json": {"example": {
        "inputs": {"amount_at_risk_paise": 2000000000, "cases": 22222,
                   "baseline_recovery_pct": 20.0, "estimated_lift_pp": 50.0},
        "incremental_recovery_paise": 1000000000,
        "incremental_recovery_display": "₹1.00 Cr",
        "projected_contacts": 66666,
        "projected_contact_spend_paise": 1044434,
        "cost_per_incremental_recovery_paise": 94,
        "assumptions": {
            "median_case_amount": "₹900 (batch generator)",
            "cost_per_touch_source": "config.yaml channels.*.cost_paise",
            "note": "a share of treated recoveries would have happened anyway "
                    "(redundant-contact share); the control group absorbs this in "
                    "the measured report"},
    }}}},
        422: {"description": "amount <= 0 or lift outside 0..100"},
    },
)
def roi_calculator(
    amount_at_risk_cr: float,
    baseline_recovery_pct: float = 20.0,
    estimated_lift_pp: float = 50.0,
    cases: int | None = None,
) -> dict[str, Any]:
    """Merchant ROI estimate from config economics — no case data touched.

    Assumptions are stated, not hidden: `estimated_lift_pp` defaults to the
    batch-measured headline lift; contact cost is the mean of the enabled
    channel costs; touches per case bounded by the policy attempt cap.
    """
    if amount_at_risk_cr <= 0 or not (0 <= estimated_lift_pp <= 100):
        raise HTTPException(422, "amount must be > 0 and lift within 0..100")
    cfg = _cfg()
    p = cfg["policy"]
    paise = amount_at_risk_cr * 1e9
    n_cases = cases or max(int(paise / 90_000), 1)   # ~₹900 median failed payment

    incremental_paise = paise * estimated_lift_pp / 100
    incremental_recoveries = n_cases * estimated_lift_pp / 100

    ladder = [c for c in ("whatsapp", "sms", "email") if cfg["channels"][c]["enabled"]]
    cost_per_touch = sum(cfg["channels"][c]["cost_paise"] for c in ladder) / len(ladder)
    touches_per_case = p["max_attempts_per_case"]          # conservative upper bound
    spend_paise = n_cases * touches_per_case * cost_per_touch

    return {
        "inputs": {
            "amount_at_risk_paise": round(paise),
            "cases": n_cases,
            "baseline_recovery_pct": baseline_recovery_pct,
            "estimated_lift_pp": estimated_lift_pp,
        },
        "incremental_recovery_paise": round(incremental_paise),
        "incremental_recovery_display": fmt_rupees(incremental_paise),
        "projected_contacts": n_cases * touches_per_case,
        "projected_contact_spend_paise": round(spend_paise),
        "cost_per_incremental_recovery_paise": (
            round(spend_paise / incremental_recoveries) if incremental_recoveries > 0 else None
        ),
        "assumptions": {
            "median_case_amount": "₹900 (batch generator)",
            "cost_per_touch_source": "config.yaml channels.*.cost_paise",
            "note": "a share of treated recoveries would have happened anyway "
                    "(redundant-contact share); the control group absorbs this in "
                    "the measured report",
        },
    }


@app.get(
    "/cases/recent",
    tags=["reporting"],
    responses={200: {"content": {"application/json": {"example": {
        "cases": [{
            "case_id": "case_9f2a1c3d4e5b", "failure_class": "INVOICE_OVERDUE",
            "amount_paise": 16900000, "status": "written_off",
            "written_off_reason": "escalated_to_human_finance_ops",
            "recovered_amount_paise": 0}]}}}}},
)
def recent_cases(limit: int = 25) -> dict[str, Any]:
    """Latest cases (newest first) for the dashboard drill-down."""
    limit = max(1, min(limit, 100))
    store = _store()
    cases = sorted(store.all_cases(), key=lambda c: c.created_at)[-limit:][::-1]
    return {"cases": [{
        "case_id": c.case_id,
        "failure_class": c.failure_class.value,
        "amount_paise": c.amount,
        "status": c.status.value,
        "written_off_reason": c.written_off_reason,
        "recovered_amount_paise": c.recovered_amount,
    } for c in cases]}


@app.get("/", response_class=HTMLResponse, tags=["reporting"])
def dashboard() -> HTMLResponse:
    """Rich dashboard (Chart.js, vendored offline). Falls back to the
    dependency-free server-rendered report if the static bundle is missing."""
    index = _STATIC / "dashboard.html"
    if index.is_file():
        return HTMLResponse(index.read_text())
    store = _store()
    cases = store.all_cases()
    rep = build_report(cases, store.actions_rows(), _cfg())
    recent = sorted(cases, key=lambda c: c.created_at)[-25:][::-1]
    from .report_html import render_dashboard
    return HTMLResponse(render_dashboard(rep, recent_cases=recent))
