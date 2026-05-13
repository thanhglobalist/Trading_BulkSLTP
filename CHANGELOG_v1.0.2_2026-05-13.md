# sltp-tg-bot v1.0.2 — Rename command shortened to `/rename`

**Released:** 2026-05-13
**Author:** Thanh Nguyen / thanhglobalist@gmail.com / [@thanhglobalist](https://t.me/thanhglobalist)

## Summary

Shortens the admin rename command from `/renameaccount` to `/rename` for ergonomics.
Inline button flow (Settings → Accounts → tap → ✏️ Rename) is unchanged.

## ⚠️ Breaking change for admins

If you had muscle memory or saved snippets using `/renameaccount`, switch to:

```
/rename <old_alias> <new_alias>
```

Example:

```
/rename Personal-IS6FX  IS6FX-Main
```

`/renameaccount` is no longer recognized — Telegram will treat it as an unknown command. No other admin commands changed.

## Changed

- `src/sltp_tg_bot/bot/handlers/admin.py` — `@router.message(Command("renameaccount"))` → `Command("rename")`; usage string and docstring updated to match
- `COMMANDS_REFERENCE_v1.0.0.md` — admin command table and access matrix updated to show `/rename`
- `src/sltp_tg_bot/__init__.py` — `__version__` → `1.0.2`
- `pyproject.toml` — `version` → `1.0.2`

## Unchanged (intentional)

The following are internal identifiers and are NOT renamed — keeping them stable avoids breaking in-flight sessions and historical audit records:

- DB pending-state string `adm_rename_account` (any active rename session created on v1.0.1 continues to work)
- Audit `action` value `adm_rename_account` (preserves historical log filters)
- Python function name `cmd_rename_account` and DB helper `db.rename_account()`
- i18n keys `admin_rename_btn`, `admin_rename_prompt`, `admin_rename_ok`, etc.

## Validation

- `py_compile` clean on `admin.py`
- i18n parity: 93/93/93 keys across EN/JA/VI (unchanged from v1.0.1)
- No autocomplete update needed — `/rename` was never advertised via `set_my_commands` (admin-only typed command, same as the previous `/renameaccount`)

## Files in this release

For Git workflow, the following individual files are shipped:

| File | Repo path |
|---|---|
| `admin.py` | `src/sltp_tg_bot/bot/handlers/admin.py` |
| `COMMANDS_REFERENCE_v1.0.0.md` | repo root |
| `__init__.py` | `src/sltp_tg_bot/__init__.py` |
| `pyproject.toml` | repo root |
| `CHANGELOG_v1.0.2_2026-05-13.md` | repo root |

## Suggested commit message

```
chore(admin): shorten /renameaccount → /rename — v1.0.2

- handlers/admin: Command("renameaccount") → Command("rename")
- docs: COMMANDS_REFERENCE table + access matrix updated
- bump __init__.py and pyproject.toml to 1.0.2

Internal identifiers (DB state, audit action, function names) unchanged
to preserve in-flight rename sessions and historical audit records.
```
