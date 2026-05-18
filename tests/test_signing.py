"""Unit tests for HMAC-SHA256 signing utility."""
import json

from app.utils.signing import generate_signature, verify_signature


def test_signature_is_64_char_hex():
    sig = generate_signature({"amount": 5000, "currency": "INR"}, "secret")
    assert isinstance(sig, str)
    assert len(sig) == 64
    assert all(c in "0123456789abcdef" for c in sig)


def test_valid_signature_verifies():
    payload = {"transaction_id": "txn_001", "amount": 5000}
    secret = "test-secret-key"
    sig = generate_signature(payload, secret)
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    assert verify_signature(payload_bytes, secret, sig) is True


def test_wrong_secret_fails_verification():
    payload = {"amount": 5000}
    sig = generate_signature(payload, "correct-secret")
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    assert verify_signature(payload_bytes, "wrong-secret", sig) is False


def test_tampered_payload_fails_verification():
    payload = {"amount": 5000}
    sig = generate_signature(payload, "secret")
    tampered = json.dumps({"amount": 9999}, sort_keys=True, separators=(",", ":")).encode()
    assert verify_signature(tampered, "secret", sig) is False
