"""Reads URL-encoded form posts with the standard library.

Every form in the app is a plain text form with no file uploads, so this avoids adding
python-multipart, which Starlette's request.form() needs (AI-021).
"""

from urllib.parse import parse_qsl

from fastapi import Request

FORM_TYPE = "application/x-www-form-urlencoded"
# Not a game number: the largest form body accepted. Join and takeaways are far smaller.
MAX_BODY_BYTES = 16_384


class BadForm(Exception):
    pass


async def read_form(request: Request) -> dict[str, str]:
    """The posted fields. A repeated field keeps its first value. Cached per request."""
    if hasattr(request.state, "form"):
        return request.state.form
    content_type = request.headers.get("content-type", "").split(";")[0].strip()
    if content_type != FORM_TYPE:
        raise BadForm
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY_BYTES:
            raise BadForm  # stop reading at the limit
    try:
        pairs = parse_qsl(
            body.decode("utf-8"), keep_blank_values=True, strict_parsing=False
        )
    except UnicodeDecodeError as error:
        raise BadForm from error
    form: dict[str, str] = {}
    for key, value in pairs:
        form.setdefault(key, value)
    request.state.form = form
    return form
