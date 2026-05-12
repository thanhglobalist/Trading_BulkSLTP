"""Admin-only flows: team mgmt, account mgmt, audit log, broadcast.

Every entry point checks ``require_admin`` first; non-admins receive the
generic ``err_not_allowed`` string and an audit row — never a hint that the
section exists.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ... import db
from ...config import get_settings
from ...i18n import t
from ...utils import generate_ea_token, mdv2_escape, truncate
from ..auth import can_remove_or_demote_admin, require_admin
from ..keyboards import (
    account_actions_kb,
    accounts_list_kb,
    admin_settings_kb,
    perm_grid_kb,
)

# Pending rename flow uses the existing ``sessions.pending_state`` DB column
# (same pattern as ``adm_add_user_id`` / ``adm_add_display``). State string:
_STATE_RENAME = "adm_rename_account"

# Validation: 1–32 chars, alnum/dash/underscore only. Matches the EA token
# convention and avoids issues with MarkdownV2 rendering of the alias.
_ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


async def _is_rename_state(message: Message) -> bool:
    """Decorator-level filter: matches only when user is in rename flow.

    aiogram 3.x calls async filter functions before dispatching the handler,
    so returning ``False`` here lets aiogram try the NEXT registered handler.
    Filtering inside the handler body would consume the update.
    """
    if message.from_user is None or message.text is None:
        return False
    if message.text.startswith("/"):
        return False
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        sess = await db.get_session(conn, message.from_user.id)
    return bool(sess and sess["pending_state"] == _STATE_RENAME)


log = logging.getLogger(__name__)
router = Router(name="admin")


# ---------------------------------------------------------------------------
# Rename-flow text capture
#
# REGISTERED FIRST INTENTIONALLY: aiogram dispatches handlers within a router
# in registration order, picking the first whose filters match. The existing
# ``adm_capture_display`` (below) uses a broad ``F.text`` filter, so it would
# otherwise swallow the rename text input before we could see it. Putting
# this handler first — with a state-aware async filter — lets aiogram skip
# us cleanly when no rename is pending.
# ---------------------------------------------------------------------------


@router.message(F.text, _is_rename_state)
async def msg_consume_rename(message: Message) -> None:
    """Apply rename from inline Rename flow."""
    if message.from_user is None or message.text is None:
        return

    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        sess = await db.get_session(conn, message.from_user.id)
        if not sess or sess["pending_state"] != _STATE_RENAME:
            return

        if not await require_admin(conn, user_id=message.from_user.id, action="rename_account_apply"):
            await db.set_pending_state(conn, user_id=message.from_user.id, state=None, args=None)
            await message.answer(t("err_not_allowed", "en"), parse_mode=None)
            return

        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"] if member else "en"

        args = json.loads(sess["pending_args_json"]) if sess["pending_args_json"] else {}
        account_id = args.get("account_id")
        account = await db.get_account_by_id(conn, account_id) if account_id else None
        if account is None:
            await db.set_pending_state(conn, user_id=message.from_user.id, state=None, args=None)
            await message.answer(t("admin_account_not_found", lang), parse_mode=None)
            return

        new_alias = message.text.strip()
        await _do_rename(
            conn=conn,
            actor=message.from_user.id,
            old_alias=account["alias"],
            new_alias=new_alias,
            lang=lang,
            reply=message.answer,
        )
        await db.set_pending_state(conn, user_id=message.from_user.id, state=None, args=None)


@router.message(Command("renameaccount"))
async def cmd_rename_account(message: Message) -> None:
    """Typed shortcut: /renameaccount <old_alias> <new_alias>"""
    if message.from_user is None or message.text is None:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /renameaccount <old_alias> <new_alias>", parse_mode=None)
        return

    old_alias, new_alias = parts[1].strip(), parts[2].strip()
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=message.from_user.id, action="adm_rename_account"):
            await message.answer(t("err_not_allowed", "en"), parse_mode=None)
            return
        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"] if member else "en"

        await _do_rename(
            conn=conn,
            actor=message.from_user.id,
            old_alias=old_alias,
            new_alias=new_alias,
            lang=lang,
            reply=message.answer,
        )


async def _do_rename(
    *,
    conn,
    actor: int,
    old_alias: str,
    new_alias: str,
    lang: str,
    reply,
) -> None:
    if not _ALIAS_RE.match(new_alias):
        await reply(t("admin_rename_invalid", lang), parse_mode=None)
        return
    try:
        account_id = await db.rename_account(conn, old_alias=old_alias, new_alias=new_alias)
    except db.AccountNotFoundError:
        await reply(t("admin_account_not_found", lang), parse_mode=None)
        return
    except db.AliasConflictError:
        await reply(t("admin_rename_taken", lang, alias=new_alias), parse_mode=None)
        return

    await db.audit(
        conn,
        user_id=actor,
        account_id=account_id,
        action="adm_rename_account",
        allowed=True,
        reason=f"{old_alias}->{new_alias}",
    )
    await reply(t("admin_rename_ok", lang, old=old_alias, new=new_alias), parse_mode=None)


@router.message(Command("addaccount"))
async def cmd_add_account(message: Message) -> None:
    if message.from_user is None or message.text is None:
        return
    settings = get_settings()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /addaccount <alias>")
        return
    alias = parts[1].strip()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=message.from_user.id, action="add_account"):
            await message.answer(t("err_not_allowed", "en"))
            return
        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"]
        try:
            account_id, token = await db.add_account(conn, alias=alias)
        except Exception as exc:
            await message.answer(f"Failed: {exc}")
            return
        await db.audit(
            conn, user_id=message.from_user.id, account_id=account_id,
            action="add_account", allowed=True, reason=alias,
        )
    await message.answer(
        t("admin_account_added", lang, token=mdv2_escape(token)),
        parse_mode=None,
    )


@router.message(Command("rotate"))
async def cmd_rotate(message: Message) -> None:
    if message.from_user is None or message.text is None:
        return
    settings = get_settings()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /rotate <alias>")
        return
    alias = parts[1].strip()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=message.from_user.id, action="rotate_token"):
            await message.answer(t("err_not_allowed", "en"))
            return
        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"]
        token = await db.rotate_account_token(conn, alias)
        if token is None:
            await message.answer(f"Unknown alias: {alias}")
            return
        await db.audit(
            conn, user_id=message.from_user.id, account_id=None,
            action="rotate_token", allowed=True, reason=alias,
        )
    await message.answer(
        t("admin_token_rotated", lang, token=mdv2_escape(token)),
        parse_mode=None,
    )


# ---------------------------------------------------------------------------
# Pause / resume members (with at-least-one-admin invariant)
# ---------------------------------------------------------------------------


@router.message(Command("pause"))
async def cmd_pause(message: Message) -> None:
    await _toggle_pause(message, paused=True)


@router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    await _toggle_pause(message, paused=False)


async def _toggle_pause(message: Message, *, paused: bool) -> None:
    if message.from_user is None or message.text is None:
        return
    settings = get_settings()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /pause <user_id>")
        return
    try:
        target = int(parts[1].strip())
    except ValueError:
        await message.answer("user_id must be numeric")
        return
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=message.from_user.id, action="pause"):
            await message.answer(t("err_not_allowed", "en"))
            return
        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"]
        if paused and not await can_remove_or_demote_admin(conn, target):
            await message.answer(t("err_last_admin", lang))
            return
        await db.set_member_paused(conn, target, paused)
        await db.audit(
            conn, user_id=message.from_user.id, account_id=None,
            action="pause" if paused else "resume", allowed=True, reason=str(target),
        )
    await message.answer("✅")


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------



@router.callback_query(F.data.startswith("acctadm:open:"))
async def cb_account_open(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    try:
        account_id = int(cb.data.rsplit(":", 1)[1])
    except Exception:
        await cb.answer()
        return

    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="admin_account_open"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"]
        acc = await db.get_account_by_id(conn, account_id)
        if acc is None:
            await cb.answer("Account not found", show_alert=True)
            return

    await cb.message.answer(
        f"Account: {acc['alias']}\n\nPick an action below.",
        parse_mode=None,
        reply_markup=account_actions_kb(account_id, lang),
    )
    await cb.answer()

@router.callback_query((F.data == "admin:audit") | (F.data == "admin_audit"))
async def cb_audit(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="audit_view"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"]
        rows = await db.list_audit(conn, limit=20)

    lines = [f"*{mdv2_escape(t('admin_audit', lang))}*", ""]
    for r in rows:
        flag = "✅" if r["allowed"] else "🚫"
        lines.append(
            f"{flag} `{mdv2_escape(r['created_at'])}` "
            f"u=`{r['user_id']}` a=`{r['account_id']}` "
            f"`{mdv2_escape(r['action'])}` "
            f"{mdv2_escape(truncate(r['reason'] or '', 40))}"
        )
    if not rows:
        lines.append("(empty)")
    await cb.message.answer("\n".join(lines), parse_mode=None)
    await cb.answer()


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    if message.from_user is None or message.text is None:
        return
    settings = get_settings()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /broadcast <message>")
        return
    body = parts[1]
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=message.from_user.id, action="broadcast"):
            await message.answer(t("err_not_allowed", "en"))
            return
        members = await db.list_members(conn)
        await db.audit(
            conn, user_id=message.from_user.id, account_id=None,
            action="broadcast", allowed=True, reason=truncate(body, 80),
        )
    sent = 0
    for m in members:
        if m["is_paused"]:
            continue
        try:
            await message.bot.send_message(m["user_id"], body)
            sent += 1
        except Exception as exc:
            log.warning("broadcast to %s failed: %s", m["user_id"], exc)
    await message.answer(f"✅ Sent to {sent} members.")


@router.callback_query((F.data == "admin:broadcast") | (F.data == "admin_broadcast"))
async def cb_broadcast_hint(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="broadcast_hint"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
    await cb.message.answer("Use /broadcast [message] to send to all members.")
    await cb.answer()


@router.callback_query((F.data == "admin:team") | (F.data == "admin_team"))
async def cb_team(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="admin_team"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"] if member else "en"
        members = await db.list_members(conn)

    lines = [f"*{mdv2_escape(t('admin_team', lang))}*", ""]
    for m in members:
        flag = "👑" if m["is_admin"] else ("⏸" if m["is_paused"] else "•")
        lines.append(f"{flag} {m['user_id']} {m['display_name']} [{m['language']}]")
    lines.append("")
    lines.append("Use /addmember to add. Use /pause <id> /resume <id>.")
    await cb.message.answer("\n".join(lines), parse_mode=None)
    await cb.answer()


@router.callback_query((F.data == "admin:accounts") | (F.data == "admin_accounts"))
async def cb_accounts(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="admin_accounts"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"] if member else "en"
        accounts = await db.list_all_accounts(conn)

    lines = [f"*{mdv2_escape(t('admin_accounts', lang))}*", ""]
    for a in accounts:
        last = a["last_seen_at"] or "—"
        lines.append(f"• {a['alias']} [id={a['id']}] last_seen={last}")
    if not accounts:
        lines.append(t("admin_accounts_empty", lang))
    lines.append("")
    lines.append(t("admin_accounts_tap_hint", lang))
    await cb.message.answer("\n".join(lines), parse_mode=None, reply_markup=accounts_list_kb(accounts, lang))
    await cb.answer()




@router.message(F.text & ~F.text.startswith("/"))
async def consume_pending_rename(message: Message) -> None:
    if message.from_user is None or message.text is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=message.from_user.id, action="rename_account_apply"):
            return

        sess = await db.get_session(conn, message.from_user.id)
        if not sess or sess.get("pending_state") != "adm_rename_account":
            return

        import json
        args = json.loads(sess["pending_args_json"]) if sess.get("pending_args_json") else {}
        old_alias = args.get("account_alias")
        if not old_alias:
            await db.set_pending_state(conn, user_id=message.from_user.id, state=None, args=None)
            await message.answer("Rename context expired. Please try again.")
            return

        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"] if member else "en"
        new_alias = message.text.strip()

        await _do_rename(
            conn=conn,
            actor=message.from_user.id,
            old_alias=old_alias,
            new_alias=new_alias,
            lang=lang,
            reply=message.answer,
        )
        await db.set_pending_state(conn, user_id=message.from_user.id, state=None, args=None)


@router.callback_query(F.data.startswith("acctadm:rename:"))
async def cb_account_rename(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    try:
        account_id = int(cb.data.rsplit(":", 1)[1])
    except Exception:
        await cb.answer()
        return

    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="rename_account_start"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"] if member else "en"
        acc = await db.get_account_by_id(conn, account_id)
        if acc is None:
            await cb.answer("Account not found", show_alert=True)
            return

        await db.set_pending_state(
            conn,
            user_id=cb.from_user.id,
            state="adm_rename_account",
            args={"account_alias": acc["alias"]},
        )

    await cb.message.answer(
        f"Send new alias for '{acc['alias']}' (1-32, a-z A-Z 0-9 - _)."
    )
    await cb.answer()
