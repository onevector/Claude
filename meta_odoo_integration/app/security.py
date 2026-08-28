import hashlib
import hmac


def verify_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Verify Meta's X-Hub-Signature-256 header against the raw request body.

    Meta signs every webhook POST with HMAC-SHA256 over the raw (unparsed)
    body, keyed with the app secret. Rejecting anything that doesn't match
    stops spoofed requests from creating fake leads in Odoo.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)
