"""Vulcan classifier adapter: env-gated, graceful degradation to rule table."""
import httpx


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("VULCAN_API_URL", raising=False)
    from app.classifier import classify
    from app.classifier_vulcan import vulcan_classify
    from app.models import FailureClass

    assert vulcan_classify("x", "y") is None
    # classify() behaves exactly as before: rules answer
    cls, conf = classify("insufficient_funds", "Payment declined due to insufficient funds")
    assert cls is FailureClass.INSUFFICIENT_FUNDS and conf >= 0.9


def test_healthy_provider_wins_over_rules(monkeypatch):
    monkeypatch.setenv("VULCAN_API_URL", "http://vulcan.local/classify")

    def fake_post(url, **kw):
        assert kw["json"]["raw_error_code"] == "gateway_error"
        return httpx.Response(200, json={"failure_class": "MANDATE_ISSUE",
                                         "confidence": 0.97})

    from app import classifier_vulcan
    monkeypatch.setattr(classifier_vulcan, "_post", fake_post)
    from app.classifier import classify
    from app.models import FailureClass

    # gateway_error would map to ISSUER_UNAVAILABLE via rules; Vulcan wins
    cls, conf = classify("gateway_error", "acquirer timeout", "card")
    assert (cls, conf) == (FailureClass.MANDATE_ISSUE, 0.97)


def test_broken_provider_falls_back_to_rules(monkeypatch):
    monkeypatch.setenv("VULCAN_API_URL", "http://vulcan.local/classify")

    def broken_post(url, **kw):
        raise httpx.ConnectError("provider down")

    from app import classifier_vulcan
    monkeypatch.setattr(classifier_vulcan, "_post", broken_post)
    from app.classifier import classify
    from app.models import FailureClass

    cls, _ = classify("network_error", "Request timed out at network", "upi")
    assert cls is FailureClass.NETWORK_TIMEOUT          # rules caught the fall


def test_malformed_payload_falls_back_to_rules(monkeypatch):
    monkeypatch.setenv("VULCAN_API_URL", "http://vulcan.local/classify")

    def weird_post(url, **kw):
        return httpx.Response(200, json={"failure_class": "NOT_A_CLASS",
                                         "confidence": "high"})

    from app import classifier_vulcan
    monkeypatch.setattr(classifier_vulcan, "_post", weird_post)
    from app.classifier import classify
    from app.models import FailureClass

    cls, _ = classify("blocked_card", "Card blocked by issuer, do not honor", "card")
    assert cls is FailureClass.HARD_DECLINE
