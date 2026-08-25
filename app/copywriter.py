"""Deterministic Hinglish nudge copy. Transactional recovery messages only,
with opt-out footer (compliance). Optional LLM polish when configured."""
from __future__ import annotations

from .llm import chat_json
from .models import ActionType, FailureClass, RecoveryCase

FOOTER = "\n\n(Ye payment update hai. STOP reply karke opt out kar sakte hain.)"

_TEMPLATES: dict[tuple[FailureClass, str], str] = {
    (FailureClass.INSUFFICIENT_FUNDS, "whatsapp"):
        "Namaste {name}! Aapka payment ₹{amt} balance kam hone ki wajah se fail hua tha. "
        "Jaise hi amount aa jaye, 1 tap me complete karein: {link}",
    (FailureClass.INSUFFICIENT_FUNDS, "sms"):
        "{name}, ₹{amt} payment fail tha (low balance). Pay here: {link}",
    (FailureClass.NETWORK_TIMEOUT, "whatsapp"):
        "Hi {name}, network issue ki wajah se ₹{amt} payment incomplete raha. "
        "Aapka order reserved hai — yahan complete karein: {link}",
    (FailureClass.ISSUER_UNAVAILABLE, "sms"):
        "{name}, bank issue se ₹{amt} payment fail hua tha. Retry karein: {link}",
    (FailureClass.SOFT_DECLINE_OTHER, "whatsapp"):
        "Hi {name}, aapka bank ne ₹{amt} transaction decline kiya. "
        "Kripya apna bank app check karein ya dusra tareeka try karein: {link}",
    (FailureClass.HARD_DECLINE, "whatsapp"):
        "Hi {name}, card decline ho gaya. UPI ya dusre instrument se ₹{amt} "
        "yahan pay karein: {link}",
    (FailureClass.MANDATE_ISSUE, "whatsapp"):
        "Hi {name}, aapka auto-debit mandate inactive ho gaya hai. Service continue "
        "rakhne ke liye 1 minute me re-authorize karein: {link}",
    (FailureClass.CUSTOMER_ABANDONMENT, "whatsapp"):
        "Hi {name}, aapka ₹{amt} ka order abhi bhi wait kar raha hai! "
        "Checkout complete karein: {link}",
    (FailureClass.CUSTOMER_ABANDONMENT, "sms"):
        "{name}, your ₹{amt} order is waiting. Complete checkout: {link}",
    (FailureClass.INVOICE_OVERDUE, "whatsapp"):
        "Hello {name}, invoice of ₹{amt} is pending since {days} din. "
        "Pay securely here: {link}",
    (FailureClass.INVOICE_OVERDUE, "sms"):
        "{name}: Invoice ₹{amt} overdue by {days} days. Pay: {link}",
    (FailureClass.INVOICE_OVERDUE, "email"):
        "Dear {name}, our records show invoice ₹{amt} is {days} days overdue. "
        "Kindly clear it here at the earliest: {link}",
    (FailureClass.SUBSCRIPTION_FAILED, "whatsapp"):
        "Hi {name}, aapki ₹{amt} ki auto-renewal fail ho gayi. Service continue "
        "rakhne ke liye payment complete karein: {link}",
    (FailureClass.SUBSCRIPTION_FAILED, "email"):
        "Hi {name}, we couldn't renew your plan (₹{amt}). Update your payment "
        "method or manage your plan here: {link}",
    (FailureClass.UNKNOWN, "email"):
        "Hello {name}, your recent payment of Rs {amt} could not be completed. "
        "You can safely complete it here: {link}",
}

_FALLBACK_ORDER = ["whatsapp", "sms", "email"]


def render(case: RecoveryCase, action_type: ActionType, channel: str, link: str) -> str:
    cls = case.failure_class
    template = _TEMPLATES.get((cls, channel))
    if template is None:
        for ch in _FALLBACK_ORDER:
            template = _TEMPLATES.get((cls, ch))
            if template:
                break
    template = template or (
        "Hi {name}, please complete your pending payment of Rs {amt}: {link}"
    )
    text = template.format(
        name=case.customer.name or "there",
        amt=f"{case.amount / 100:,.0f}",
        link=link,
        days=case.loss_age_days,
    )
    return text + FOOTER


def llm_polish(text: str, case: RecoveryCase) -> str:
    out = chat_json(
        "Rewrite this Indian payment-recovery SMS/WhatsApp message. Keep meaning, "
        "amount, link, and the opt-out line unchanged. Warm, brief, Hinglish. "
        'JSON: {"text": "..."}',
        text,
    )
    polished = (out or {}).get("text")
    return polished if isinstance(polished, str) and len(polished) > 30 else text


_VOICE_SCRIPTS: dict[FailureClass, str] = {
    FailureClass.INVOICE_OVERDUE: (
        "Namaste {name} ji, main Apex Enterprises ki accounts team se bol rahi hoon. "
        "Sir, aapka ₹{amt} ka invoice {days} din se pending hai. Agar aap convenient "
        "hain to main abhi payment link SMS kar deti hoon, us par ek click me clear "
        "ho jayega. Koi issue ho to aap mujhe wapas call kar sakte hain. Dhanyavaad."
    ),
}


def render_voice_script(case: RecoveryCase, link_url: str) -> tuple[str, str]:
    """Returns (tts_script, sms_followthrough_text). The link always travels by
    SMS — nobody can click a link on a phone call."""
    template = _VOICE_SCRIPTS.get(
        case.failure_class,
        "Namaste {name} ji, ₹{amt} ka payment pending hai. Link SMS me bhej rahe "
        "hain, ek click me complete ho jayega. Dhanyavaad.",
    )
    script = template.format(
        name=case.customer.name or "ji",
        amt=f"{case.amount / 100:,.0f}",
        days=case.loss_age_days,
    )
    # voice calls are high-intrusion: compliance footer is spoken too
    script += " Is message ko band karne ke liye STOP SMS karein."
    sms = render(case, ActionType.NUDGE_SMS, "sms", link_url)
    return script, sms
