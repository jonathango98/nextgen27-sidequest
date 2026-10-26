"""Wrapped skeleton (WRAP-002). Unlocking comes with the Wrapped feature."""

from fastapi import APIRouter, Depends, Request

from app.auth.current import get_current_player
from app.rendering import templates

router = APIRouter()


@router.get("/wrapped", dependencies=[Depends(get_current_player)])
def wrapped(request: Request):
    return templates.TemplateResponse(request, "player/wrapped.html")
