"""Admin-only flows: team mgmt, account mgmt, audit log, broadcast.

Every entry point checks ``require_admin`` first; non-admins receive the
generic ``err_not_allowed`` string and an audit row — never a hint that the
section exists.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import json
import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ... import db
from ...config import get_settings
from ...i18n import t
from ...utils import generate_ea_token, mdv2_escape, truncate
from ..auth import can_remove_or_demote_admin, require_admin
from ..keyboards import admin_settings_kb, perm_grid_kb

log = logging.getLogger(__name__)
router = Router(name="admin")


# ---------------------------------------------------------------------------
# /settings command
# ---------------------------------------------------------------------------


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=message.from_user.id, action="settings"):
            await message.answer(t("err_not_allowed", "en"))
            return
        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"] if member else "en"
    await message.answer(t("btn_settings", lang), reply_markup=admin_settings_kb(lang))


@router.callback_query(F.data == "menu:settings")
async def cb_settings(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="settings"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"] if member else "en"
    await cb.message.answer(t("btn_settings", lang), reply_markup=admin_settings_kb(lang))
    await cb.answer()


# ---------------------------------------------------------------------------
# Team — list members
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "admin:team")
async def cb_team(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="admin_team"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"]
        members = await db.list_members(conn)

    lines = [f"*{mdv2_escape(t('admin_team', lang))}*", ""]
    for m in members:
        flag = "👑" if m["is_admin"] else ("⏸" if m["is_paused"] else "•")
        lines.append(
            f"{flag} `{m['user_id']}` "
            f"{mdv2_escape(m['display_name'])} "
            f"\\[{mdv2_escape(m['language'])}\\]"
        )
    lines.append("")
    lines.append(f"Use /addmember to add. Use /pause `<id>` /resume `<id>`.")
    await cb.message.answer("\n".join(lines))
    await cb.answer()


# ---------------------------------------------------------------------------
# Add member flow (multi-step)
# ---------------------------------------------------------------------------


@router.message(Command("addmember"))
async def cmd_add_member(message: Message) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=message.from_user.id, action="add_member"):
            await message.answer(t("err_not_allowed", "en"))
            return
        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"]
        await db.set_pending_state(
            conn,
            user_id=message.from_user.id,
            state="adm_add_user_id",
            args={},
        )
    await message.answer(t("admin_ask_user_id", lang))


@router.message(F.text.regexp(r"^\d{5,15}$"))
async def adm_capture_user_id(message: Message) -> None:
    """Capture a numeric ID typed during the addmember flow."""
    if message.from_user is None or message.text is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await db.is_admin(conn, message.from_user.id):
            return
        sess = await db.get_session(conn, message.from_user.id)
        if not sess or sess["pending_state"] != "adm_add_user_id":
            return
        target = int(message.text.strip())
        await db.set_pending_state(
            conn,
            user_id=message.from_user.id,
            state="adm_add_display",
            args={"target_user_id": target},
        )
        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"]
    await message.answer(t("admin_ask_display_name", lang))


@router.message(F.text)
async def adm_capture_display(message: Message) -> None:
    """Capture display name during addmember flow.

    Lower-priority than the numeric ID handler above because aiogram tries
    handlers in registration order; pending_state filtering inside makes it
    safe even if the user is in another flow.
    """
    if message.from_user is None or message.text is None or message.text.startswith("/"):
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await db.is_admin(conn, message.from_user.id):
            return
        sess = await db.get_session(conn, message.from_user.id)
        if not sess or sess["pending_state"] != "adm_add_display":
            return
        args = json.loads(sess["pending_args_json"]) if sess["pending_args_json"] else {}
        target = args.get("target_user_id")
        if target is None:
            await db.set_pending_state(
                conn, user_id=message.from_user.id, state=None, args=None,
            )
            return
        display = message.text.strip()[:64]
        await db.upsert_member(
            conn,
            user_id=target,
            display_name=display,
            language="en",
            is_admin=False,
            created_by=message.from_user.id,
        )
        await db.set_pending_state(
            conn, user_id=message.from_user.id, state=None, args=None,
        )
        await db.audit(
            conn,
            user_id=message.from_user.id,
            account_id=None,
            action="add_member",
            allowed=True,
            reason=f"target={target}",
        )
        member = await db.get_member(conn, message.from_user.id)
        lang = member["language"]
        # Show permission grid
        accounts = await db.list_all_accounts(conn)

    await message.answer(t("admin_member_added", lang))
    if accounts:
        await message.answer(
            t("admin_pick_perms", lang),
            reply_markup=perm_grid_kb(accounts, current={}, target_user_id=target, lang=lang),
        )


# ---------------------------------------------------------------------------
# Permission grid callbacks
# ---------------------------------------------------------------------------


# We track in-flight permission grid edits per admin user.
_PERM_DRAFTS: dict[int, dict[int, dict[int, str]]] = {}
# _PERM_DRAFTS[admin_id][target_user_id] = {account_id: role}


@router.callback_query(F.data.startswith("perm:set:"))
async def cb_perm_set(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    parts = cb.data.split(":")
    if len(parts) != 5:
        await cb.answer()
        return
    try:
        target_uid = int(parts[2])
        account_id = int(parts[3])
    except ValueError:
        await cb.answer()
        return
    role = parts[4]

    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="perm_set"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        accounts = await db.list_all_accounts(conn)

    drafts = _PERM_DRAFTS.setdefault(cb.from_user.id, {}).setdefault(target_uid, {})
    drafts[account_id] = role
    member_lang = "en"
    async with db.connect(settings.db_path) as conn:
        m = await db.get_member(conn, cb.from_user.id)
        if m:
            member_lang = m["language"]

    try:
        await cb.message.edit_reply_markup(
            reply_markup=perm_grid_kb(accounts, drafts, target_uid, member_lang)
        )
    except Exception:
        pass
    await cb.answer()


@router.callback_query(F.data.startswith("perm:save:"))
async def cb_perm_save(cb: CallbackQuery) -> None:
    if cb.from_user is None or cb.data is None:
        return
    try:
        target_uid = int(cb.data.split(":")[2])
    except (IndexError, ValueError):
        await cb.answer()
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="perm_save"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        drafts = _PERM_DRAFTS.get(cb.from_user.id, {}).get(target_uid, {})
        for account_id, role in drafts.items():
            if role == "none":
                await db.revoke_permission(
                    conn, user_id=target_uid, account_id=account_id,
                )
            elif role in db.VALID_ROLES:
                await db.set_permission(
                    conn,
                    user_id=target_uid,
                    account_id=account_id,
                    role=role,
                    granted_by=cb.from_user.id,
                )
            await db.audit(
                conn,
                user_id=cb.from_user.id,
                account_id=account_id,
                action="perm_set",
                allowed=True,
                reason=f"target={target_uid} role={role}",
            )
        m = await db.get_member(conn, cb.from_user.id)
        lang = m["language"] if m else "en"
    _PERM_DRAFTS.get(cb.from_user.id, {}).pop(target_uid, None)
    await cb.message.answer(t("admin_member_added", lang))
    await cb.answer()


# ---------------------------------------------------------------------------
# Accounts: list / add / rotate / remove
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "admin:accounts")
async def cb_accounts(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="admin_accounts"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
        member = await db.get_member(conn, cb.from_user.id)
        lang = member["language"]
        accounts = await db.list_all_accounts(conn)

    lines = [f"*{mdv2_escape(t('admin_accounts', lang))}*", ""]
    for a in accounts:
        last = a["last_seen_at"] or "—"
        lines.append(
            f"• `{mdv2_escape(a['alias'])}` "
            f"\\[id={a['id']}\\] last\\_seen=`{mdv2_escape(last)}`"
        )
    lines.append("")
    lines.append("Use /addaccount `<alias>` to add, /rotate `<alias>` to rotate token.")
    await cb.message.answer("\n".join(lines))
    await cb.answer()


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
        parse_mode="MarkdownV2",
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
        parse_mode="MarkdownV2",
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


@router.callback_query(F.data == "admin:audit")
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
    await cb.message.answer("\n".join(lines))
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


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast_hint(cb: CallbackQuery) -> None:
    if cb.from_user is None:
        return
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        if not await require_admin(conn, user_id=cb.from_user.id, action="broadcast_hint"):
            await cb.answer(t("err_not_allowed", "en"), show_alert=True)
            return
    await cb.message.answer("Use /broadcast <message> to send to all members.")
    await cb.answer()
