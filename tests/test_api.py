from fastapi.testclient import TestClient

from ccp.api import app

client = TestClient(app)
CONSENT = {"sms": True, "email": True, "push": True}


def body(**over):
    base = {"consent": CONSENT, "history": [], "proposed": {"day": 10, "hour": 12, "channel": "sms"}}
    base.update(over)
    return base


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_policy_endpoint_exposes_rules():
    r = client.get("/policy").json()
    assert r["rules"]["min_gap_days"] == 2


def test_allowed():
    r = client.post("/check-contact", json=body()).json()
    assert r == {"allowed": True, "reason": None, "policy_version": 1}


def test_suppressed_with_reason():
    r = client.post("/check-contact", json=body(consent={"sms": False, "email": True, "push": True})).json()
    assert r["allowed"] is False and r["reason"] == "no_consent"


def test_history_is_used():
    hist = [{"day": 9, "hour": 12, "channel": "push"}]
    assert client.post("/check-contact", json=body(history=hist)).json()["reason"] == "min_gap"


def test_invalid_hour_rejected():
    bad = body(proposed={"day": 10, "hour": 25, "channel": "sms"})
    assert client.post("/check-contact", json=bad).status_code == 422


def test_invalid_channel_rejected():
    bad = body(proposed={"day": 10, "hour": 12, "channel": "fax"})
    assert client.post("/check-contact", json=bad).status_code == 422
