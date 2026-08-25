#!/usr/bin/env python
"""Live test-mode preflight. Run AFTER putting real keys in .env:

    cp .env.example .env      # fill RAZORPAY_KEY_ID / KEY_SECRET / WEBHOOK_SECRET
    .venv/bin/python scripts/live_check.py

Checks, in order: key format -> API auth -> payment-link creation ->
webhook signature round-trip through the actual receiver.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dotenv import load_env

load_env()

import os

import httpx

from app.razorpay_client import RazorpayClient

KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
BASE = "https://api.razorpay.com/v1"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


print("[1/4] credentials")
check("key id present", bool(KEY_ID))
check("key id is test-mode", KEY_ID.startswith("rzp_test_"),
      "live mode keys are out of scope for this program"
      if KEY_ID and not KEY_ID.startswith("rzp_test_") else "")
check("key secret present", bool(KEY_SECRET))
if not (KEY_ID and KEY_SECRET):
    print("\nPut RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in .env first.")
    sys.exit(1)

print("[2/4] API auth")
try:
    r = httpx.get(f"{BASE}/payments?count=1", auth=(KEY_ID, KEY_SECRET), timeout=15)
    check("GET /payments authorized", r.status_code == 200,
          f"HTTP {r.status_code}" if r.status_code != 200
          else f"auth OK ({r.json().get('count', 0)} payments in test account)")
except Exception as e:
    check("GET /payments authorized", False, str(e))
    sys.exit(1)

print("[3/4] payment link creation (Rs 1 test)")
try:
    r = httpx.post(f"{BASE}/payment_links/", auth=(KEY_ID, KEY_SECRET), timeout=15, json={
        "amount": 100, "currency": "INR", "accept_partial": False,
        "reference_id": f"preflight_{int(time.time())}",
        "description": "recovery-agent preflight",
        "customer": {"name": "Preflight", "email": "preflight@example.com"},
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
    })
    ok = r.status_code in (200, 201)
    short_url = r.json().get("short_url", "") if ok else ""
    check("POST /payment_links/", ok,
          f"HTTP {r.status_code} {r.text[:120]}" if not ok else short_url)
except Exception as e:
    check("POST /payment_links/", False, str(e))

print("[4/4] webhook signature round-trip through the real receiver")
if not WEBHOOK_SECRET:
    check("webhook secret set", False,
          "add RAZORPAY_WEBHOOK_SECRET (set it in Dashboard -> Settings -> Webhooks too)")
else:
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    failed_event = {
        "event": "payment.failed",
        "created_at": int(time.time()),
        "payload": {"payment": {"entity": {
            "id": "pay_preflight0001", "order_id": "order_preflight01",
            "amount": 250000, "method": "card",
            "error_code": "insufficient_funds",
            "error_description": "Payment declined due to insufficient funds",
            "customer_id": "cust_preflight1",
            "notes": {"name": "Preflight User", "phone": "+919999900009",
                      "email": "preflight@example.com"},
        }}},
    }
    body = json.dumps(failed_event).encode()
    sig = RazorpayClient.sign(body, WEBHOOK_SECRET)
    resp = c.post("/webhooks/razorpay", content=body,
                  headers={"X-Razorpay-Signature": sig})
    case_id = resp.json().get("case_id", "") if resp.status_code == 200 else ""
    check("signed payment.failed accepted", resp.status_code == 200 and bool(case_id),
          f"HTTP {resp.status_code} {resp.text[:120]}")

    bad = c.post("/webhooks/razorpay", content=body,
                 headers={"X-Razorpay-Signature": "deadbeef"})
    check("forged signature rejected", bad.status_code == 400)

    paid_event = {
        "event": "payment_link.paid",
        "created_at": int(time.time()),
        "payload": {
            "payment_link": {"entity": {
                "id": "plink_preflight", "reference_id": case_id or "",
                "amount": 250000,
                "payments": [{"id": "pay_preflight_paid1"}],
            }},
        },
    }
    body2 = json.dumps(paid_event).encode()
    sig2 = RazorpayClient.sign(body2, WEBHOOK_SECRET)
    resp2 = c.post("/webhooks/razorpay", content=body2,
                   headers={"X-Razorpay-Signature": sig2})
    check("signed payment_link.paid marks recovery",
          resp2.status_code == 200 and resp2.json().get("status") == "recovered",
          f"HTTP {resp2.status_code} {resp2.text[:120]}")

print()
failed = [r for r in results if not r[1]]
if failed:
    print(f"{len(failed)} check(s) FAILED — fix above, then re-run.")
    sys.exit(1)
print("ALL CHECKS PASS — live test-mode plumbing is verified end to end.")
print()
print("Next steps:")
print("  1. Dashboard -> Settings -> Webhooks -> add URL (https://.../webhooks/razorpay),")
print("     secret = same as RAZORPAY_WEBHOOK_SECRET, events: payment.failed, payment_link.paid")
print("  2. Expose localhost for testing:  ngrok http 8000   (or cloudflared tunnel --url http://localhost:8000)")
print("  3. Run the agent:  .venv/bin/uvicorn app.main:app --port 8000")
print("  4. Cron/tick every minute during testing: curl -X POST localhost:8000/tick")
