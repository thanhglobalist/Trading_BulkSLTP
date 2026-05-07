"""Database layer (aiosqlite).

This module owns the schema, all CRUD helpers, and the small set of
query-shapes used by handlers. **Tenant isolation is enforced in SQL** —
every helper that returns accounts/jobs/permissions for a user filters by
that user's permissions in the ``WHERE`` clause itself.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Iterable, Optional

import aiosqlite

from .utils import generate_ea_token, utc_now_iso

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLE_NONE = "none"
ROLE_VIEW = "view"
ROLE_VIEW_CLOSE = "view_close"
ROLE_FULL = "full"

ROLE_RANK = {
    ROLE_NONE: 0,
    ROLE_VIEW: 1,
    ROLE_VIEW_CLOSE: 2,
    ROLE_FULL: 3,
}

VALID_ROLES = {ROLE_VIEW, ROLE_VIEW_CLOSE, ROLE_FULL}

# Action → minimum role required. Admin-only actions are checked separately.
ACTION_MIN_ROLE: dict[str, str] = {
    "status": ROLE_VIEW,
    "positions": ROLE_VIEW,
    "close_all": ROLE_VIEW_CLOSE,
    "close_buys": ROLE_VIEW_CLOSE,
    "close_sells": ROLE_VIEW_CLOSE,
    "sl": ROLE_FULL,
    "tp": ROLE_FULL,
    "sloff": ROLE_FULL,
    "tpoff": ROLE_FULL,
    "be": ROLE_FULL,
    "panic": ROLE_FULL,
}


def role_at_least(role: str, minimum: str) -> bool:
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(minimum, 0)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  alias TEXT UNIQUE NOT NULL,
  ea_token TEXT UNIQUE NOT NULL,
  mt5_login INTEGER,
  mt5_server TEXT,
  base_currency TEXT,
  ea_version TEXT,
  last_seen_at TEXT,
  created_at TEXT NOT NULL,
  is_paused INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS team_members (
  user_id INTEGER PRIMARY KEY,
  display_name TEXT NOT NULL,
  language TEXT DEFAULT 'en',
  is_admin INTEGER DEFAULT 0,
  is_paused INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  created_by INTEGER
);

CREATE TABLE IF NOT EXISTS permissions (
  user_id INTEGER NOT NULL,
  account_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  granted_at TEXT NOT NULL,
  granted_by INTEGER,
  PRIMARY KEY (user_id, account_id),
  FOREIGN KEY (user_id) REFERENCES team_members(user_id),
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  account_id INTEGER NOT NULL,
  requested_by INTEGER NOT NULL,
  action TEXT NOT NULL,
  args_json TEXT,
  status TEXT NOT NULL,
  result_json TEXT,
  created_at TEXT NOT NULL,
  claimed_at TEXT,
  completed_at TEXT,
  expires_at TEXT NOT NULL,
  reply_chat_id INTEGER,
  reply_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  delivered INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  account_id INTEGER,
  action TEXT NOT NULL,
  allowed INTEGER NOT NULL,
  reason TEXT,
  ip TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  user_id INTEGER PRIMARY KEY,
  current_account_id INTEGER,
  pending_state TEXT,
  pending_args_json TEXT,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_account
  ON jobs(account_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_undelivered
  ON alerts(delivered, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_created
  ON audit_log(created_at DESC);
"""


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


@asynccontextmanager
async def connect(db_path: str) -> AsyncIterator[aiosqlite.Connection]:
    """Async context manager yielding a configured aiosqlite connection."""
    Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(db_path)
    try:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        yield conn
    finally:
        await conn.close()


async def init_schema(db_path: str) -> None:
    """Create the schema if it doesn't exist."""
    async with connect(db_path) as conn:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()


# ---------------------------------------------------------------------------
# team_members
# ---------------------------------------------------------------------------


async def get_member(conn: aiosqlite.Connection, user_id: int) -> Optional[aiosqlite.Row]:
    cur = await conn.execute(
        "SELECT * FROM team_members WHERE user_id = ?", (user_id,)
    )
    return await cur.fetchone()


async def upsert_member(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    display_name: str,
    language: str = "en",
    is_admin: bool = False,
    created_by: Optional[int] = None,
) -> None:
    now = utc_now_iso()
    await conn.execute(
        """
        INSERT INTO team_members (user_id, display_name, language, is_admin, is_paused, created_at, created_by)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          display_name = excluded.display_name
        """,
        (user_id, display_name, language, 1 if is_admin else 0, now, created_by),
    )
    await conn.commit()


