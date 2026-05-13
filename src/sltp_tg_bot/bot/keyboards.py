"""Inline keyboard factories.

All callback data follows the convention ``"<domain>:<action>:<arg1>:<arg2>"``,
e.g. ``"acct:pick:42"``, ``"trade:close_all:42"``, ``"perm:set:123:42:full"``.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

from typing import Iterable, Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .. import db
from ..i18n import SUPPORTED_LANGUAGES, language_label, t


# ---------------------------------------------------------------------------
# Account picker
# ---------------------------------------------------------------------------


def account_picker_kb(accounts: Sequence, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for acc in accounts:
        kb.button(text=acc["alias"], callback_data=f"acct:pick:{acc['id']}")
    kb.adjust(1)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Main menu (role-gated)
# ---------------------------------------------------------------------------


def main_menu_kb(role: str, *, is_admin: bool, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    # View tier — always present
    kb.button(text=t("btn_status", lang), callback_data="menu:status")
    kb.button(text=t("btn_positions", lang), callback_data="menu:positions")

    if db.role_at_least(role, db.ROLE_VIEW_CLOSE):
        kb.button(text=t("btn_close", lang), callback_data="menu:close")

    if db.role_at_least(role, db.ROLE_FULL):
        kb.button(text=t("btn_sltp", lang), callback_data="menu:sltp")
        kb.button(text=t("btn_be", lang), callback_data="menu:be")
        kb.button(text=t("btn_panic", lang), callback_data="menu:panic")

    kb.button(text=t("btn_help", lang), callback_data="menu:help")
    kb.button(text=t("btn_lang", lang), callback_data="menu:lang")
    kb.button(text=t("btn_switch_account", lang), callback_data="menu:switch")

    if is_admin:
        kb.button(text=t("btn_settings", lang), callback_data="menu:settings")

    # Layout: 2 per row for compact mobile UI
    kb.adjust(2)
    return kb.as_markup()


def close_submenu_kb(account_id: int, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("btn_close_all", lang), callback_data=f"trade:close_all:{account_id}")
    kb.button(text=t("btn_close_buys", lang), callback_data=f"trade:close_buys:{account_id}")
    kb.button(text=t("btn_close_sells", lang), callback_data=f"trade:close_sells:{account_id}")
    kb.button(text=t("btn_back", lang), callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def sltp_submenu_kb(account_id: int, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("btn_sl", lang), callback_data=f"trade:sl:{account_id}")
    kb.button(text=t("btn_tp", lang), callback_data=f"trade:tp:{account_id}")
    kb.button(text=t("btn_sloff", lang), callback_data=f"trade:sloff:{account_id}")
    kb.button(text=t("btn_tpoff", lang), callback_data=f"trade:tpoff:{account_id}")
    kb.button(text=t("btn_back", lang), callback_data="menu:home")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Confirm / cancel
# ---------------------------------------------------------------------------


def confirm_kb(token: str, lang: str) -> InlineKeyboardMarkup:
    """``token`` is an opaque payload identifying the queued action."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t("btn_confirm", lang), callback_data=f"cfm:ok:{token}")
    kb.button(text=t("btn_cancel", lang), callback_data=f"cfm:no:{token}")
    kb.adjust(2)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Language picker
# ---------------------------------------------------------------------------


def language_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code in SUPPORTED_LANGUAGES:
        kb.button(text=language_label(code), callback_data=f"lang:set:{code}")
    kb.adjust(1)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Help v2 (v1.0.3) — role-aware help menu
# ---------------------------------------------------------------------------


def help_home_kb(*, role: str, is_admin: bool, lang: str) -> InlineKeyboardMarkup:
    """Home grid for ``/help`` and the ``menu:help`` callback.

    Topics are gated by role exactly like the main menu. Strangers (no
    membership at all) get a much smaller grid via :func:`help_stranger_kb`.
    """
    kb = InlineKeyboardBuilder()

    # Always visible to known members
    kb.button(text=t("help_v2_btn_navigation", lang), callback_data="help:nav")
    kb.button(text=t("help_v2_btn_reading", lang),    callback_data="help:reading")

    if db.role_at_least(role, db.ROLE_VIEW_CLOSE):
        kb.button(text=t("help_v2_btn_closing", lang), callback_data="help:closing")

    if db.role_at_least(role, db.ROLE_FULL):
        kb.button(text=t("help_v2_btn_sltp", lang),      callback_data="help:sltp")
        kb.button(text=t("help_v2_btn_be", lang),        callback_data="help:be")
        kb.button(text=t("help_v2_btn_emergency", lang), callback_data="help:emergency")

    kb.button(text=t("help_v2_btn_alerts", lang),    callback_data="help:alerts")
    kb.button(text=t("help_v2_btn_roles", lang),     callback_data="help:roles")
    kb.button(text=t("help_v2_btn_commands", lang),  callback_data="help:commands")

    if is_admin:
        kb.button(text=t("help_v2_btn_admin", lang), callback_data="help:admin")

    kb.button(
        text=t("help_v2_btn_lang", lang).format(label=language_label(lang)),
        callback_data="help:lang",
    )
    kb.button(text=t("help_v2_back_to_menu", lang),  callback_data="menu:home")

    kb.adjust(2)
    return kb.as_markup()


