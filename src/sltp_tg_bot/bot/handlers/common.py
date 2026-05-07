"""/start, /help, /menu, /getmyid, /lang and the language picker.

Implements the stranger-lockout policy: anyone not in ``team_members``
(and not the bootstrap admin) gets *only* the localised lockout string
and an audit row — no command list, no version hint.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
    Message,
)

from ... import db
from ...config import get_settings
from ...i18n import (
    SUPPORTED_LANGUAGES,
    detect_language_from_client,
    t,
)
from ...utils import mdv2_escape
from ..keyboards import language_kb

log = logging.getLogger(__name__)
router = Router(name="common")


# ---------------------------------------------------------------------------
# Per-user command list
# ---------------------------------------------------------------------------


def _commands_for(lang: str, *, is_admin: bool) -> list[BotCommand]:
    cmds = [
        BotCommand(command="menu", description=t("btn_status", lang)[2:] + " / menu"),
        BotCommand(command="status", description=t("btn_status", lang)[2:]),
        BotCommand(command="positions", description=t("btn_positions", lang)[2:]),
        BotCommand(command="help", description=t("btn_help", lang)[2:]),
        BotCommand(command="lang", description=t("btn_lang", lang)[2:]),
        BotCommand(command="getmyid", description="Telegram ID"),
    ]
    if is_admin:
        cmds.append(BotCommand(command="settings", description=t("btn_settings", lang)[2:]))
    return cmds


async def apply_user_commands(bot, user_id: int, lang: str, *, is_admin: bool) -> None:
    """Set the per-chat command list in the user's selected language."""
    try:
        await bot.set_my_commands(
            commands=_commands_for(lang, is_admin=is_admin),
            scope=BotCommandScopeChat(chat_id=user_id),
        )
    except Exception as exc:  # pragma: no cover — Telegram-side issues only
        log.warning("set_my_commands failed for %s: %s", user_id, exc)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    user_id = message.from_user.id
    client_lang = detect_language_from_client(message.from_user.language_code)

    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, user_id)

        # Bootstrap admin auto-create
        if member is None and user_id == settings.admin_user_id and settings.admin_user_id:
            display = message.from_user.full_name or "admin"
            await db.upsert_member(
                conn,
                user_id=user_id,
                display_name=display,
                language=client_lang,
                is_admin=True,
                created_by=user_id,
            )
            member = await db.get_member(conn, user_id)
            await db.audit(
                conn, user_id=user_id, account_id=None,
                action="bootstrap_admin", allowed=True,
            )

        if member is None:
            # Stranger lockout — minimal response, audit, stop.
            await message.answer(t("lockout", client_lang))
            await db.audit(
                conn, user_id=user_id, account_id=None,
                action="start", allowed=False, reason="not_member",
            )
            return

        lang = member["language"] or client_lang
        is_admin = bool(member["is_admin"])

    await apply_user_commands(message.bot, user_id, lang, is_admin=is_admin)
    await message.answer(
        f"{t('welcome_title', lang)}\n\n{mdv2_escape(t('welcome_body', lang))}",
        parse_mode="MarkdownV2",
    )
    await message.answer("/menu")


# ---------------------------------------------------------------------------
# /lang
# ---------------------------------------------------------------------------


@router.message(Command("lang"))
async def cmd_lang(message: Message) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, message.from_user.id)
        if member is None:
            await message.answer(t("lockout", "en"))
            await db.audit(
                conn, user_id=message.from_user.id, account_id=None,
                action="lang", allowed=False, reason="not_member",
            )
            return
        lang = member["language"]
    await message.answer(t("pick_language", lang), reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang:set:"))
async def cb_set_language(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    new_lang = cb.data.split(":")[2]
    if new_lang not in SUPPORTED_LANGUAGES:
        await cb.answer("invalid", show_alert=False)
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
        if member is None:
            await cb.answer(t("lockout", "en"), show_alert=True)
            return
        await db.set_language(conn, cb.from_user.id, new_lang)
        is_admin = bool(member["is_admin"])
    await apply_user_commands(cb.bot, cb.from_user.id, new_lang, is_admin=is_admin)
    await cb.message.answer(t("language_set", new_lang))
    await cb.answer()


# ---------------------------------------------------------------------------
# /getmyid (always available, even to strangers — it's just their ID)
# ---------------------------------------------------------------------------


@router.message(Command("getmyid"))
async def cmd_getmyid(message: Message) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    lang = "en"
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, message.from_user.id)
        if member is None and message.from_user.id != settings.admin_user_id:
            # Strangers may still see their own ID — useful for the admin to
            # add them. We DO log it.
            await db.audit(
                conn, user_id=message.from_user.id, account_id=None,
                action="getmyid", allowed=True, reason="stranger",
            )
        elif member is not None:
            lang = member["language"]
    await message.answer(
        t("your_id", lang, user_id=message.from_user.id), parse_mode="MarkdownV2"
    )


# ---------------------------------------------------------------------------
# Catch-all unknown text
# ---------------------------------------------------------------------------


@router.message(F.text & ~F.text.startswith("/"))
async def fallback_text(message: Message) -> None:
    """Free-text messages from non-members get the lockout string only."""
    if message.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, message.from_user.id)
        if member is None and message.from_user.id != settings.admin_user_id:
            await message.answer(t("lockout", "en"))
            await db.audit(
                conn, user_id=message.from_user.id, account_id=None,
                action="text", allowed=False, reason="not_member",
            )
            return
    # Members reach this only when no other handler matched — silently ignore
    # to avoid revealing internal state. Pending-state input is consumed by
    # the trading handler before this catch-all runs.
