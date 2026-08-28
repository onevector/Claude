import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app, settings

client = TestClient(app)


def _sign(body: bytes) -> str:
    digest = hmac.new(settings.meta_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_webhook_success():
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.meta_verify_token,
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 200
    assert response.text == "12345"


def test_verify_webhook_wrong_token():
    response = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert response.status_code == 403


def test_receive_webhook_rejects_bad_signature():
    body = json.dumps({"object": "page", "entry": []}).encode()
    response = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=deadbeef"})
    assert response.status_code == 403


def test_receive_webhook_accepts_valid_signature_no_leads():
    body = json.dumps({"object": "page", "entry": []}).encode()
    response = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body)})
    assert response.status_code == 200
    assert response.text == "EVENT_RECEIVED"
