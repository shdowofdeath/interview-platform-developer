import hashlib
import hmac

from src.config import get_settings


def expected_signature(body: bytes) -> str:
    secret = get_settings().webhook_signing_secret.encode()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, provided: str) -> bool:
    return expected_signature(body) == provided
