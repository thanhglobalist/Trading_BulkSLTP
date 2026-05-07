"""EA bearer-token validation for the bridge.

The bridge accepts a single header form: ``Authorization: Bearer <token>``.
The token is matched against ``accounts.ea_token``; the matching account is
returned so endpoints can scope every operation to that account.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, status

from .. import db
from ..config import get_settings


async def authenticate_account(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """FastAPI dependency that validates the Bearer token.

    Returns the account row as a dict. Raises 401 on failure.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_token",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_token",
        )
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        row = await db.get_account_by_token(conn, token)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_token",
            )
        return dict(row)
