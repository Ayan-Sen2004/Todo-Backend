import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

from app.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    to_encode.update({
        "exp": int(expire.timestamp())
    })

    header = {
        "alg": "HS256",
        "typ": "JWT"
    }

    header_b64 = _b64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_b64 = _b64url_encode(
        json.dumps(to_encode, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).digest()

    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def verify_token(token: str):

    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_signature = hmac.new(
            settings.secret_key.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(
            _b64url_encode(expected_signature),
            signature_b64
        ):
            return None

        payload = json.loads(_b64url_decode(payload_b64))
        exp = payload.get("exp")
        if not isinstance(exp, int):
            return None
        if exp < int(time.time()):
            return None

        return payload

    except Exception:
        return None