"""Alert fan-out background task.

Polls the ``alerts`` table for undelivered rows and dispatches each to the
team members who have at least the required role for that alert type, in
their selected language.

Alert types and minimum role required to *receive* them:

  * ``pos_open``       — view
  * ``pos_close``      — view
  * ``margin``         — view_close
  * ``daily_summary``  — view

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from .. import db
from ..config import get_settings
from ..i18n import t
from ..utils import format_pl, mdv2_escape

log = logging.getLogger(__name__)

# Alert type → minimum role required to receive
ALERT_MIN_ROLE: dict[str, str] = {
    "pos_open": db.ROLE_VIEW,
    "pos_close": db.ROLE_VIEW,
    "margin": db.ROLE_VIEW_CLOSE,
    "daily_summary": db.ROLE_VIEW,
}

POLL_INTERVAL_SECONDS = 2.0


def _format_alert(*, alert_type: str, account_alias: str, payload: dict[str, Any],
                  lang: str) -> str:
    """Render an alert into a localised MarkdownV2 message."""
    alias = mdv2_escape(account_alias)
    if alert_type == "pos_open":
        return t(
            "alert_pos_open", lang,
            alias=alias,
            side=mdv2_escape(payload.get("side", "?")),
            volume=mdv2_escape(str(payload.get("volume", "?"))),
            symbol=mdv2_escape(payload.get("symbol", "?")),
            price=mdv2_escape(str(payload.get("price", "?"))),
        )
    if alert_type == "pos_close":
        return t(
            "alert_pos_close", lang,
            alias=alias,
            side=mdv2_escape(payload.get("side", "?")),
            volume=mdv2_escape(str(payload.get("volume", "?"))),
            symbol=mdv2_escape(payload.get("symbol", "?")),
            price=mdv2_escape(str(payload.get("price", "?"))),
            pl=mdv2_escape(format_pl(
                payload.get("pl", 0.0), payload.get("currency", "USD")
            )),
        )
    if alert_type == "margin":
        return t(
            "alert_margin", lang,
            alias=alias,
            level=mdv2_escape(str(payload.get("level", "?"))),
        )
    if alert_type == "daily_summary":
        return t(
            "alert_daily_summary", lang,
            alias=alias,
            trades=mdv2_escape(str(payload.get("trades", 0))),
            pl=mdv2_escape(format_pl(
                payload.get("pl", 0.0), payload.get("currency", "USD")
            )),
        )
    # Fallback: no localisation available — keep it generic.
    return f"*{alias}* — {mdv2_escape(alert_type)}"


async def deliver_one(bot, conn, row) -> None:
    alert_type = row["type"]
    account_id = row["account_id"]
    payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
    min_role = ALERT_MIN_ROLE.get(alert_type, db.ROLE_VIEW)

    account = await db.get_account_by_id(conn, account_id)
    if account is None:
        await db.mark_alert_delivered(conn, row["id"])
        return

    recipients = await db.users_with_min_role_for_account(
        conn, account_id=account_id, min_role=min_role,
    )
    for r in recipients:
        lang = r["language"] or "en"
        text = _format_alert(
            alert_type=alert_type,
            account_alias=account["alias"],
            payload=payload,
            lang=lang,
        )
        try:
            await bot.send_message(r["user_id"], text, parse_mode="MarkdownV2")
        except Exception as exc:
            log.warning("alert delivery to %s failed: %s", r["user_id"], exc)
    await db.mark_alert_delivered(conn, row["id"])


async def alerts_worker(bot) -> None:
    """Background task: drain undelivered alerts forever."""
    settings = get_settings()
    log.info("alerts worker started; polling every %ss", POLL_INTERVAL_SECONDS)
    while True:
        try:
            async with db.connect(settings.db_path) as conn:
                rows = await db.fetch_undelivered_alerts(conn, limit=50)
                for row in rows:
                    await deliver_one(bot, conn, row)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover
            log.exception("alerts worker error: %s", exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def jobs_expirer() -> None:
    """Background task: periodically expire stale jobs."""
    settings = get_settings()
    while True:
        try:
            async with db.connect(settings.db_path) as conn:
                await db.expire_stale_jobs(conn)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover
            log.exception("expirer error: %s", exc)
        await asyncio.sleep(5.0)
