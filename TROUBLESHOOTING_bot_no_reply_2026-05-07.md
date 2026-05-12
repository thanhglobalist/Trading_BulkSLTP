# Troubleshooting — Telegram bot not replying to `/help` or `/getmyid`

**Reported:** 2026-05-07 16:32 ICT (Asia/Bangkok)
**Reporter:** Thanh Nguyen (@thanhglobalist)
**For:** sltp-tg-bot v1.0.0 + DevOps Guide v1.0.1
**Severity:** Blocking — bot does not respond to any command

---

## 1. Symptom (verbatim from user screenshot)

User sent two consecutive messages to the bot in Telegram:

```
/help        4:32 PM ✓✓
/getmyid     4:32 PM ✓✓
```

Both messages show **double blue checkmarks** = Telegram delivered them to its servers.
The bot **did not reply with anything** — no menu, no lockout message, no error.

> "These 2 commands are not working. The Ubuntu VPS has deployed."

---

## 2. What the symptom rules out

| Hypothesis | Verdict | Why |
|---|---|---|
| Network problem on phone | ❌ ruled out | ✓✓ confirms message reached Telegram |
| Telegram outage | ❌ ruled out | message delivery worked |
| User is allowlisted but command unknown | ❌ ruled out | even unknown commands trigger a generic response in v1.0.0 |
| User is unauthorized stranger | ⚠️ partial | unauthorized strangers should still get `⛔ This bot is private.` — they got **nothing** |

**Conclusion:** the bot process is either (a) not running, (b) running but not connected to Telegram, or (c) running and connected but has a handler crash. Diagnosis must start at the VPS, not at Telegram.

---

## 3. Diagnostic checklist — work top to bottom

Stop at the **first** check that fails. That's your root cause.

### ☐ 3.1 — Confirm you are messaging the right bot

In Telegram, tap the bot's name at the top of the chat. Note the `@username`.

```
Bot username seen in chat:    @___________________________
Bot username @BotFather gave: @___________________________
```

If they don't match → **switch to the correct chat**. The wrong-bot mistake is more common than people admit.

### ☐ 3.2 — Service status

On the Ubuntu VPS:

```bash
sudo systemctl status sltp-tg-bot --no-pager | head -20
```

Expected: `Active: active (running) since ...`

If you see `failed`, `inactive`, `activating`, or `auto-restart` — service is dead or flapping. Continue to 3.3 to find out why.

If you see `active (running)` — service is up; jump to 3.5.

### ☐ 3.3 — Recent error logs

```bash
sudo journalctl -u sltp-tg-bot -n 100 --no-pager | tail -60
```

Scan for `ERROR`, `Traceback`, `Exception`, `panic`, or repeated lines. Match against the table below — these are the failure modes I've seen most often:

| What you see in logs | Root cause | Fix |
|---|---|---|
| `pydantic_core._pydantic_core.ValidationError`<br>`BOT_TOKEN ... field required` | `.env` missing or `BOT_TOKEN=` empty | `nano /opt/sltp-tg-bot/.env`, paste BotFather token, `sudo systemctl restart sltp-tg-bot` |
| `aiogram.exceptions.TelegramUnauthorizedError`<br>`Unauthorized` / `401` from `getMe` | `BOT_TOKEN` wrong, revoked, or has whitespace | Get fresh token: DM `@BotFather` → `/mybots` → select bot → **API Token** → copy. Paste **without spaces** into `.env`. Restart. |
| `TelegramConflictError`<br>`409 Conflict: terminated by other getUpdates request` | Two processes polling with the same token, OR a webhook is set | (a) `pgrep -fa sltp_tg_bot` — kill duplicates. (b) `curl -s "https://api.telegram.org/bot<TOKEN>/deleteWebhook"`. Restart service. |
| `OSError: [Errno 98] Address already in use` | Port 8080 occupied | `sudo lsof -i :8080` — identify conflict, change `LISTEN_PORT` in `.env`, restart |
| `sqlite3.OperationalError: unable to open database file` | DB path missing or wrong permissions | `mkdir -p /var/lib/sltp-tg-bot && chown sltpbot:sltpbot /var/lib/sltp-tg-bot && chmod 700 /var/lib/sltp-tg-bot`. Restart. |
| `sqlite3.OperationalError: no such table: team_members` | Schema never initialized | `sudo -u sltpbot /opt/sltp-tg-bot/.venv/bin/python -m sltp_tg_bot.scripts.init_db`. Restart. |
| `ModuleNotFoundError: No module named 'aiogram'` | Wrong venv, or pip install never ran | `cd /opt/sltp-tg-bot && sudo -u sltpbot .venv/bin/pip install -e .`. Restart. |
| `PermissionError: [Errno 13] Permission denied: '/var/log/sltp-tg-bot/...'` | Log directory not writable by service user | `mkdir -p /var/log/sltp-tg-bot && chown sltpbot:sltpbot /var/log/sltp-tg-bot`. Restart. |
| `httpx.ConnectError` / `getaddrinfo failed` repeatedly | DNS or outbound connectivity broken | `curl -v https://api.telegram.org` from VPS — if it fails, check droplet networking / firewall outbound |
| `KeyError: 'ADMIN_USER_ID'` or `int_parsing` for it | `ADMIN_USER_ID` missing or non-numeric | `nano .env`, set to your Telegram numeric ID (no `@` prefix, just the number). Restart. |
| **No errors at all, but no `polling` line either** | Process started FastAPI bridge but Telegram dispatcher silently failed | Continue to 3.4 |

