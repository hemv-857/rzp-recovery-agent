"""
Razorpay webhook ingestion & payment link generation.
Foura: <12ms synchronous placeholder + background LLM diagnosis.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request

from .classifier import classify
from .currency import get_normalizer
from .llm_client import get_groq_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

# Razorpay webhook secret
WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "demo_secret")

# In-memory queue for background processing (replace with Redis/RQ in production)
_diagnosis_queue: list[dict] = []


@dataclass
class IngestedFailure:
    """Normalized failure from Razorpay webhook."""
    payment_id: str
    order_id: str
    amount_paise: int
    currency: str
    method: str
    error_code: str
    error_description: str
    customer_id: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    customer_name: str | None = None
    failed_at: datetime | None = None
    metadata: dict | None = None


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify Razorpay webhook signature."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_webhook(payload: dict) -> IngestedFailure | None:
    """Parse Razorpay payment.failed webhook payload."""
    try:
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        if not payment:
            return None

        # Extract error details
        error_code = payment.get("error_code", "unknown")
        error_desc = payment.get("error_description", "Payment failed")
        error_source = payment.get("error_source", "unknown")
        error_step = payment.get("error_step", "unknown")
        error_reason = payment.get("error_reason", "unknown")

        full_desc = (
            f"{error_desc} [{error_code}]"
            f" source:{error_source}"
            f" step:{error_step}"
            f" reason:{error_reason}"
        )

        # Extract customer info
        customer = payment.get("customer", {}) or {}

        return IngestedFailure(
            payment_id=payment.get("id", ""),
            order_id=payment.get("order_id", ""),
            amount_paise=payment.get("amount", 0),
            currency=payment.get("currency", "INR").upper(),
            method=payment.get("method", "unknown"),
            error_code=error_code,
            error_description=full_desc,
            customer_id=customer.get("id"),
            customer_email=customer.get("email"),
            customer_phone=customer.get("contact"),
            customer_name=customer.get("name"),
            failed_at=(
                datetime.fromtimestamp(
                    payment.get("created_at", 0), tz=timezone.utc
                )
                if payment.get("created_at")
                else None
            ),
            metadata=payment.get("notes"),
        )
    except Exception as e:
        logger.error(f"Failed to parse webhook: {e}")
        return None


def create_failure_context(failure: IngestedFailure) -> dict:
    """Build context dict for LLM diagnosis."""
    # Classify first (deterministic)
    fc, confidence = classify(failure.error_code, failure.error_description)

    return {
        "payment_id": failure.payment_id,
        "order_id": failure.order_id,
        "amount_paise": failure.amount_paise,
        "currency": failure.currency,
        "method": failure.method,
        "error_code": failure.error_code,
        "error_description": failure.error_description,
        "failure_class": fc.value,
        "class_confidence": confidence,
        "customer_id": failure.customer_id,
        "customer_email": failure.customer_email,
        "customer_phone": failure.customer_phone,
        "customer_name": failure.customer_name,
        "failed_at": failure.failed_at.isoformat() if failure.failed_at else None,
        "metadata": failure.metadata,
    }


def run_llm_diagnosis(ctx: dict) -> dict:
    """Run LLM diagnosis (background task)."""
    client = get_groq_client()
    if not client.available():
        return {
            "diagnosis": "llm_unavailable",
            "confidence": 0.0,
            "reasoning": "Groq not configured",
        }

    # Enrich context for LLM
    normalizer = get_normalizer()
    amount_inr = normalizer.convert(ctx["amount_paise"], ctx["currency"], "INR")

    enriched = {
        **ctx,
        "amount_paise": amount_inr,
        "currency": "INR",
        "customer_tier": "premium" if amount_inr > 100000 else "standard",  # ₹1,000+
        "attempt_number": 1,  # Would come from DB in production
        "minutes_since_failure": 0,
        "previous_actions": "none",
        "customer_history": "unknown",
    }

    return client.diagnose(enriched)


def generate_recovery_link(
    payment_id: str,
    amount_paise: int,
    currency: str,
    customer_phone: str | None,
    customer_email: str | None,
) -> dict:
    """
    Generate Razorpay payment recovery link.
    Uses Razorpay Payment Link API (test mode).
    """
    # This would use Razorpay SDK in production
    # For now, return a mock link structure
    return {
        "payment_link_id": f"plink_{payment_id}",
        "short_url": f"https://rzp.io/i/{payment_id}",
        "amount_paise": amount_paise,
        "currency": currency,
        "status": "created",
        "expires_at": None,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
    }


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
):
    """
    Razorpay webhook endpoint for payment.failed events.

    Flow:
    1. Verify signature (<2ms)
    2. Parse payload & create placeholder case (<5ms)
    3. Return 200 OK immediately (<12ms total)
    4. Background: LLM diagnosis + case creation + intervention dispatch
    """
    # 1. Read raw body for signature verification
    body = await request.body()

    # 2. Verify signature
    if not x_razorpay_signature or not verify_signature(body, x_razorpay_signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(400, "Invalid signature")

    # 3. Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON") from None

    # Only handle payment.failed events
    event = payload.get("event")
    if event != "payment.failed":
        return {"status": "ignored", "event": event}

    # 4. Parse failure
    failure = parse_webhook(payload)
    if not failure:
        raise HTTPException(400, "Failed to parse payment.failed payload")

    # 5. Create context & placeholder case (synchronous, <5ms)
    ctx = create_failure_context(failure)

    # 6. Queue LLM diagnosis for background processing
    _diagnosis_queue.append({
        "ctx": ctx,
        "failure": asdict(failure),
        "queued_at": datetime.now(timezone.utc).isoformat(),
    })

    # 7. Return immediately (<12ms target)
    return {
        "status": "accepted",
        "payment_id": failure.payment_id,
        "case_queued": True,
        "llm_diagnosis": "pending",
    }


@router.get("/diagnosis/queue")
def diagnosis_queue_status():
    """Check background diagnosis queue status."""
    return {
        "queue_length": len(_diagnosis_queue),
        "queue": _diagnosis_queue[-10:],  # last 10
    }


@router.post("/diagnosis/process")
def process_diagnosis_queue():
    """Process queued diagnoses (call from cron or background worker)."""
    processed = []
    while _diagnosis_queue:
        item = _diagnosis_queue.pop(0)
        ctx = item["ctx"]
        item["failure"]

        # Run LLM diagnosis
        diagnosis = run_llm_diagnosis(ctx)

        # Here you would: create case in DB, dispatch intervention, etc.
        # For now, just return the diagnosis
        processed.append({
            "payment_id": ctx["payment_id"],
            "failure_class": ctx["failure_class"],
            "llm_diagnosis": diagnosis,
        })

    return {"processed": len(processed), "results": processed}
