"""Help v2 — role-aware, multi-topic, multilingual help center.

Entry points:
  * ``/help``  (typed command)
  * ``menu:help`` callback (❓ Help button on the main menu)

Surface:
  * Home grid → topic pages → deep links into the matching screen
  * Inline language switcher (``helplang:set:<code>``) that refreshes
    setMyCommands for the chat scope and re-renders help in the new
    language without leaving the screen.
  * Strangers (no team_members row) see a slim "send your ID to admin"
    home with their Telegram ID rendered inline.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ... import db
from ...config import get_settings
from ...i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import (
    help_home_kb,
    help_lang_kb,
    help_stranger_kb,
    help_topic_kb,
)
from .common import apply_user_commands

router = Router(name="help")
log = logging.getLogger(__name__)

# Plain text — the bot default is HTML, which would otherwise eat "<"/">"
# characters in command signatures like ``/rename <old> <new>``. The help
# strings already use unicode icons + indentation for structure.
PARSE_MODE = None

# Map ``help:<topic>`` callback suffix → (body i18n key, gate fn)
# ``gate`` returns True if the user is allowed to read the page. When False
# we silently fall back to the home grid; this is purely defensive — buttons
# for gated topics are not shown on the home grid in the first place.
_TOPICS: dict[str, str] = {
    "nav":       "help_v2_nav",
    "reading":   "help_v2_reading",
    "closing":   "help_v2_closing",
    "sltp":      "help_v2_sltp",
    "be":        "help_v2_be",
    "emergency": "help_v2_emergency",
    "alerts":    "help_v2_alerts",
    "roles":     "help_v2_roles",
    "admin":     "help_v2_admin",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _resolve_lang_role(conn, user_id: int) -> tuple[str, str, bool, bool]:
    """Return ``(lang, role, is_admin, is_member)``.

    ``role`` is resolved against the user's *currently selected* account if
    one is set in their session, otherwise the highest role across all the
    accounts they have any access to. This keeps help useful even for users
    who open ``/help`` as their very first action.
    """
    member = await db.get_member(conn, user_id)
    if member is None:
        return ("en", db.ROLE_NONE, False, False)

    lang = member["language"] or "en"
    is_admin = bool(member["is_admin"])
    role = db.ROLE_FULL if is_admin else db.ROLE_NONE

    if not is_admin:
        sess = await db.get_session(conn, user_id)
        account_id = sess["current_account_id"] if sess else None
        if account_id:
            role = await db.get_role(
                conn, user_id=user_id, account_id=account_id
            )
        else:
            # Fall back to the highest role they hold on any account so the
            # home grid still shows the right buttons before they pick.
            accounts = await db.list_accounts_for_user(conn, user_id)
            for acc in accounts:
                r = await db.get_role(
                    conn, user_id=user_id, account_id=acc["id"]
                )
                if db.role_at_least(r, role):
                    role = r

    return (lang, role, is_admin, True)


async def _render_home(*, lang: str, role: str, is_admin: bool, is_member: bool,
                       user_id: int) -> tuple[str, object]:
    """Build the home text + keyboard for the resolved viewer."""
    if not is_member:
        text = (
            f"{t('help_v2_stranger_title', lang)}\n\n"
            f"{t('help_v2_stranger_body', lang).format(user_id=user_id)}"
        )
        return text, help_stranger_kb(lang)

    text = f"{t('help_v2_title', lang)}\n\n{t('help_v2_body', lang)}"
    return text, help_home_kb(role=role, is_admin=is_admin, lang=lang)


def _topic_text(topic: str, lang: str, *, is_admin: bool) -> Optional[str]:
    key = _TOPICS.get(topic)
    if key is None:
        return None
    body = t(key, lang)
    # The Commands list page concatenates the admin extra block when admin.
    if topic == "commands":  # not in _TOPICS — handled below
        return None
    return body


def _commands_text(lang: str, *, is_admin: bool) -> str:
    body = t("help_v2_commands_user", lang)
    if is_admin:
        body += t("help_v2_commands_admin_extra", lang)
    return body


async def _safe_edit_or_send(cb: CallbackQuery, text: str, kb) -> None:
    """Edit the originating message when possible, else send a new one.

    Telegram rejects edits when the new content is identical or the message
    is too old; in both cases we fall back to sending a fresh message so the
    user always sees a response.
    """
    msg = cb.message
    if msg is None:
        return
    try:
        await msg.edit_text(text, parse_mode=PARSE_MODE, reply_markup=kb)
        return
    except Exception as exc:  # aiogram raises TelegramBadRequest, etc.
        log.debug("help edit failed (%s); sending new message", exc)
        try:
            await msg.answer(text, parse_mode=PARSE_MODE, reply_markup=kb)
        except Exception as exc2:
            log.warning("help send fallback failed: %s", exc2)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        lang, role, is_admin, is_member = await _resolve_lang_role(
            conn, message.from_user.id
        )
        await db.audit(
            conn, user_id=message.from_user.id, account_id=None,
            action="help", allowed=True,
            reason=None if is_member else "stranger",
        )
    text, kb = await _render_home(
        lang=lang, role=role, is_admin=is_admin,
        is_member=is_member, user_id=message.from_user.id,
    )
    await message.answer(text, parse_mode=PARSE_MODE, reply_markup=kb)


@router.callback_query(F.data == "menu:help")
async def cb_menu_help(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        lang, role, is_admin, is_member = await _resolve_lang_role(
            conn, cb.from_user.id
        )
        await db.audit(
            conn, user_id=cb.from_user.id, account_id=None,
            action="menu_help", allowed=True,
            reason=None if is_member else "stranger",
        )
    text, kb = await _render_home(
        lang=lang, role=role, is_admin=is_admin,
        is_member=is_member, user_id=cb.from_user.id,
    )
    # Always send a fresh message for the button entry point — keeps the
    # previous main menu intact in scrollback.
    if cb.message is not None:
        await cb.message.answer(text, parse_mode=PARSE_MODE, reply_markup=kb)
    await cb.answer()


# ---------------------------------------------------------------------------
# Home navigation
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "help:home")
async def cb_help_home(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        lang, role, is_admin, is_member = await _resolve_lang_role(
            conn, cb.from_user.id
        )
    text, kb = await _render_home(
        lang=lang, role=role, is_admin=is_admin,
        is_member=is_member, user_id=cb.from_user.id,
    )
    await _safe_edit_or_send(cb, text, kb)
    await cb.answer()


# ---------------------------------------------------------------------------
# Topic pages
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "help:commands")
async def cb_help_commands(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        lang, role, is_admin, _is_member = await _resolve_lang_role(
            conn, cb.from_user.id
        )
    text = _commands_text(lang, is_admin=is_admin)
    kb = help_topic_kb("commands", role=role, is_admin=is_admin, lang=lang)
    await _safe_edit_or_send(cb, text, kb)
    await cb.answer()


@router.callback_query(F.data.startswith("help:") & ~F.data.in_(
    {"help:home", "help:lang", "help:commands"}
))
async def cb_help_topic(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    topic = cb.data.split(":", 1)[1]
    if topic not in _TOPICS:
        await cb.answer()
        return

    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        lang, role, is_admin, is_member = await _resolve_lang_role(
            conn, cb.from_user.id
        )

    # Defensive gate — buttons shouldn't appear for unauthorized topics but
    # we re-check on the callback in case the user kept an old keyboard.
    if topic == "closing" and not db.role_at_least(role, db.ROLE_VIEW_CLOSE):
        await cb.answer()
        return
    if topic in {"sltp", "be", "emergency"} and not db.role_at_least(role, db.ROLE_FULL):
        await cb.answer()
        return
    if topic == "admin" and not is_admin:
        await cb.answer()
        return
    if not is_member and topic not in {"roles"}:
        await cb.answer()
        return

    text = t(_TOPICS[topic], lang)
    kb = help_topic_kb(topic, role=role, is_admin=is_admin, lang=lang)
    await _safe_edit_or_send(cb, text, kb)
    await cb.answer()


# ---------------------------------------------------------------------------
# Inline language switcher
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "help:lang")
async def cb_help_lang(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        lang, _role, _is_admin, _is_member = await _resolve_lang_role(
            conn, cb.from_user.id
        )
    text = t("help_v2_pick_language", lang)
    await _safe_edit_or_send(cb, text, help_lang_kb(lang))
    await cb.answer()


@router.callback_query(F.data.startswith("helplang:set:"))
async def cb_help_lang_set(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    new_lang = cb.data.split(":")[2]
    if new_lang not in SUPPORTED_LANGUAGES:
        await cb.answer()
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
        if member is None:
            # Stranger flipping language is fine — but there's nothing to
            # persist (no team_members row). Just re-render help in EN/JA/VI
            # using the requested lang for THIS session.
            text, kb = await _render_home(
                lang=new_lang, role=db.ROLE_NONE, is_admin=False,
                is_member=False, user_id=cb.from_user.id,
            )
            await _safe_edit_or_send(cb, text, kb)
            await cb.answer()
            return

        await db.set_language(conn, cb.from_user.id, new_lang)
        is_admin = bool(member["is_admin"])
        role = db.ROLE_FULL if is_admin else db.ROLE_NONE
        if not is_admin:
            sess = await db.get_session(conn, cb.from_user.id)
            account_id = sess["current_account_id"] if sess else None
            if account_id:
                role = await db.get_role(
                    conn, user_id=cb.from_user.id, account_id=account_id
                )

    # Refresh per-chat setMyCommands so the / autocomplete localizes too.
    await apply_user_commands(cb.bot, cb.from_user.id, new_lang, is_admin=is_admin)

    text, kb = await _render_home(
        lang=new_lang, role=role, is_admin=is_admin,
        is_member=True, user_id=cb.from_user.id,
    )
    await _safe_edit_or_send(cb, text, kb)
    await cb.answer(t("language_set", new_lang), show_alert=False)
