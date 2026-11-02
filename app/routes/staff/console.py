"""Plain usher and admin consoles, so a staff login lands somewhere (ARCH-035). GET /usher and
GET /admin only (API-001). The real tools come with their own pieces, such as usher.scan and
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
        {"csrf_token": token, "staff": staff, "page": page},
    )
    csrf.set_token(response, token)
    return response


@router.get("/usher")
def usher_console(request: Request, staff: Usher):
    return _console(request, staff, "usher")


@router.get("/admin")
def admin_console(request: Request, staff: Admin):
    return _console(request, staff, "admin")
