"""Job lifecycle helpers shared between bot handlers and the bridge.

Flow::

    handler   ─▶  enqueue_and_wait()
                    ├── INSERT jobs(status='pending', expires_at=now+T)
                    ├── poll jobs.status until completed/failed/expired
                    └── return result row (or None on timeout)

The EA polls the bridge's ``/jobs/next`` long-poll endpoint, claims the job,
executes it, and POSTs the result back to ``/jobs/{id}/result``.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

import aiosqlite

from .. import db

log = logging.getLogger(__name__)

# How often we poll the DB for a job result while waiting.
_POLL_INTERVAL_SECONDS = 0.5


async def enqueue_and_wait(
    db_path: str,
    *,
    account_id: int,
    requested_by: int,
    action: str,
    args: Optional[dict[str, Any]] = None,
    timeout_seconds: int = 30,
    reply_chat_id: Optional[int] = None,
    reply_message_id: Optional[int] = None,
) -> Optional[aiosqlite.Row]:
    """Enqueue a job and await its completion (or timeout).

    Returns the final job row, or ``None`` if the wait loop timed out before
    the EA reported back.
    """
    async with db.connect(db_path) as conn:
        job_id = await db.enqueue_job(
            conn,
            account_id=account_id,
            requested_by=requested_by,
            action=action,
            args=args,
            timeout_seconds=timeout_seconds,
            reply_chat_id=reply_chat_id,
            reply_message_id=reply_message_id,
        )

    deadline_steps = int(timeout_seconds / _POLL_INTERVAL_SECONDS) + 2
    for _ in range(deadline_steps):
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        async with db.connect(db_path) as conn:
            row = await db.get_job(conn, job_id=job_id)
            if row is None:
                continue
            if row["status"] in ("completed", "failed", "expired"):
                return row
    # Final pass: mark as expired so it doesn't sit in 'pending'.
    async with db.connect(db_path) as conn:
        await db.expire_stale_jobs(conn)
        return await db.get_job(conn, job_id=job_id)


def parse_result_payload(row: Optional[aiosqlite.Row]) -> dict[str, Any]:
    if row is None or row["result_json"] is None:
        return {}
    try:
        return json.loads(row["result_json"])
    except (ValueError, TypeError):
        return {}