async def set_language(conn: aiosqlite.Connection, user_id: int, language: str) -> None:
    await conn.execute(
        "UPDATE team_members SET language = ? WHERE user_id = ?", (language, user_id)
    )
    await conn.commit()


async def is_admin(conn: aiosqlite.Connection, user_id: int) -> bool:
    cur = await conn.execute(
        "SELECT is_admin FROM team_members WHERE user_id = ? AND is_paused = 0",
        (user_id,),
    )
    row = await cur.fetchone()
    return bool(row and row[0])


async def count_admins(conn: aiosqlite.Connection) -> int:
    cur = await conn.execute(
        "SELECT COUNT(*) FROM team_members WHERE is_admin = 1 AND is_paused = 0"
    )
    row = await cur.fetchone()
    return int(row[0]) if row else 0


async def list_members(conn: aiosqlite.Connection) -> list[aiosqlite.Row]:
    cur = await conn.execute(
        "SELECT * FROM team_members ORDER BY is_admin DESC, display_name ASC"
    )
    return list(await cur.fetchall())


async def set_member_paused(conn: aiosqlite.Connection, user_id: int, paused: bool) -> None:
    await conn.execute(
        "UPDATE team_members SET is_paused = ? WHERE user_id = ?",
        (1 if paused else 0, user_id),
    )
    await conn.commit()


