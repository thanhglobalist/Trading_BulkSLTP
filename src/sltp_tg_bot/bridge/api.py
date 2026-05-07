"""FastAPI bridge — endpoints called by the EA running on the Windows VPS.

All endpoints require ``Authorization: Bearer <ea_token>``. The token maps
1-to-1 to an account; every operation is scoped to that account.

Endpoints
~~~~~~~~~

* ``POST /api/v1/heartbeat``         — periodic EA → bridge ping.
* ``GET  /api/v1/jobs/next``         — long-poll for the next pending job.
* ``POST /api/v1/jobs/{id}/result``  — report job outcome.
* ``POST /api/v1/alerts``            — enqueue a JSON alert.
* ``POST /api/v1/alerts/photo``      — upload a chart screenshot (multipart).
* ``GET  /healthz``                  — liveness probe (no auth).

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from .. import __version__, db
from ..config import get_settings
from .auth import authenticate_account

log = logging.getLogger(__name__)

# Long-poll cap (Telegram-style). EA gets a definitive response within 25s.
LONG_POLL_SECONDS = 25
LONG_POLL_INTERVAL = 0.5


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class HeartbeatIn(BaseModel):
    login: Optional[int] = None
    server: Optional[str] = None
    base_currency: Optional[str] = None
    ea_version: Optional[str] = None
    equity: Optional[float] = None
    balance: Optional[float] = None
    positions_count: Optional[int] = None


class JobResultIn(BaseModel):
    success: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)


class AlertIn(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


router = APIRouter(prefix="/api/v1")


@router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatIn, account: dict = Depends(authenticate_account)
) -> dict[str, Any]:
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        await db.update_heartbeat(
            conn,
            account_id=account["id"],
            login=body.login,
            server=body.server,
            base_currency=body.base_currency,
            ea_version=body.ea_version,
        )
    return {"ok": True, "server_version": __version__}


@router.get("/jobs/next")
async def get_next_job(
    account: dict = Depends(authenticate_account),
) -> dict[str, Any]:
    """Long-poll up to ``LONG_POLL_SECONDS`` for a pending job."""
    settings = get_settings()
    deadline = time.monotonic() + LONG_POLL_SECONDS
    while True:
        async with db.connect(settings.db_path) as conn:
            row = await db.claim_next_job(conn, account_id=account["id"])
        if row is not None:
            return {
                "job": {
                    "id": row["id"],
                    "action": row["action"],
                    "args": json.loads(row["args_json"]) if row["args_json"] else {},
                    "created_at": row["created_at"],
                    "expires_at": row["expires_at"],
                }
            }
        if time.monotonic() >= deadline:
            return {"job": None}
        await asyncio.sleep(LONG_POLL_INTERVAL)


@router.post("/jobs/{job_id}/result")
async def submit_job_result(
    job_id: str, body: JobResultIn,
    account: dict = Depends(authenticate_account),
) -> dict[str, Any]:
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        # Tenant isolation: the job MUST belong to the calling account.
        existing = await db.get_job(conn, job_id=job_id)
        if existing is None or existing["account_id"] != account["id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="job_not_found",
            )
        if existing["status"] in ("completed", "failed", "expired"):
            return {"ok": True, "already": existing["status"]}
        await db.complete_job(
            conn, job_id=job_id, success=body.success, payload=body.payload,
        )
    return {"ok": True}


@router.post("/alerts")
async def post_alert(
    body: AlertIn, account: dict = Depends(authenticate_account),
) -> dict[str, Any]:
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        alert_id = await db.enqueue_alert(
            conn,
            account_id=account["id"],
            type_=body.type,
            payload=body.payload,
        )
    return {"ok": True, "id": alert_id}


@router.post("/alerts/photo")
async def post_alert_photo(
    type: str = Form(...),
    payload_json: str = Form("{}"),
    photo: UploadFile = File(...),
    account: dict = Depends(authenticate_account),
) -> dict[str, Any]:
    """Receive a screenshot alongside an alert.

    For now we persist the photo's filename + size into the alert payload
    so the bot can later render it. The actual binary stays in memory only
    for the duration of this request — extend here if you need on-disk
    persistence.
    """
    if photo.size and photo.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="photo_too_large",
        )
    try:
        payload = json.loads(payload_json) if payload_json else {}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_payload_json",
        )
    payload.setdefault("photo", {})
    payload["photo"]["filename"] = photo.filename
    payload["photo"]["content_type"] = photo.content_type
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        alert_id = await db.enqueue_alert(
            conn, account_id=account["id"], type_=type, payload=payload,
        )
    return {"ok": True, "id": alert_id}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def build_app() -> FastAPI:
    app = FastAPI(
        title="sltp-tg-bot bridge",
        version=__version__,
        docs_url=None,         # disable public docs
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"ok": "true", "version": __version__}

    app.include_router(router)
    return app
