"""Rotating QR codes: SQ1 payloads and time-based codes (GAME-001, ARCH-020 to ARCH-023)."""

import hashlib
import hmac
import math
import os

KEY_ENV = "SQ_QR_SIGNING_KEY"  # ARCH-023
PLAYER_KIND = "P"  # ARCH-020: a player's My Code


class SigningKeyMissing(Exception):
    pass


def _signing_key() -> bytes:
    # ARCH-023: the key lives only in the server environment. No fallback key.
    key = os.environ.get(KEY_ENV, "")
    if not key:
        raise SigningKeyMissing(f"{KEY_ENV} is not set")
    return key.encode()


def _secret(kind: str, public_id: str) -> bytes:
    # ARCH-023: each player and session gets its own secret, derived from the key and its public ID.
    message = f"{kind}|{public_id}".encode()
    return hmac.new(_signing_key(), message, hashlib.sha256).digest()


def _window(now: float, qr: dict) -> int:
    return int(now // qr["rotation_seconds"])


def _code(secret: bytes, window: int, digits: int) -> str:
    # ARCH-021: TOTP. RFC 4226 truncation over HMAC-SHA256 of the window number.
    mac = hmac.new(secret, window.to_bytes(8, "big"), hashlib.sha256).digest()
    offset = mac[-1] & 0x0F
    value = int.from_bytes(mac[offset : offset + 4], "big") & 0x7FFFFFFF
    return str(value % 10**digits).zfill(digits)


def payload(kind: str, public_id: str, now: float, qr: dict) -> str:
    # ARCH-020: SQ1.<kind>.<public_id>.<code>
    code = _code(_secret(kind, public_id), _window(now, qr), qr["code_digits"])
    return f"{qr['format_version']}.{kind}.{public_id}.{code}"


def verify(kind: str, public_id: str, code: str, now: float, qr: dict) -> bool:
    # ARCH-022: accept the current window and qr.accepted_previous_steps windows before it.
    if not (code.isascii() and code.isdigit() and len(code) == qr["code_digits"]):
        return False
    secret = _secret(kind, public_id)
    window = _window(now, qr)
    return any(
        hmac.compare_digest(code, _code(secret, window - step, qr["code_digits"]))
        for step in range(qr["accepted_previous_steps"] + 1)
    )


def seconds_left(now: float, qr: dict) -> int:
    # API-030: whole seconds until the next code, so the page refreshes on time.
    rotation = qr["rotation_seconds"]
    return math.ceil(rotation - now % rotation)