def help_stranger_kb(lang: str) -> InlineKeyboardMarkup:
    """Slim grid for users with no team membership."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t("help_v2_btn_roles", lang),    callback_data="help:roles")
    kb.button(text=t("help_v2_btn_commands", lang), callback_data="help:commands")
    kb.button(
        text=t("help_v2_btn_lang", lang).format(label=language_label(lang)),
        callback_data="help:lang",
    )
    kb.adjust(2, 1)
    return kb.as_markup()


def help_topic_kb(
    topic: str, *, role: str, is_admin: bool, lang: str
) -> InlineKeyboardMarkup:
    """Footer keyboard on each topic page.

    Some topics expose a deep-link button (e.g. "Open SL/TP screen") that
    routes back into the existing main-menu callbacks. The deep links are
    only added when the viewer's role actually permits the action — we
    don't tease screens they can't open.
    """
    kb = InlineKeyboardBuilder()

    if topic == "nav":
        kb.button(text=t("help_v2_btn_switch_account", lang), callback_data="menu:switch")
    elif topic == "reading":
        kb.button(text=t("help_v2_btn_open_status", lang),    callback_data="menu:status")
        kb.button(text=t("help_v2_btn_open_positions", lang), callback_data="menu:positions")
    elif topic == "closing" and db.role_at_least(role, db.ROLE_VIEW_CLOSE):
        kb.button(text=t("help_v2_btn_open_close", lang), callback_data="menu:close")
    elif topic == "sltp" and db.role_at_least(role, db.ROLE_FULL):
        kb.button(text=t("help_v2_btn_open_sltp", lang), callback_data="menu:sltp")
    elif topic == "be" and db.role_at_least(role, db.ROLE_FULL):
        kb.button(text=t("help_v2_btn_open_be", lang), callback_data="menu:be")
    elif topic == "roles":
        kb.button(text=t("help_v2_btn_switch_account", lang), callback_data="menu:switch")
    elif topic == "admin" and is_admin:
        kb.button(text=t("help_v2_btn_open_settings", lang), callback_data="menu:settings")

    kb.button(text=t("help_v2_back_to_help", lang), callback_data="help:home")
    # 2 per row when there's a deep link, else just the back button
    kb.adjust(2, 1) if topic in {"reading"} else kb.adjust(1)
    return kb.as_markup()


def help_lang_kb(lang: str) -> InlineKeyboardMarkup:
    """Language picker rendered inside the help screen.

    Uses a distinct callback prefix ``helplang:set:<code>`` so it does NOT
    collide with the global ``/lang`` flow's ``lang:set:<code>`` (which
    answers with a confirmation message instead of re-rendering help).
    """
    kb = InlineKeyboardBuilder()
    for code in SUPPORTED_LANGUAGES:
        kb.button(text=language_label(code), callback_data=f"helplang:set:{code}")
    kb.button(text=t("help_v2_back_to_help", lang), callback_data="help:home")
    kb.adjust(1)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Admin keyboards
# ---------------------------------------------------------------------------


def admin_settings_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("admin_team", lang), callback_data="admin:team")
    kb.button(text=t("admin_accounts", lang), callback_data="menu:settings")
    kb.button(text=t("admin_audit", lang), callback_data="admin:audit")
    kb.button(text=t("admin_broadcast", lang), callback_data="admin:broadcast")
    kb.button(text=t("btn_back", lang), callback_data="menu:home")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def accounts_list_kb(accounts: Iterable, lang: str) -> InlineKeyboardMarkup:
    """Tap an account to drill into its per-account action menu."""
    kb = InlineKeyboardBuilder()
    for acc in accounts:
        kb.button(
            text=f"🏦 {acc['alias']}",
            callback_data=f"acct:pick:{acc['id']}",
        )
    kb.button(text=t("btn_back", lang), callback_data="menu:settings")
    kb.adjust(1)
    return kb.as_markup()


def account_actions_kb(account_id: int, lang: str) -> InlineKeyboardMarkup:
    """Actions available on a single selected account (admin only)."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text=t("admin_rename_btn", lang),
        callback_data=f"acctadm:rename:{account_id}",
    )
    kb.button(
        text=t("admin_rotate_btn", lang),
        callback_data=f"acctadm:rotate:{account_id}",
    )
    kb.button(text=t("btn_back", lang), callback_data="menu:settings")
    kb.adjust(2, 1)
    return kb.as_markup()


def perm_grid_kb(
    accounts: Iterable, current: dict[int, str], target_user_id: int, lang: str
) -> InlineKeyboardMarkup:
    """Permission editor grid for ``target_user_id``.

    ``current`` maps ``account_id`` → role string ('none'|'view'|'view_close'|'full').
    """
    kb = InlineKeyboardBuilder()
    role_seq = ("none", "view", "view_close", "full")
    role_label = {
        "none": "—",
        "view": "View",
        "view_close": "V+Close",
        "full": "Full",
    }
    for acc in accounts:
        cur_role = current.get(acc["id"], "none")
        # Header row: alias
        kb.row(InlineKeyboardButton(text=acc["alias"], callback_data="noop"))
        buttons: list[InlineKeyboardButton] = []
        for r in role_seq:
            mark = "● " if r == cur_role else ""
            buttons.append(
                InlineKeyboardButton(
                    text=f"{mark}{role_label[r]}",
                    callback_data=f"perm:set:{target_user_id}:{acc['id']}:{r}",
                )
            )
        kb.row(*buttons)
    kb.row(
        InlineKeyboardButton(
            text="✅ Save",
            callback_data=f"perm:save:{target_user_id}",
        ),
        InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="menu:home"),
    )
    return kb.as_markup()
