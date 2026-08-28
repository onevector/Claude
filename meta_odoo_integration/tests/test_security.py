import hashlib
import hmac

from app.security import verify_meta_signature

SECRET = "test-app-secret"
BODY = b'{"object":"page","entry":[]}'


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_accepted():
    assert verify_meta_signature(BODY, _sign(BODY, SECRET), SECRET) is True


def test_wrong_secret_rejected():
    assert verify_meta_signature(BODY, _sign(BODY, "wrong-secret"), SECRET) is False


def test_tampered_body_rejected():
    signature = _sign(BODY, SECRET)
    assert verify_meta_signature(b'{"object":"page","entry":["tampered"]}', signature, SECRET) is False


def test_missing_header_rejected():
    assert verify_meta_signature(BODY, None, SECRET) is False


def test_malformed_header_rejected():
    assert verify_meta_signature(BODY, "not-a-real-signature", SECRET) is False
