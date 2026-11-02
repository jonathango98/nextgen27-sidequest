"""Usher and admin consoles (ARCH-035, GAME-112). GET /usher and GET /admin only (API-001).
The usher console has the scanner. The other tools come with their own pieces, such as
game-state.admin-switch.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth import csrf
from app.auth.staff import CurrentStaff, require_role
from app.rendering import templates

router = APIRouter()
Usher = Annotated[CurrentStaff, Depends(require_role("usher"))]
Admin = Annotated[CurrentStaff, Depends(require_role("admin"))]


def _console(request: Request, staff: CurrentStaff, page: str):
    token = csrf.token_for(request)
    response = templates.TemplateResponse(
        request,
        "staff/console.html",
        {
            "csrf_token": token,
            "staff": staff,
            "page": page,
            # ARCH-025: the scanner only accepts codes that start with this version.
            "qr_format": request.app.state.config["qr"]["format_version"],
        },
    )
    csrf.set_token(response, token)
    return response


@router.get("/usher")
def usher_console(request: Request, staff: Usher):
    return _console(request, staff, "usher")


@router.get("/admin")
def admin_console(request: Request, staff: Admin):
    return _console(request, staff, "admin")