async def set_member_admin(conn: aiosqlite.Connection, user_id: int, admin: bool) -> None:
    """Promote/demote an admin. Caller MUST check the at-least-one-admin invariant."""
    await conn.execute(
        "UPDATE team_members SET is_admin = ? WHERE user_id = ?",
        (1 if admin else 0, user_id),
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# accounts
# ---------------------------------------------------------------------------


async def add_account(
    conn: aiosqlite.Connection, *, alias: str, ea_token: Optional[str] = None
) -> tuple[int, str]:
    """Insert an account. Returns ``(account_id, ea_token)``."""
    token = ea_token or generate_ea_token()
    now = utc_now_iso()
    cur = await conn.execute(
        "INSERT INTO accounts (alias, ea_token, created_at) VALUES (?, ?, ?)",
        (alias, token, now),
    )
    await conn.commit()
    return cur.lastrowid, token


async def rotate_account_token(conn: aiosqlite.Connection, alias: str) -> Optional[str]:
    new_token = generate_ea_token()
    cur = await conn.execute(
        "UPDATE accounts SET ea_token = ? WHERE alias = ?", (new_token, alias)
    )
    await conn.commit()
    return new_token if cur.rowcount > 0 else None


async def get_account_by_id(
    conn: aiosqlite.Connection, account_id: int
) -> Optional[aiosqlite.Row]:
    cur = await conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return await cur.fetchone()


async def get_account_by_token(
    conn: aiosqlite.Connection, ea_token: str
) -> Optional[aiosqlite.Row]:
    cur = await conn.execute(
        "SELECT * FROM accounts WHERE ea_token = ?", (ea_token,)
    )
    return await cur.fetchone()


async def list_all_accounts(conn: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Admin-only: list every account."""
    cur = await conn.execute("SELECT * FROM accounts ORDER BY alias ASC")
    return list(await cur.fetchall())


async def list_accounts_for_user(
    conn: aiosqlite.Connection, user_id: int
) -> list[aiosqlite.Row]:
    """Tenant-isolated: only accounts the user has any permission on.

    Admins implicitly receive *all* accounts so they can operate freely.
    """
    if await is_admin(conn, user_id):
        return await list_all_accounts(conn)
    cur = await conn.execute(
        """
        SELECT a.*
        FROM accounts a
        INNER JOIN permissions p ON p.account_id = a.id
        WHERE p.user_id = ?
        ORDER BY a.alias ASC
        """,
        (user_id,),
    )
    return list(await cur.fetchall())


async def update_heartbeat(
    conn: aiosqlite.Connection,
    *,
    account_id: int,
    login: Optional[int],
    server: Optional[str],
    base_currency: Optional[str],
    ea_version: Optional[str],
) -> None:
    await conn.execute(
        """
        UPDATE accounts
           SET mt5_login = COALESCE(?, mt5_login),
               mt5_server = COALESCE(?, mt5_server),
               base_currency = COALESCE(?, base_currency),
               ea_version = COALESCE(?, ea_version),
               last_seen_at = ?
         WHERE id = ?
        """,
        (login, server, base_currency, ea_version, utc_now_iso(), account_id),
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# permissions
# ---------------------------------------------------------------------------


async def get_role(
    conn: aiosqlite.Connection, *, user_id: int, account_id: int
) -> str:
    """Return the user's role for an account, or ``ROLE_NONE`` if no record.

    Admins always receive ``ROLE_FULL``.
    """
    if await is_admin(conn, user_id):
        return ROLE_FULL
    cur = await conn.execute(
        "SELECT role FROM permissions WHERE user_id = ? AND account_id = ?",
        (user_id, account_id),
    )
    row = await cur.fetchone()
    return row[0] if row else ROLE_NONE


async def set_permission(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    account_id: int,
    role: str,
    granted_by: Optional[int],
) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"invalid role: {role}")
    now = utc_now_iso()
    await conn.execute(
        """
        INSERT INTO permissions (user_id, account_id, role, granted_at, granted_by)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, account_id) DO UPDATE SET
          role = excluded.role,
          granted_at = excluded.granted_at,
          granted_by = excluded.granted_by
        """,
        (user_id, account_id, role, now, granted_by),
    )
    await conn.commit()


async def revoke_permission(
    conn: aiosqlite.Connection, *, user_id: int, account_id: int
) -> None:
    await conn.execute(
        "DELETE FROM permissions WHERE user_id = ? AND account_id = ?",
        (user_id, account_id),
    )
    await conn.commit()


async def list_permissions_for_user(
    conn: aiosqlite.Connection, user_id: int
) -> list[aiosqlite.Row]:
    cur = await conn.execute(
        """
        SELECT p.*, a.alias
          FROM permissions p
          JOIN accounts a ON a.id = p.account_id
         WHERE p.user_id = ?
         ORDER BY a.alias ASC
        """,
        (user_id,),
    )
    return list(await cur.fetchall())


async def aggregated_roles_for_user(
    conn: aiosqlite.Connection, user_id: int
) -> set[str]:
    """Collect the distinct roles a user holds across their accounts.

    Used by the dynamic help generator. Admins always include ``ROLE_FULL``.
    """
    roles: set[str] = set()
    if await is_admin(conn, user_id):
        roles.add(ROLE_FULL)
    cur = await conn.execute(
        "SELECT DISTINCT role FROM permissions WHERE user_id = ?", (user_id,)
    )
    for row in await cur.fetchall():
        roles.add(row[0])
    return roles


async def users_with_min_role_for_account(
    conn: aiosqlite.Connection, *, account_id: int, min_role: str
) -> list[aiosqlite.Row]:
    """Return team members entitled to *receive* alerts at ``min_role`` or higher.

    Admins are always included.
    """
    min_rank = ROLE_RANK.get(min_role, 0)
    cur = await conn.execute(
        """
        SELECT tm.user_id, tm.language, tm.is_admin,
               COALESCE(p.role, 'none') AS role
          FROM team_members tm
          LEFT JOIN permissions p
                 ON p.user_id = tm.user_id AND p.account_id = ?
         WHERE tm.is_paused = 0
           AND (tm.is_admin = 1 OR p.role IS NOT NULL)
        """,
        (account_id,),
    )
    rows = await cur.fetchall()
    out: list[aiosqlite.Row] = []
    for r in rows:
        rank = ROLE_RANK["full"] if r["is_admin"] else ROLE_RANK.get(r["role"], 0)
        if rank >= min_rank:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# sessions
# ---------------------------------------------------------------------------


async def get_session(conn: aiosqlite.Connection, user_id: int) -> Optional[aiosqlite.Row]:
    cur = await conn.execute("SELECT * FROM sessions WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def set_session_account(
    conn: aiosqlite.Connection, *, user_id: int, account_id: Optional[int]
) -> None:
    now = utc_now_iso()
    await conn.execute(
        """
        INSERT INTO sessions (user_id, current_account_id, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          current_account_id = excluded.current_account_id,
          updated_at = excluded.updated_at
        """,
        (user_id, account_id, now),
    )
    await conn.commit()


async def set_pending_state(
    conn: aiosqlite.Connection,
    *,
    user_id: int,
    state: Optional[str],
    args: Optional[dict[str, Any]] = None,
) -> None:
    payload = json.dumps(args) if args is not None else None
    now = utc_now_iso()
    await conn.execute(
        """
        INSERT INTO sessions (user_id, pending_state, pending_args_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          pending_state = excluded.pending_state,
          pending_args_json = excluded.pending_args_json,
          updated_at = excluded.updated_at
        """,
        (user_id, state, payload, now),
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------


async def enqueue_job(
    conn: aiosqlite.Connection,
    *,
    account_id: int,
    requested_by: int,
    action: str,
    args: Optional[dict[str, Any]] = None,
    timeout_seconds: int = 30,
    reply_chat_id: Optional[int] = None,
    reply_message_id: Optional[int] = None,
) -> str:
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(seconds=timeout_seconds)).isoformat()
    await conn.execute(
        """
        INSERT INTO jobs (id, account_id, requested_by, action, args_json,
                          status, created_at, expires_at, reply_chat_id, reply_message_id)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            job_id,
            account_id,
            requested_by,
            action,
            json.dumps(args or {}),
            now.isoformat(),
            expires,
            reply_chat_id,
            reply_message_id,
        ),
    )
    await conn.commit()
    return job_id


async def claim_next_job(
    conn: aiosqlite.Connection, *, account_id: int
) -> Optional[aiosqlite.Row]:
    """Atomically claim the oldest pending job for an account."""
    now = utc_now_iso()
    await conn.execute("BEGIN IMMEDIATE")
    try:
        cur = await conn.execute(
            """
            SELECT * FROM jobs
             WHERE account_id = ? AND status = 'pending'
             ORDER BY created_at ASC
             LIMIT 1
            """,
            (account_id,),
        )
        row = await cur.fetchone()
        if not row:
            await conn.execute("ROLLBACK")
            return None
        await conn.execute(
            "UPDATE jobs SET status = 'claimed', claimed_at = ? WHERE id = ?",
            (now, row["id"]),
        )
        await conn.execute("COMMIT")
    except Exception:
        await conn.execute("ROLLBACK")
        raise
    cur = await conn.execute("SELECT * FROM jobs WHERE id = ?", (row["id"],))
    return await cur.fetchone()


async def complete_job(
    conn: aiosqlite.Connection,
    *,
    job_id: str,
    success: bool,
    payload: Optional[dict[str, Any]] = None,
) -> Optional[aiosqlite.Row]:
    now = utc_now_iso()
    status = "completed" if success else "failed"
    await conn.execute(
        """
        UPDATE jobs
           SET status = ?, result_json = ?, completed_at = ?
         WHERE id = ? AND status IN ('pending', 'claimed')
        """,
        (status, json.dumps(payload or {}), now, job_id),
    )
    await conn.commit()
    cur = await conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    return await cur.fetchone()


async def expire_stale_jobs(conn: aiosqlite.Connection) -> int:
    """Mark jobs whose ``expires_at`` is in the past as expired."""
    now = utc_now_iso()
    cur = await conn.execute(
        """
        UPDATE jobs
           SET status = 'expired', completed_at = ?
         WHERE status IN ('pending', 'claimed') AND expires_at < ?
        """,
        (now, now),
    )
    await conn.commit()
    return cur.rowcount or 0


async def get_job(
    conn: aiosqlite.Connection, *, job_id: str
) -> Optional[aiosqlite.Row]:
    cur = await conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    return await cur.fetchone()


# ---------------------------------------------------------------------------
# alerts
# ---------------------------------------------------------------------------


async def enqueue_alert(
    conn: aiosqlite.Connection,
    *,
    account_id: int,
    type_: str,
    payload: dict[str, Any],
) -> int:
    cur = await conn.execute(
        """
        INSERT INTO alerts (account_id, type, payload_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (account_id, type_, json.dumps(payload), utc_now_iso()),
    )
    await conn.commit()
    return cur.lastrowid


async def fetch_undelivered_alerts(
    conn: aiosqlite.Connection, *, limit: int = 50
) -> list[aiosqlite.Row]:
    cur = await conn.execute(
        """
        SELECT * FROM alerts WHERE delivered = 0
         ORDER BY created_at ASC LIMIT ?
        """,
        (limit,),
    )
    return list(await cur.fetchall())


async def mark_alert_delivered(conn: aiosqlite.Connection, alert_id: int) -> None:
    await conn.execute(
        "UPDATE alerts SET delivered = 1 WHERE id = ?", (alert_id,)
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# audit_log
# ---------------------------------------------------------------------------


async def audit(
    conn: aiosqlite.Connection,
    *,
    user_id: Optional[int],
    account_id: Optional[int],
    action: str,
    allowed: bool,
    reason: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO audit_log (user_id, account_id, action, allowed, reason, ip, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, account_id, action, 1 if allowed else 0, reason, ip, utc_now_iso()),
    )
    await conn.commit()


async def list_audit(
    conn: aiosqlite.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[int] = None,
    account_id: Optional[int] = None,
) -> list[aiosqlite.Row]:
    where: list[str] = []
    params: list[Any] = []
    if user_id is not None:
        where.append("user_id = ?")
        params.append(user_id)
    if account_id is not None:
        where.append("account_id = ?")
        params.append(account_id)
    sql = "SELECT * FROM audit_log"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur = await conn.execute(sql, params)
    return list(await cur.fetchall())
