# CHANGELOG — sltp-tg-bot v1.0.4

**Release date:** 2026-05-13
**Author:** Thanh Nguyen <thanhglobalist@gmail.com>
**Telegram:** https://t.me/thanhglobalist

---

## Summary

**Hard rename `/menu` → `/accounts`.** The command that opens the
account picker is now `/accounts`. The old `/menu` command has been
**completely removed** — there is no alias. The picker title and
Telegram command-list descriptions have been rewritten so the action
matches what the screen actually does (showing a list of trading
accounts to control).

This is a UX clarification release. No new features; no behaviour
change for traders beyond the new command name.

---

## Changes

### Command rename — `/menu` → `/accounts` (hard switch, no alias)

**Why:** The previous label *"Status / menu"* in the Telegram
autocomplete (and the `/menu` command itself) caused confusion — tapping
it opened an account picker, not a status menu. The new name
`/accounts` is literal and self-describing.

**Code:**
- `src/sltp_tg_bot/bot/handlers/menu.py`
  - `@router.message(Command("menu"))` → `Command("accounts")`
  - `cmd_menu` function renamed to `cmd_accounts`
  - Audit `action="menu"` → `action="accounts"`
  - Hardcoded fallback string `"No active account. Use /menu …"` →
    `"… Use /accounts …"`
- `src/sltp_tg_bot/bot/handlers/common.py`
  - Module docstring updated
  - `_commands_for()` rewritten — the brittle slicing trick
    `t("btn_status", lang)[2:] + " / menu"` is gone; descriptions now
    come from new dedicated i18n keys (see below)
  - `BotCommand(command="menu", …)` → `BotCommand(command="accounts", …)`
  - `/start` final hint message `"/menu"` → `"/accounts"`

### New i18n keys (×3 languages, parity 136/136/136)

Added a dedicated block of Telegram-autocomplete descriptions so they
no longer piggyback on button labels:

| Key | EN | JA | VI |
|---|---|---|---|
| `cmd_desc_menu` | 🏦 Switch trading account | 🏦 取引口座を切替 | 🏦 Đổi tài khoản giao dịch |
| `cmd_desc_status` | 📊 Quick account status | 📊 口座ステータスを確認 | 📊 Trạng thái tài khoản |
| `cmd_desc_positions` | 📋 List open positions | 📋 ポジション一覧 | 📋 Danh sách vị thế |
| `cmd_desc_help` | ❓ Show help | ❓ ヘルプを表示 | ❓ Xem trợ giúp |
| `cmd_desc_lang` | 🌐 Change language | 🌐 言語を変更 | 🌐 Đổi ngôn ngữ |
| `cmd_desc_getmyid` | 🆔 Show your Telegram ID | 🆔 Telegram ID を表示 | 🆔 Xem Telegram ID |
| `cmd_desc_settings` | ⚙️ Admin settings | ⚙️ 管理者設定 | ⚙️ Cài đặt quản trị |

(`cmd_desc_menu` is the description of the new `/accounts` command — name
preserved for future-proofing if we ever add a separate "main menu".)

### Picker title rewritten

`pick_account` now reads as a full sentence describing the action:

- **EN:** "🏦 Pick a trading account to control"
- **JA:** "🏦 操作する取引口座を選択"
- **VI:** "🏦 Chọn tài khoản giao dịch để điều khiển"

### Doc & help-text references

Every user-facing reference to `/menu` was rewritten to `/accounts`:

- `i18n.py` — `welcome_body`, `help_navigation`, `help_v2_nav`,
  `help_v2_closing`, `help_v2_emergency`, `help_v2_commands_user`
  (all 3 languages)
- `COMMANDS_REFERENCE_v1.0.0.md` — 19 occurrences

Historical CHANGELOGs (v1.0.1–v1.0.3) deliberately untouched.

### Version

- `__version__` → `1.0.4`
- `pyproject.toml` `version` → `1.0.4`

---

## Validation

- `python3 -W error -m py_compile` on every changed `.py` — **clean**
- i18n key parity: **EN 136 / JA 136 / VI 136**
- `grep -r "/menu" src/` returns only `Router(name="menu")` — the
  internal aiogram router identifier, not user-visible
- `grep -r "cmd_menu\|Command(\"menu\")" src/` — **0 hits**

---

## Migration notes

- Existing users will see `/accounts` in their Telegram autocomplete
  the first time they hit `/start`, `/lang`, or any flow that calls
  `apply_user_commands()`. No DB migration required.
- Any user who types `/menu` will now get Telegram's default
  *"Command not recognised"* — by design (hard switch).
- Audit-log readers: rows with `action='menu'` now appear as
  `action='accounts'` going forward.
