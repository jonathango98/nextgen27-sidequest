"""PIN hashing (SAFE-021, ARCH-030). PINs are never stored, logged, or sent back."""

import base64
import hashlib
import hmac
import secrets

# ARCH-030: scrypt parameters, set by developers and checked in safety review.
# n=2**14, r=8 uses 16 MB. Measured 44 ms per hash on a laptop, and hashes run in parallel
# across worker threads. The load test checks this on Railway (ARCH-071).
# A 4-digit PIN has only 10,000 values, so a slower hash would add little; lockout does the work (SAFE-022).
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
HASH_BYTES = 32


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _scrypt(pin: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        pin.encode(), salt=salt, n=n, r=r, p=p, maxmem=2 * 128 * n * r, dklen=HASH_BYTES
    )


def is_valid(pin: str, digits: int) -> bool:
    return len(pin) == digits and pin.isascii() and pin.isdigit()


def hash_pin(pin: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _scrypt(pin, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_pin(pin: str, stored: str) -> bool:
    scheme, n, r, p, salt, digest = stored.split("$")
    if scheme != "scrypt":
        return False
    candidate = _scrypt(pin, _unb64(salt), int(n), int(r), int(p))
    return hmac.compare_digest(candidate, _unb64(digest))
