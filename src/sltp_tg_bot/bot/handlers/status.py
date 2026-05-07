"""/status and /positions — both routed through the bridge job system.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import json

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ... import db
from ...config import get_settings
from ...i18n import t
from ..auth import check_action
from ..formatters import render_positions, render_status
from ..jobs import enqueue_and_wait, parse_result_payload

router = Router(name="status")


async def _account_or_lock(conn, user_id: int):
    """Return (member, account, lang) for the user's current session, or None."""
    member = await db.get_member(conn, user_id)
    if member is None:
        return None
    sess = await db.get_session(conn, user_id)
    if sess is None or sess["current_account_id"] is None:
        return (member, None, member["language"])
    account = await db.get_account_by_id(conn, sess["current_account_id"])
    return (member, account, member["language"])


async def _run_action(message_or_cb, action: str) -> None:
    settings = get_settings()
    user = message_or_cb.from_user
    if user is None:
        return
    chat = (message_or_cb.message.chat
            if hasattr(message_or_cb, "message") and message_or_cb.message
            else message_or_cb.chat)

    async with db.connect(settings.db_path) as conn:
        ctx = await _account_or_lock(conn, user.id)
        if ctx is None:
            await message_or_cb.answer(t("lockout", "en"))
            return
        member, account, lang = ctx
        if account is None:
            await message_or_cb.answer(t("no_accounts", lang))
            return
        auth = await check_action(
            conn, user_id=user.id, account_id=account["id"], action=action,
        )
        if not auth:
            await message_or_cb.answer(t("err_not_allowed", lang))
            return

    proc_msg = await chat.bot.send_message(chat.id, t("processing", lang))
    row = await enqueue_and_wait(
        settings.db_path,
        account_id=account["id"],
        requested_by=user.id,
        action=action,
        timeout_seconds=settings.job_timeout_seconds,
        reply_chat_id=chat.id,
        reply_message_id=proc_msg.message_id,
    )
    if row is None or row["status"] != "completed":
        await chat.bot.edit_message_text(
            t("result_timeout", lang), chat_id=chat.id, message_id=proc_msg.message_id,
        )
        return
    payload = parse_result_payload(row)
    if action == "status":
        text = render_status(account=dict(account), state=payload, lang=lang)
    else:  # positions
        text = render_positions(
            account=dict(account),
            positions=payload.get("positions", []),
            lang=lang,
        )
    try:
        await chat.bot.edit_message_text(
            text, chat_id=chat.id, message_id=proc_msg.message_id,
            parse_mode="MarkdownV2",
        )
    except Exception:
        await chat.bot.send_message(chat.id, text, parse_mode="MarkdownV2")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await _run_action(message, "status")


@router.message(Command("positions"))
async def cmd_positions(message: Message) -> None:
    await _run_action(message, "positions")


@router.callback_query(F.data == "menu:status")
async def cb_status(cb: CallbackQuery) -> None:
    await _run_action(cb, "status")
    await cb.answer()


@router.callback_query(F.data == "menu:positions")
async def cb_positions(cb: CallbackQuery) -> None:
    await _run_action(cb, "positions")
    await cb.answer()
