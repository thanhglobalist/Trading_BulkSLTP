"""Main menu, account picker, and the home screen.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ... import db
from ...config import get_settings
from ...i18n import t
from ..formatters import render_header
from ..keyboards import (
    account_picker_kb,
    close_submenu_kb,
    main_menu_kb,
    sltp_submenu_kb,
)

router = Router(name="menu")


async def _get_member_or_lock(conn, user_id: int):
    member = await db.get_member(conn, user_id)
    return member


# ---------------------------------------------------------------------------
# /accounts  → account picker
# ---------------------------------------------------------------------------


@router.message(Command("accounts"))
async def cmd_accounts(message: Message) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await _get_member_or_lock(conn, message.from_user.id)
        if member is None:
            await message.answer(t("lockout", "en"))
            await db.audit(
                conn, user_id=message.from_user.id, account_id=None,
                action="accounts", allowed=False, reason="not_member",
            )
            return
        lang = member["language"]
        accounts = await db.list_accounts_for_user(conn, message.from_user.id)
    if not accounts:
        await message.answer(t("no_accounts", lang))
        return
    await message.answer(t("pick_account", lang), reply_markup=account_picker_kb(accounts, lang))


# ---------------------------------------------------------------------------
# Account chosen → set session, show main menu
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("acct:pick:"))
async def cb_pick_account(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    try:
        account_id = int(cb.data.split(":")[2])
    except (IndexError, ValueError):
        await cb.answer()
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
        if member is None:
            await cb.answer(t("lockout", "en"), show_alert=True)
            return
        # Tenant isolation re-check
        role = await db.get_role(conn, user_id=cb.from_user.id, account_id=account_id)
        if role == db.ROLE_NONE:
            await cb.answer(t("err_not_allowed", member["language"]), show_alert=True)
            await db.audit(
                conn, user_id=cb.from_user.id, account_id=account_id,
                action="menu_pick", allowed=False, reason="no_perm",
            )
            return
        await db.set_session_account(conn, user_id=cb.from_user.id, account_id=account_id)
        account = await db.get_account_by_id(conn, account_id)
        lang = member["language"]
        is_admin = bool(member["is_admin"])

    if account is None:
        await cb.answer()
        return

    header = render_header(
        alias=account["alias"], equity=None, pl=None,
        currency=account["base_currency"] or "USD",
        lang=lang, has_data=False,
    )
    await cb.message.answer(
        header,
        parse_mode="MarkdownV2",
        reply_markup=main_menu_kb(role, is_admin=is_admin, lang=lang),
    )
    await cb.answer()


# ---------------------------------------------------------------------------
# Switch account / Home
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "menu:switch")
async def cb_switch(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
        if member is None:
            await cb.answer(t("lockout", "en"), show_alert=True)
            return
        lang = member["language"]
        accounts = await db.list_accounts_for_user(conn, cb.from_user.id)
    if not accounts:
        await cb.message.answer(t("no_accounts", lang))
    else:
        await cb.message.answer(
            t("pick_account", lang), reply_markup=account_picker_kb(accounts, lang)
        )
    await cb.answer()


@router.callback_query(F.data == "menu:home")
async def cb_home(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
        if member is None:
            await cb.answer(t("lockout", "en"), show_alert=True)
            return
        lang = member["language"]
        is_admin = bool(member["is_admin"])
        sess = await db.get_session(conn, cb.from_user.id)
        account_id = sess["current_account_id"] if sess else None
        if not account_id:
            accounts = await db.list_accounts_for_user(conn, cb.from_user.id)
            await cb.message.answer(
                t("pick_account", lang),
                reply_markup=account_picker_kb(accounts, lang),
            )
            await cb.answer()
            return
        role = await db.get_role(conn, user_id=cb.from_user.id, account_id=account_id)
        account = await db.get_account_by_id(conn, account_id)
    if account is None:
        await cb.answer()
        return
    header = render_header(
        alias=account["alias"], equity=None, pl=None,
        currency=account["base_currency"] or "USD",
        lang=lang, has_data=False,
    )
    await cb.message.answer(
        header,
        parse_mode="MarkdownV2",
        reply_markup=main_menu_kb(role, is_admin=is_admin, lang=lang),
    )
    await cb.answer()


# ---------------------------------------------------------------------------
# Submenus
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "menu:close")
async def cb_close(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
        if member is None:
            await cb.answer(t("lockout", "en"), show_alert=True)
            return
        lang = member["language"]
        sess = await db.get_session(conn, cb.from_user.id)
        account_id = sess["current_account_id"] if sess else None
        if not account_id:
            await cb.answer()
            return
        role = await db.get_role(conn, user_id=cb.from_user.id, account_id=account_id)
        if not db.role_at_least(role, db.ROLE_VIEW_CLOSE):
            await db.audit(
                conn, user_id=cb.from_user.id, account_id=account_id,
                action="menu_close", allowed=False, reason="role",
            )
            await cb.answer(t("err_not_allowed", lang), show_alert=True)
            return
    await cb.message.answer(
        t("btn_close", lang), reply_markup=close_submenu_kb(account_id, lang)
    )
    await cb.answer()


@router.callback_query(F.data == "menu:sltp")
async def cb_sltp_menu(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
        if member is None:
            await cb.answer(t("lockout", "en"), show_alert=True)
            return
        lang = member["language"]
        sess = await db.get_session(conn, cb.from_user.id)
        account_id = sess["current_account_id"] if sess else None
        if not account_id:
            await cb.answer()
            return
        role = await db.get_role(conn, user_id=cb.from_user.id, account_id=account_id)
        if not db.role_at_least(role, db.ROLE_FULL):
            await db.audit(
                conn, user_id=cb.from_user.id, account_id=account_id,
                action="menu_sltp", allowed=False, reason="role",
            )
            await cb.answer(t("err_not_allowed", lang), show_alert=True)
            return
    await cb.message.answer(
        t("btn_sltp", lang), reply_markup=sltp_submenu_kb(account_id, lang)
    )
    await cb.answer()


@router.callback_query(F.data == "menu:lang")
async def cb_menu_lang(cb: CallbackQuery) -> None:
    """Language picker invoked from the main menu."""
    if cb.from_user is None:
        return
    from ..keyboards import language_kb
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        member = await db.get_member(conn, cb.from_user.id)
    lang = member["language"] if member else "en"
    await cb.message.answer(t("pick_language", lang), reply_markup=language_kb())
    await cb.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()


@router.callback_query(F.data == "menu:settings")
async def cb_menu_settings(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        sess = await db.get_session(conn, cb.from_user.id)
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"] if member else "en"

    account_id = sess["current_account_id"] if sess else None
    if not account_id:
        await cb.message.answer("No active account. Use /accounts to pick one.")
        await cb.answer()
        return

    from ..keyboards import account_actions_kb
    await cb.message.answer(
        "Account settings:",
        reply_markup=account_actions_kb(account_id, lang),
        parse_mode=None,
    )
    await cb.answer()
