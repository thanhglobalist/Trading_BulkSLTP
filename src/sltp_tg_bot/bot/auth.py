"""Authorization helpers for bot handlers.

Every action handler MUST go through :func:`check_action` (or one of the
admin helpers) so that:

  * stranger lockout is enforced uniformly,
  * permissions are re-checked on the server even if the UI hid the button,
  * every allow / deny is written to the audit log.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import aiosqlite

from .. import db


@dataclass
class AuthResult:
    allowed: bool
    role: str
    reason: Optional[str] = None

    def __bool__(self) -> bool:
        return self.allowed


async def is_known_member(conn: aiosqlite.Connection, user_id: int) -> bool:
    """Return True if the user has a (non-paused) team_members row."""
    cur = await conn.execute(
        "SELECT 1 FROM team_members WHERE user_id = ? AND is_paused = 0",
        (user_id,),
    )
    return (await cur.fetchone()) is not None


async def check_action(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    account_id: int,
    action: str,
) -> AuthResult:
    """Verify that ``user_id`` may perform ``action`` on ``account_id``.

    Writes a row to ``audit_log`` on every call.
    """
    if not await is_known_member(conn, user_id):
        await db.audit(
            conn,
            user_id=user_id,
            account_id=account_id,
            action=action,
            allowed=False,
            reason="not_member",
        )
        return AuthResult(False, db.ROLE_NONE, "not_member")

    role = await db.get_role(conn, user_id=user_id, account_id=account_id)
    minimum = db.ACTION_MIN_ROLE.get(action)
    if minimum is None:
        await db.audit(
            conn,
            user_id=user_id,
            account_id=account_id,
            action=action,
            allowed=False,
            reason="unknown_action",
        )
        return AuthResult(False, role, "unknown_action")

    if not db.role_at_least(role, minimum):
        await db.audit(
            conn,
            user_id=user_id,
            account_id=account_id,
            action=action,
            allowed=False,
            reason=f"role={role}<{minimum}",
        )
        return AuthResult(False, role, "insufficient_role")

    await db.audit(
        conn,
        user_id=user_id,
        account_id=account_id,
        action=action,
        allowed=True,
    )
    return AuthResult(True, role)


async def require_admin(
    conn: aiosqlite.Connection, *, user_id: int, action: str
) -> bool:
    """Return True if ``user_id`` is an active admin; audit either way."""
    ok = await db.is_admin(conn, user_id)
    await db.audit(
        conn,
        user_id=user_id,
        account_id=None,
        action=action,
        allowed=ok,
        reason=None if ok else "not_admin",
    )
    return ok


async def can_remove_or_demote_admin(
    conn: aiosqlite.Connection, target_user_id: int
) -> bool:
    """Enforce the at-least-one-admin invariant.

    Returns False if removing/demoting ``target_user_id`` would leave the
    system without any active admin.
    """
    cur = await conn.execute(
        "SELECT is_admin, is_paused FROM team_members WHERE user_id = ?",
        (target_user_id,),
    )
    row = await cur.fetchone()
    if not row or not row[0]:
        # target is not currently an admin → safe to remove
        return True
    n = await db.count_admins(conn)
    return n > 1
