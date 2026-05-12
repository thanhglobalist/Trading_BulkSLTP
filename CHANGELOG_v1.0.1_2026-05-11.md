# sltp-tg-bot v1.0.1 — Rename button + per-account inline menu

**Released:** 2026-05-11
**Author:** Thanh Nguyen / thanhglobalist@gmail.com / [@thanhglobalist](https://t.me/thanhglobalist)

## What's new

### ✏️ Inline Rename flow for accounts

You can now rename a trading account directly from the bot UI, no typing required:

```
/menu  →  ⚙️ Settings  →  🏦 Accounts  →  (tap the account)  →  ✏️ Rename
```

The bot will ask for the new alias. Send it as a plain text message. The rename is applied immediately and confirmed with `✅ Renamed: <old> → <new>`.

### 🔁 Inline Rotate token (bonus)

The same per-account menu also exposes `🔁 Rotate token` as an inline button — previously only available via the `/rotate <alias>` typed command.

### `/renameaccount` typed command

Power-user shortcut equivalent to the button flow:

```
/renameaccount Personal-IS6FX  IS6FX-Main
```

### What stays the same on rename

- The EA token, MT5 login, granted permissions, and audit history are all preserved
- Audit log entries from before the rename keep their original alias text in the `details` column
- The EA on the Windows VPS does NOT need to be restarted or reconfigured — alias is a bot-side label only

## Alias validation

- 1–32 characters
- Allowed: A–Z, a–z, 0–9, `-`, `_`
- Spaces and special chars are rejected with `🚫 Invalid alias`
- Duplicates rejected with `🚫 Alias '<x>' is already in use by another account`

## Architecture notes

- New DB helper `db.rename_account(conn, old_alias=..., new_alias=...)` with two custom exceptions: `AccountNotFoundError` and `AliasConflictError`
- New keyboard factories `accounts_list_kb()` and `account_actions_kb(account_id)` in `bot/keyboards.py`
- New callbacks `acctadm:open:<id>`, `acctadm:rename:<id>`, `acctadm:rotate:<id>` in `bot/handlers/admin.py`
- Rename text-capture handler uses the existing `sessions.pending_state` column (state name `adm_rename_account`) — survives bot restarts
- Critical: the new text-capture handler is registered **before** `adm_capture_display` in the admin router. aiogram dispatches in registration order; this prevents the broad `F.text` filter in `adm_capture_display` from swallowing the rename input. The new handler uses an async `_is_rename_state` decorator-level filter so it cleanly skips when no rename is pending.

## i18n

10 new keys added in all three languages (EN/JA/VI):

- `admin_rename_btn`, `admin_rotate_btn`
- `admin_account_header`, `admin_accounts_empty`, `admin_accounts_tap_hint`
- `admin_rename_prompt`, `admin_rename_ok`, `admin_rename_taken`, `admin_rename_invalid`
- `admin_account_not_found`

**Key parity:** 93/93 across EN/JA/VI (was 83/83 in v1.0.0).

## Upgrade steps (on Ubuntu VPS)

```bash
# 1. Stop the bot
sudo systemctl stop sltp-tg-bot

# 2. Replace the source (assuming /opt/sltp-tg-bot install)
cd /opt
sudo rm -rf sltp-tg-bot.bak
sudo mv sltp-tg-bot sltp-tg-bot.bak
sudo unzip /path/to/sltp-tg-bot-v1.0.1.zip
sudo cp sltp-tg-bot.bak/.env sltp-tg-bot/
sudo cp -r sltp-tg-bot.bak/data sltp-tg-bot/

# 3. Restart
sudo systemctl start sltp-tg-bot

# 4. Verify
sudo journalctl -u sltp-tg-bot --since "1 minute ago"
```

The SQLite DB is untouched — no migrations needed. Existing accounts, members, and permissions carry over.

## Audit log

Every rename writes an audit row:

```
2026-05-11T15:50:23+07:00  user=123456789  account=42  action=rename_account  allowed=1  reason=Personal-IS6FX→IS6FX-Main
```

You can filter for all renames with `/audit action:rename_account`.
