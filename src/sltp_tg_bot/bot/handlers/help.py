"""Dynamic /help generator.

``build_help(user_id, language)`` aggregates the user's permissions across
every account they have access to and produces a personalised help string.
Admins see the admin section; non-admins must never see *any* hint that an
admin section exists.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ... import db
from ...config import get_settings
from ...i18n import t
from ...utils import mdv2_escape

router = Router(name="help")


async def build_help(user_id: int, language: str) -> str:
    """Build a personalised help message for ``user_id`` in ``language``."""
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, user_id)
        if member is None:
            # Stranger lockout — never reached via /help (gated upstream),
            # but defensive: produce nothing useful.
            return mdv2_escape(t("lockout", language))

        is_admin = bool(member["is_admin"])
        accounts = await db.list_accounts_for_user(conn, user_id)
        roles = await db.aggregated_roles_for_user(conn, user_id)

    if not accounts and not is_admin:
        return mdv2_escape(t("help_no_access", language))

    sections: list[str] = [t("help_title", language), ""]
    sections.append(t("help_navigation", language))
    sections.append("")
    sections.append(t("help_reading", language))

    if db.ROLE_VIEW_CLOSE in roles or db.ROLE_FULL in roles or is_admin:
        sections.append("")
        sections.append(t("help_closing", language))

    if db.ROLE_FULL in roles or is_admin:
        sections.append("")
        sections.append(t("help_sltp", language))
        sections.append("")
        sections.append(t("help_be", language))
        sections.append("")
        sections.append(t("help_emergency", language))

    if is_admin:
        sections.append("")
        sections.append(t("help_admin", language))

    sections.append("")
    sections.append(t("help_alerts", language))
    sections.append("")
    sections.append(t("help_tips", language))

    if accounts:
        sections.append("")
        sections.append(t("help_accounts_label", language))
        for a in accounts:
            sections.append(f"• `{mdv2_escape(a['alias'])}`")

    # Render: section text is already partly Markdown (asterisks/backticks),
    # so we DO NOT mdv2_escape the whole blob — escape only dynamic data above.
    return "\n".join(sections)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, message.from_user.id)
        if member is None and message.from_user.id != settings.admin_user_id:
            await message.answer(t("lockout", "en"))
            await db.audit(
                conn,
                user_id=message.from_user.id,
                account_id=None,
                action="help",
                allowed=False,
                reason="not_member",
            )
            return
        lang = (member["language"] if member else "en")
    text = await build_help(message.from_user.id, lang)
    await message.answer(text, parse_mode="MarkdownV2")


@router.callback_query(F.data == "menu:help")
async def cb_help(cb) -> None:  # type: ignore[no-untyped-def]
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
    lang = member["language"] if member else "en"
    text = await build_help(cb.from_user.id, lang)
    await cb.message.answer(text, parse_mode="MarkdownV2")
    await cb.answer()