Paste the actual log block here for the record:

```
[ paste output of `sudo journalctl -u sltp-tg-bot -n 100 --no-pager` here ]
```

### ☐ 3.4 — Confirm the Telegram polling loop actually started

```bash
sudo journalctl -u sltp-tg-bot --since "15 minutes ago" --no-pager \
  | grep -iE "polling|started|telegram|@.*bot|getme"
```

Expected: at least one line like

```
INFO     aiogram.dispatcher     Start polling
INFO     aiogram.dispatcher     Run polling for bot @YourBotName id=123456789 ...
```

If you see those lines → polling is alive. The problem is downstream (handler crash on message). Skip to 3.6.

If you see **nothing** → polling never started. The most common cause is `BOT_TOKEN` failing `getMe` validation but the failure being eaten by an outer try/except. Try the manual `getMe` test in 3.5.

### ☐ 3.5 — Manually verify the bot token works

Replace `<BOT_TOKEN>` with the literal value from `.env`:

```bash
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getMe" | python3 -m json.tool
```

Expected:

```json
{
    "ok": true,
    "result": {
        "id": 7842917341,
        "is_bot": true,
        "first_name": "Bulk SLTP",
        "username": "BulkSLTPBot",
        ...
    }
}
```

| What you actually get | What it means |
|---|---|
| `{"ok": true, ...}` with username matching what you see in Telegram | Token is good. Problem is in the bot's startup or handlers — go to 3.7. |
| `{"ok": false, "error_code": 401, "description": "Unauthorized"}` | Token wrong/revoked. Regenerate at @BotFather. |
| `{"ok": false, "error_code": 404}` | Token malformed (has spaces, missing characters). Re-copy carefully. |
| `curl: (6) Could not resolve host` | DNS broken on VPS. Check `/etc/resolv.conf`. |
| `curl: (7) Failed to connect` | Outbound HTTPS blocked. Check droplet firewall / DO cloud firewall. |

### ☐ 3.6 — Confirm there's no leftover webhook

A webhook and long-polling are mutually exclusive. If a webhook was ever set (even by a previous owner of the same token), polling silently fails with `409 Conflict`.

```bash
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo" | python3 -m json.tool
```

Look at the `url` field:

| Value of `url` | Action |
|---|---|
| `""` (empty string) | Good — no webhook. Move on. |
| Any non-empty URL | **Delete it:** `curl -s "https://api.telegram.org/bot<BOT_TOKEN>/deleteWebhook?drop_pending_updates=true"` then restart service. |

### ☐ 3.7 — Confirm the bridge HTTP API is up (proves FastAPI side is healthy)

```bash
curl -s http://127.0.0.1:8080/healthz
```

Expected: `{"status":"ok"}` (or similar JSON 200).

If you get nothing or connection refused → the entire bot process is down even if `systemctl` says active (rare; usually means the process is hung). `sudo systemctl restart sltp-tg-bot` and watch logs live with `sudo journalctl -u sltp-tg-bot -f`.

