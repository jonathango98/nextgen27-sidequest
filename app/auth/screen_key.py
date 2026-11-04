"""The main screen's secret link (ARCH-037, DEC-069). The key lives only in SQ_SCREEN_KEY on the server.

The main screen has no login. Its link carries the key as ?k=. A wrong or missing key gets the
same 404 as a page that does not exist, and so does every main screen page while the key is not set.
"""

import hmac
import os
from urllib.parse import quote

from fastapi import HTTPException, Request

KEY_ENV = "SQ_SCREEN_KEY"
PARAM = "k"


def _key() -> str | None:
    return os.environ.get(KEY_ENV) or None


def require_screen_key(request: Request) -> str:
    """A FastAPI dependency for every main screen page. Returns the key, for the next view's link."""
    key = _key()
    given = request.query_params.get(PARAM, "")
    # compare_digest takes the same time whatever the guess, so timing gives nothing away.
    if key is None or not hmac.compare_digest(given.encode(), key.encode()):
        raise HTTPException(status_code=404)
    return key


def screen_link(request: Request) -> str | None:
    """The full main screen link, shown to admins on the admin console. None while the key is not set."""
    key = _key()
    if key is None:
        return None
    # ARCH-010: always HTTPS. Railway ends HTTPS at its edge, so the app may see plain http.
    return f"https://{request.url.netloc}/screen?{PARAM}={quote(key, safe='')}"
