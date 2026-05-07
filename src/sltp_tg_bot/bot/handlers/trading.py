"""Destructive trading flows: close, SL/TP, breakeven, panic.

Each flow follows: action tap → confirmation screen → confirm tap → enqueue
job → "Processing…" reply → background wait → success/failure edit.

Re-checks server-side permissions on every step regardless of UI state.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import json
import secrets
from typing import Any, Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ... import db
from ...config import get_settings
from ...i18n import t
from ...utils import mdv2_escape
from ..auth import check_action
from ..formatters import render_result
from ..jobs import enqueue_and_wait, parse_result_payload
from ..keyboards import confirm_kb

router = Router(name="trading")


# ---------------------------------------------------------------------------
# In-memory pending-action store
# ---------------------------------------------------------------------------
# Each pending action is keyed by an opaque token we embed in the
# Confirm/Cancel callback data. Stored payload includes the user_id so we
# can re-check that the *same* user is the one tapping confirm.
# ---------------------------------------------------------------------------

_PENDING: dict[str, dict[str, Any]] = {}
_PENDING_MAX = 1024


def _stash(payload: dict[str, Any]) -> str:
    if len(_PENDING) > _PENDING_MAX:
        # crude eviction: drop oldest half by insertion order
        for k in list(_PENDING.keys())[: _PENDING_MAX // 2]:
            _PENDING.pop(k, None)
    token = secrets.token_urlsafe(12)
    _PENDING[token] = payload
    return token


def _pop(token: str) -> Optional[dict[str, Any]]:
    return _PENDING.pop(token, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_ACTIONS_NEEDING_PRICE = {"sl", "tp"}


def _confirm_text(action: str, *, alias: str, lang: str, n: int = 0,
                  price: Optional[str] = None) -> str:
    a = mdv2_escape(alias)
    if action == "close_all":
        return t("confirm_close_all", lang, alias=a, n=n)
    if action == "close_buys":
        return t("confirm_close_buys", lang, alias=a)
    if action == "close_sells":
        return t("confirm_close_sells", lang, alias=a)
    if action == "sl":
        return t("confirm_sl", lang, alias=a, price=mdv2_escape(price or ""), n=n)
    if action == "tp":
        return t("confirm_tp", lang, alias=a, price=mdv2_escape(price or ""), n=n)
    if action == "sloff":
        return t("confirm_sloff", lang, alias=a, n=n)
    if action == "tpoff":
        return t("confirm_tpoff", lang, alias=a, n=n)
    if action == "be":
        return t("confirm_be", lang, alias=a)
    return action


# ---------------------------------------------------------------------------
# Action tap → confirmation
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("trade:"))
async def cb_trade(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    parts = cb.data.split(":")
    if len(parts) < 3:
        await cb.answer()
        return
    action = parts[1]
    try:
        account_id = int(parts[2])
    except ValueError:
        await cb.answer()
        return

    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
        if member is None:
            await cb.answer(t("lockout", "en"), show_alert=True)
            return
        lang = member["language"]
        # Re-check permissions on the server
        auth = await check_action(
            conn, user_id=cb.from_user.id, account_id=account_id, action=action,
        )
        if not auth:
            await cb.answer(t("err_not_allowed", lang), show_alert=True)
            return
        account = await db.get_account_by_id(conn, account_id)

    if account is None:
        await cb.answer()
        return

    # Panic uses an extra-friction text gate, not the inline confirm.
    if action == "panic":
        await db.connect(settings.db_path).__aenter__() if False else None
        # Mark pending state so the catch-all picks up the typed "PANIC".
        async with db.connect(settings.db_path) as conn:
            await db.set_pending_state(
                conn,
                user_id=cb.from_user.id,
                state="awaiting_panic",
                args={"account_id": account_id},
            )
        await cb.message.answer(
            t("panic_prompt", lang, alias=mdv2_escape(account["alias"])),
            parse_mode="MarkdownV2",
        )
        await cb.answer()
        return

    # SL / TP need a price first → set pending_state, ask user for input.
    if action in _ACTIONS_NEEDING_PRICE:
        async with db.connect(settings.db_path) as conn:
            await db.set_pending_state(
                conn,
                user_id=cb.from_user.id,
                state=f"awaiting_{action}_price",
                args={"account_id": account_id},
            )
        prompt = t("ask_sl_price" if action == "sl" else "ask_tp_price", lang)
        await cb.message.answer(prompt)
        await cb.answer()
        return

    # All other actions: show confirmation screen now.
    token = _stash({
        "user_id": cb.from_user.id,
        "account_id": account_id,
        "action": action,
        "args": {},
    })
    text = _confirm_text(action, alias=account["alias"], lang=lang, n=0)
    await cb.message.answer(
        text, parse_mode="MarkdownV2", reply_markup=confirm_kb(token, lang),
    )
    await cb.answer()


# ---------------------------------------------------------------------------
# Pending-state text input (price for SL/TP, "PANIC" word)
# ---------------------------------------------------------------------------


@router.message(F.text & ~F.text.startswith("/"))
async def pending_text(message: Message) -> None:
    if message.from_user is None or message.text is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, message.from_user.id)
        if member is None:
            # The common.py catch-all also handles strangers; bail.
            return
        sess = await db.get_session(conn, message.from_user.id)
        if sess is None or not sess["pending_state"]:
            return  # let the common.py catch-all handle it
        state = sess["pending_state"]
        args = json.loads(sess["pending_args_json"]) if sess["pending_args_json"] else {}
        lang = member["language"]
        # Always clear pending state once we read it
        await db.set_pending_state(conn, user_id=message.from_user.id, state=None, args=None)

    text = message.text.strip()

    if state == "awaiting_panic":
        account_id = args.get("account_id")
        if text != "PANIC":
            await message.answer(t("panic_cancelled", lang))
            return
        async with db.connect(settings.db_path) as conn:
            auth = await check_action(
                conn, user_id=message.from_user.id, account_id=account_id, action="panic",
            )
            if not auth:
                await message.answer(t("err_not_allowed", lang))
                return
            account = await db.get_account_by_id(conn, account_id)
        await message.answer(
            t("panic_armed", lang, alias=mdv2_escape(account["alias"]) if account else ""),
            parse_mode="MarkdownV2",
        )
        await _execute(message.from_user.id, account_id, "panic", {}, message, lang)
        return

    if state in ("awaiting_sl_price", "awaiting_tp_price"):
        action = "sl" if state == "awaiting_sl_price" else "tp"
        account_id = args.get("account_id")
        try:
            price = float(text.replace(",", "."))
        except ValueError:
            await message.answer(t("invalid_price", lang))
            return
        async with db.connect(settings.db_path) as conn:
            auth = await check_action(
                conn, user_id=message.from_user.id, account_id=account_id, action=action,
            )
            if not auth:
                await message.answer(t("err_not_allowed", lang))
                return
            account = await db.get_account_by_id(conn, account_id)
        token = _stash({
            "user_id": message.from_user.id,
            "account_id": account_id,
            "action": action,
            "args": {"price": price},
        })
        await message.answer(
            _confirm_text(action, alias=account["alias"] if account else "?",
                          lang=lang, price=str(price), n=0),
            parse_mode="MarkdownV2",
            reply_markup=confirm_kb(token, lang),
        )
        return


# ---------------------------------------------------------------------------
# Confirm / Cancel
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("cfm:"))
async def cb_confirm(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    parts = cb.data.split(":")
    if len(parts) < 3:
        await cb.answer()
        return
    decision, token = parts[1], parts[2]
    payload = _pop(token)
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
    lang = member["language"] if member else "en"

    if payload is None:
        await cb.answer(t("err_unknown", lang), show_alert=True)
        return
    if payload["user_id"] != cb.from_user.id:
        await cb.answer(t("err_not_allowed", lang), show_alert=True)
        return
    if decision != "ok":
        await cb.message.answer(t("cancelled", lang))
        await cb.answer()
        return

    await _execute(
        cb.from_user.id, payload["account_id"], payload["action"],
        payload.get("args", {}), cb.message, lang,
    )
    await cb.answer()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


async def _execute(
    user_id: int, account_id: int, action: str, args: dict[str, Any],
    chat_msg, lang: str,
) -> None:
    settings = get_settings()
    # Always re-verify permission server-side.
    async with db.connect(settings.db_path) as conn:
        auth = await check_action(
            conn, user_id=user_id, account_id=account_id, action=action,
        )
        if not auth:
            await chat_msg.answer(t("err_not_allowed", lang))
            return

    proc = await chat_msg.answer(t("processing", lang))
    row = await enqueue_and_wait(
        settings.db_path,
        account_id=account_id,
        requested_by=user_id,
        action=action,
        args=args,
        timeout_seconds=settings.job_timeout_seconds,
        reply_chat_id=proc.chat.id,
        reply_message_id=proc.message_id,
    )
    if row is None or row["status"] != "completed":
        try:
            await chat_msg.bot.edit_message_text(
                t("result_timeout", lang),
                chat_id=proc.chat.id, message_id=proc.message_id,
            )
        except Exception:
            await chat_msg.answer(t("result_timeout", lang))
        return
    payload = parse_result_payload(row)
    success = bool(payload.get("success", row["status"] == "completed"))
    summary = str(payload.get("summary") or payload.get("message") or action)
    text = render_result(success=success, summary=summary, lang=lang)
    try:
        await chat_msg.bot.edit_message_text(
            text, chat_id=proc.chat.id, message_id=proc.message_id,
            parse_mode="MarkdownV2",
        )
    except Exception:
        await chat_msg.answer(text, parse_mode="MarkdownV2")
