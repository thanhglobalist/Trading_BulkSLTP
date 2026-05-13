# sltp-tg-bot v1.0.3 — `/help` redesigned

**Released:** 2026-05-13
**Author:** Thanh Nguyen / thanhglobalist@gmail.com / [@thanhglobalist](https://t.me/thanhglobalist)

## What changed

`/help` is no longer the 4-line stub it was. It is now a full, role-aware,
multilingual help center with deep-link buttons that take the user directly
to the screen being explained.

### New behavior

| | v1.0.2 and before | v1.0.3 |
|---|---|---|
| Surface | Single message: `/menu /status /positions /lang` | Home grid + 9 topic pages + inline language switcher |
| Role awareness | None | Buttons hidden when role doesn't permit the action |
| Stranger handling | Same as everyone | Slim variant showing the user's Telegram ID for the admin to add |
| Language switch | Forced to leave help, run `/lang` | Inline `🌐 Language` button — re-renders without leaving |
| `❓ Help` button on `/menu` | Dead callback (`menu:help` was never wired) | Opens the help home |
| Deep links | None | `📊 Open Status`, `🛡️ Open SL/TP screen`, `⚙️ Open Settings`, etc. |
| Languages | Stub message in EN only | Full EN / JA / VI parity |

### Topic pages

Every topic is a compact verbose page with a worked example where relevant
and a back button. Topics visible by role:

| Topic | Stranger | View | View+Close | Full | Admin |
|---|---|---|---|---|---|
| 🧭 Navigation | ❌ | ✅ | ✅ | ✅ | ✅ |
| 📊 Reading screens | ❌ | ✅ | ✅ | ✅ | ✅ |
| ❌ Closing positions | ❌ | ❌ | ✅ | ✅ | ✅ |
| 🛡️ Bulk SL/TP | ❌ | ❌ | ❌ | ✅ | ✅ |
| ⚖️ Breakeven | ❌ | ❌ | ❌ | ✅ | ✅ |
| 🚨 Emergency | ❌ | ❌ | ❌ | ✅ | ✅ |
| 🔔 Push alerts | ❌ | ✅ | ✅ | ✅ | ✅ |
| 👥 Roles & permissions | ✅ | ✅ | ✅ | ✅ | ✅ |
| 💬 Commands list | ✅ | ✅ | ✅ | ✅ | ✅ |
| ⚙️ Admin guide | ❌ | ❌ | ❌ | ❌ | ✅ |

Strangers get a slim grid (👥 Roles + 💬 Commands + 🌐 Language) and a
prominent "🆔 Your Telegram ID: 123456789" line so they can copy-paste it
to whoever administers the bot.

## Implementation notes

- **`src/sltp_tg_bot/bot/handlers/help.py`** rewritten from 9 lines to ~350.
  Entry points: typed `/help` (`cmd_help`) and inline `menu:help` button
  (`cb_menu_help`). Home → topic → back, all via in-place message edits where
  possible.
- **`src/sltp_tg_bot/bot/keyboards.py`** gained `help_home_kb`,
  `help_stranger_kb`, `help_topic_kb`, and `help_lang_kb`. Topic deep-link
  buttons are *only added when the viewer's role permits the target action*
  — we don't tease screens users can't open.
- **`src/sltp_tg_bot/i18n.py`** gained 36 new keys × EN/JA/VI = 108 strings.
  Total parity now **129 / 129 / 129** (up from 93 / 93 / 93 in v1.0.2).
- Help text uses `parse_mode=None` (plain text). The bot's HTML default
  would otherwise eat `<old>` / `<new>` placeholders in command signatures.
- Role resolution uses the user's currently selected account (from
  `sessions.current_account_id`); if no account is selected yet, it falls
  back to the highest role across all accounts the user has any access to.
  Admins always resolve to `ROLE_FULL`.
- Inline language switcher uses callback prefix `helplang:set:<code>` so it
  doesn't collide with the global `/lang` flow's `lang:set:<code>`.
  Both still call `apply_user_commands(...)` to refresh the per-chat
  `setMyCommands` autocomplete list.

## Unchanged (intentional)

- Existing `/lang` typed command and `lang:set:<code>` callback flow
- Main menu keyboard
- Trading, status, admin, and bridge code paths
- Database schema and audit log format

## Files in this release (for Git workflow)

| File | Repo path |
|---|---|
| `i18n.py` | `src/sltp_tg_bot/i18n.py` |
| `keyboards.py` | `src/sltp_tg_bot/bot/keyboards.py` |
| `help.py` | `src/sltp_tg_bot/bot/handlers/help.py` |
| `__init__.py` | `src/sltp_tg_bot/__init__.py` |
| `pyproject.toml` | repo root |
| `CHANGELOG_v1.0.3_2026-05-13.md` | repo root |

## Suggested commit message

```
feat(help): role-aware multilingual /help center — v1.0.3

- handlers/help: full rewrite. /help and menu:help open a home grid
  with role-gated topic pages, deep-link buttons into the matching
  screens, and an inline language switcher.
- keyboards: help_home_kb, help_stranger_kb, help_topic_kb, help_lang_kb
- i18n: +36 keys × EN/JA/VI (parity 129/129/129)
- bump version 1.0.2 → 1.0.3
```

## Verification

- `py_compile` clean on all 4 changed .py files (no warnings under `-W error`)
- i18n parity: 129/129/129 keys across EN/JA/VI
- AST scan: help router's handlers all registered in `bot/handlers/__init__.py`
- No callback-data collision with existing menu/admin/lang flows
