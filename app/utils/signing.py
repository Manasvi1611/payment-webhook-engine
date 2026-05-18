import hashlib
import hmac
import json


def generate_signature(payload: dict, secret: str) -> str:
    """Generate HMAC-SHA256 signature for a payload dict."""
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature against raw payload bytes."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
