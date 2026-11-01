"""Staff password hashing (ARCH-030, ARCH-036). Passwords are never stored, logged, or printed."""

import base64
import hashlib
import hmac
import secrets

# ARCH-030: scrypt parameters, set by developers and checked in safety review.
# Stronger than the PIN hash (app/auth/pin.py): a password has far more values than a 4-digit PIN,
# so a slower hash really does slow guessing, and staff log in rarely.
# n=2**16, r=8 uses 64 MB. Measured 80 ms per hash on a laptop.
SCRYPT_N = 2**16
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
HASH_BYTES = 32


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=n,
        r=r,
        p=p,
        maxmem=2 * 128 * n * r,
        dklen=HASH_BYTES,
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    scheme, n, r, p, salt, digest = stored.split("$")
    if scheme != "scrypt":
        return False
    candidate = _scrypt(password, _unb64(salt), int(n), int(r), int(p))
    return hmac.compare_digest(candidate, _unb64(digest))