### ☐ 3.8 — Confirm the user is reachable per the configured `ADMIN_USER_ID`

```bash
grep ADMIN_USER_ID /opt/sltp-tg-bot/.env
```

Compare with the user's actual Telegram numeric ID (Thanh's). If unknown:

- Send any message to `@userinfobot` on Telegram from the affected account
- It replies with the numeric ID

If `.env` has the wrong value:

```bash
sudo nano /opt/sltp-tg-bot/.env
# update ADMIN_USER_ID=<correct numeric id>
sudo systemctl restart sltp-tg-bot
```

Then send `/start` from Telegram. The bot should auto-create that user as admin on first contact.

### ☐ 3.9 — Confirm `/start` was sent at least once before `/help`

The v1.0.0 bot expects `/start` as the first interaction. It bootstraps the team_members row and per-user command list (`setMyCommands` scoped to `BotCommandScopeChat`). Without that, some Telegram clients don't show command suggestions, but commands typed manually should still route — **unless** the user is unauthorized, in which case the bot returns the lockout message.

The user's screenshot shows them sending `/help` and `/getmyid` directly. **Send `/start` first**, observe the reply, then retry.

| `/start` reply | Diagnosis |
|---|---|
| Welcome menu opens | Bot is healthy. The earlier silence was likely a timing race during deploy. Done. |
| `⛔ This bot is private.` | User is not in allowlist. Set `ADMIN_USER_ID` correctly (3.8) and restart. |
| Still no reply | Bot is not running / not polling — go back to 3.2 and re-check. |

### ☐ 3.10 — Last resort: clean restart with live logs

If everything above looks fine but the bot still doesn't respond:

```bash
# Stop, clear pending updates, start fresh, watch logs
sudo systemctl stop sltp-tg-bot
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/deleteWebhook?drop_pending_updates=true"
sudo systemctl start sltp-tg-bot
sudo journalctl -u sltp-tg-bot -f
```

Now from Telegram, send `/start`. You should see in the live logs:

```
INFO  aiogram.event  Update id=... received
INFO  aiogram.event  Handle update from user=<your_id> ...
```

If updates are received but not handled → handler exception, paste the traceback.
If updates are NOT received → polling is broken at Telegram's side: token issue, webhook issue, or duplicate poller (someone else has the same token open).

---

## 4. What to send back

If you've worked through 3.1 → 3.10 and it's still broken, paste these four outputs back to me and I'll diagnose precisely:

```bash
# 1
sudo systemctl status sltp-tg-bot --no-pager | head -20

# 2
sudo journalctl -u sltp-tg-bot -n 100 --no-pager

# 3 (replace TOKEN; redact before sharing publicly)
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getMe"

# 4 (replace TOKEN; redact before sharing publicly)
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

> 🔒 **Redact the bot token** before pasting. The portion before the colon is the bot ID and is safe; the portion after the colon is the secret.

---

## 5. My best guess given the symptoms

In order of probability:

1. **Service is not actually running** despite "deployment complete" — `systemctl status` failed or is in a restart loop because of a missing `.env` value (most often `BOT_TOKEN` or `ADMIN_USER_ID`). [check 3.2 → 3.3]
2. **`BOT_TOKEN` is wrong or has invisible whitespace** from a copy-paste — bot starts the bridge but never establishes a Telegram session. [check 3.5]
3. **A webhook was set on this bot token previously** and is still in place, blocking polling with 409. [check 3.6]
4. **DevOps deployed the bridge module but didn't run `init_db.py`** — bot crashes on first DB read. [check 3.3 for `no such table`]

All four are 5-minute fixes once identified.

---

## 6. Where to escalate

If 3.1 → 3.10 all pass and the bot still won't reply, capture the live log during a `/start` attempt (`journalctl -fu sltp-tg-bot` while you tap the bot in Telegram) and send it back. Anything coming through the polling loop will be visible there in real time — that's the definitive diagnosis tool.

---

*Document version: 1.0 · Generated 2026-05-07 16:40 ICT · Applies to sltp-tg-bot v1.0.0 + DevOps Guide v1.0.1*
