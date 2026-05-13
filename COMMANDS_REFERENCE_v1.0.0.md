# Telegram Bot — Complete Command Reference

**For:** sltp-tg-bot v1.0.0 + BulkSLTPUpdater EA v1.3.0
**Languages supported:** 🇬🇧 English · 🇯🇵 日本語 · 🇻🇳 Tiếng Việt
**Document version:** 1.1 · Generated 2026-05-11 (added per-role Telegram popup UI in EN/JA/VI)

---

## How to read this document

Every command in this bot is **permission-gated** at two levels:

1. **Role-level** — your role across all accounts determines which commands the bot exposes to you (and even which appear in Telegram's `/` autocomplete)
2. **Account-level** — the currently-selected account in your session determines whether the command is allowed *right now*

If you try a command outside your permissions, the bot returns a generic `⛔ Action not allowed` and writes an entry to the admin audit log. No information leakage about features you can't use.

The **`/help`** command is dynamic — it shows you only the commands listed here for your role.

---

## Role hierarchy

From least to most privileged:

| Role | Description | Granted via |
|---|---|---|
| **(Stranger)** | Not in team_members. Cannot use the bot at all. | n/a |
| **(No access)** | In team_members but no account permissions. Effectively locked out. | Admin adds them but grants no accounts |
| **View** | Read-only. Can see status and positions for granted accounts. | Admin: Settings → Team → Edit → set role to View |
| **View + Close** | View permissions + can close positions. No SL/TP/BE/panic. | Admin: ... role View+Close |
| **Full** | All trading actions on granted accounts. No team or system admin. | Admin: ... role Full |
| **Admin** | All Full powers + team management + account management + audit log + broadcast. | `is_admin=1` in DB (bootstrap from `ADMIN_USER_ID` env var; can be granted/revoked by another admin) |

**Important:** A user can have **different roles on different accounts**. Example: Trader A is `Full` on `Personal-IS6FX` and `View` on `Funded-FTMO-50K`. They see both accounts in the picker; commands available depend on which they currently have selected.

---

## Universal commands — every authenticated user gets these

These work regardless of role, as long as the user is in `team_members`:

| Command | Description | Notes |
|---|---|---|
| `/start` | Initialize / open the bot | First-time users get language auto-detect + welcome. Returning users get a "Tap /menu to begin." prompt. |
| `/help` | Dynamic per-role guide | Content varies by role — see role-specific tables below |
| `/menu` | Open main menu (account picker) | Always opens with picker if user has ≥ 2 accessible accounts; opens directly into the account if only 1 |
| `/use <alias>` | Switch session to a specific account | Power-user shortcut. Fails silently if alias doesn't exist or user has no permission on it |
| `/getmyid` | Echo your Telegram numeric ID | **Works without any auth** — useful for new users to send their ID to the admin |
| `/lang` | Switch interface language | Shows inline keyboard: 🇬🇧 English · 🇯🇵 日本語 · 🇻🇳 Tiếng Việt. Persists in `team_members.language` |
| `/cancel` | Abort any in-flight multi-step flow | E.g., escape from "awaiting SL price" prompt |

---

## Strangers — users NOT in `team_members`

Anyone with a Telegram account who finds the bot and is not in the allowlist.

| Command | Response |
|---|---|
| `/start` | `⛔ This bot is private.` (in EN/JA/VI based on Telegram client language) |
| `/help` | `⛔ This bot is private.` |
| `/getmyid` | Returns their numeric Telegram ID (this is the **only** authenticated-bypass command — strangers need a way to learn their own ID so an admin can add them) |
| Any other command | `⛔ This bot is private.` |
| Any free text | Silent (no response) — prevents probing |

**Why `/getmyid` works for strangers:** to bootstrap onboarding. A new teammate needs to tell their admin their numeric ID. Without `/getmyid` working pre-auth, admin and teammate would need a third-party bot like `@userinfobot`. Allowing `/getmyid` for strangers is a deliberate, low-risk concession.

---

## (No access) role — in `team_members` but zero permissions

User exists in the system but admin hasn't granted them any account yet.

| Command | Response |
|---|---|
| `/start` | Welcome message + "You don't have access to any account. Contact your admin with your ID: {user_id}" |
| `/help` | "You don't have access to any account yet. Your Telegram ID: {user_id}. Contact your admin." |
| `/getmyid` | Returns their numeric ID |
| `/menu` | "⛔ You don't have access to any account. Contact your admin." |
| `/lang` | Works — they can still pick their preferred language |
| `/cancel` | Works |
| Trading commands (`/closeall`, `/sl`, etc.) | `⛔ Action not allowed` + audit log entry |

---

## View role — read-only on granted accounts

| Command | Available? | Description |
|---|---|---|
| **Universal commands** (above) | ✅ All | |
| `/status` | ✅ | Account snapshot: balance, equity, free margin, P/L, position count, Portfolio BE strip |
| `/positions` | ✅ | Top 10 positions by absolute P/L on current account. Inline ◀️ ▶️ pagination |
| `/closeall` | ❌ | `⛔ Action not allowed` + audit |
| `/closebuys` | ❌ | `⛔ Action not allowed` + audit |
| `/closesells` | ❌ | `⛔ Action not allowed` + audit |
| `/sl <price>` | ❌ | `⛔ Action not allowed` + audit |
| `/tp <price>` | ❌ | `⛔ Action not allowed` + audit |
| `/sloff` | ❌ | `⛔ Action not allowed` + audit |
| `/tpoff` | ❌ | `⛔ Action not allowed` + audit |
| `/be` | ❌ | `⛔ Action not allowed` + audit |
| `/panic` | ❌ | `⛔ Action not allowed` + audit |
| Admin commands | ❌ | `⛔ Action not allowed` + audit |

**Push alerts received:**
- 🟢 Position opened (informational)
- 🔴 Position closed (informational)
- 📅 Daily P/L summary at server time

**Push alerts NOT received:**
- ⚠️ Margin warnings (operators only)
- 🚨 SL/TP-hit details (operators only)

---

## View + Close role — read-only + can close positions

| Command | Available? | Description |
|---|---|---|
| **Universal commands** | ✅ All | |
| **All View commands** | ✅ All | |
| `/closeall` | ✅ | Close ALL positions on current account. Inline keyboard confirmation. Uses v1.1.9.4 P/L safety gate. |
| `/closebuys` | ✅ | Close only BUY positions on current account |
| `/closesells` | ✅ | Close only SELL positions on current account |
| `/sl <price>` | ❌ | `⛔ Action not allowed` + audit |
| `/tp <price>` | ❌ | |
| `/sloff` | ❌ | |
| `/tpoff` | ❌ | |
| `/be` | ❌ | |
| `/panic` | ❌ | |
| Admin commands | ❌ | |

**Push alerts received:**
- All of View's alerts, PLUS:
- ⚠️ Margin level warnings (debounced)
- 🚨 Position closed by SL or TP hit (with detail)

---

## Full role — all trading actions on granted accounts

| Command | Available? | Description |
|---|---|---|
| **Universal commands** | ✅ All | |
| **All View + Close commands** | ✅ All | |
| `/sl <price>` | ✅ | Apply this stop-loss price to all open positions on current account. Inline confirm. Example: `/sl 4520.00` |
| `/tp <price>` | ✅ | Apply this take-profit price to all open positions on current account. Example: `/tp 4600.00` |
| `/sloff` | ✅ | Remove SL from all positions on current account. Inline confirm. |
| `/tpoff` | ✅ | Remove TP from all positions on current account. Inline confirm. |
| `/be` | ✅ | Apply per-side Portfolio Breakeven. Uses v1.1.9.3 lot-weighted model — TP for net-profit side, SL for net-loss side. Inline confirm shows BE_buy and BE_sell prices before executing. |
| `/panic` | ✅ | **Two-step confirm.** Close ALL + disable EA on current account. Must type the word `PANIC` (uppercase) to confirm. |
| Admin commands | ❌ | `⛔ Action not allowed` + audit |

**Push alerts received:** all alerts for accounts they have access to (full firehose).

---

## Admin role — full system control

In addition to all Full role commands:

| Command | Available? | Description |
|---|---|---|
| `/accounts` | ✅ | List ALL registered MT5 accounts with online/offline status, equity, position count, EA version, last heartbeat |
| `/addaccount` | ✅ | Multi-step flow: prompts for alias, generates unique EA token, returns config snippet for the EA |
| `/removeaccount <alias>` | ✅ | Multi-step confirm. Revokes EA token, marks account inactive. Active positions on the EA continue running but bot no longer accepts commands for that account. |
| `/rotatetoken <alias>` | ✅ | Generate new EA token for an existing account. Old token immediately invalid. Use when a token leaks. |
| `/rename <old> <new>` | ✅ | Change account alias. Token and permissions unchanged. |
| `/team` | ✅ | List ALL team members with roles per account |
| `/addmember` | ✅ | Multi-step flow: prompts for user ID, display name, then shows account-permission grid to set roles |
| `/removemember <id>` | ✅ | Hard-delete a team member. Audit log preserves the record. Blocked if removing last admin. |
| `/pausemember <id>` | ✅ | Soft-disable a team member. All their commands return `⛔ Account paused` until `/resumemember`. Preferred over remove for temporary access removal. |
| `/resumemember <id>` | ✅ | Re-enable a paused team member |
| `/setrole <user_id> <account_alias> <role>` | ✅ | Change a member's role on a specific account. role ∈ {none, view, view_close, full}. Setting `none` revokes access. |
| `/promote <user_id>` | ✅ | Grant admin to a team member. Asks for confirmation. |
| `/demote <user_id>` | ✅ | Remove admin from a team member. Blocked if it would leave zero admins. |
| `/audit [filters]` | ✅ | Paginated audit log. Filters: `user:<id>`, `account:<alias>`, `action:<name>`, `since:<YYYY-MM-DD>`, `denied:1`. Example: `/audit user:987654321 action:closeall since:2026-05-01` |
| `/broadcast <message>` | ✅ | Send a message to all active team members. Use for maintenance notices, EA upgrades, etc. |
| `/health` | ✅ | Bot self-check: DB status, Telegram session, bridge API, EA connection count, queue depth |
| `/stats` | ✅ | Aggregate stats: total accounts, members, jobs run today, alert volume, audit row count |
| `/export <table> [days]` | ✅ | Export audit_log, jobs, or alerts as CSV file (sent as a Telegram document). Default 30 days. |

**Push alerts received:** alerts from ALL accounts, plus admin-only alerts:
- 🔔 New team member added (by another admin)
- 🔔 EA token rotated
- 🔔 Bot service restarted
- 🔔 Anomaly: >10 denied actions from one user in 5 minutes (potential abuse)

---

## Visual summary — command access matrix

✅ = available · ❌ = `⛔ Action not allowed` · — = command doesn't exist

| Command | Stranger | No access | View | View+Close | Full | Admin |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `/start` | lockout | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/help` | lockout | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/getmyid` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/menu` | lockout | ⛔ no acct | ✅ | ✅ | ✅ | ✅ |
| `/use` | lockout | ⛔ no acct | ✅ | ✅ | ✅ | ✅ |
| `/lang` | lockout | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/cancel` | lockout | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/status` | lockout | ❌ | ✅ | ✅ | ✅ | ✅ |
| `/positions` | lockout | ❌ | ✅ | ✅ | ✅ | ✅ |
| `/closeall` | lockout | ❌ | ❌ | ✅ | ✅ | ✅ |
| `/closebuys` | lockout | ❌ | ❌ | ✅ | ✅ | ✅ |
| `/closesells` | lockout | ❌ | ❌ | ✅ | ✅ | ✅ |
| `/sl <price>` | lockout | ❌ | ❌ | ❌ | ✅ | ✅ |
| `/tp <price>` | lockout | ❌ | ❌ | ❌ | ✅ | ✅ |
| `/sloff` | lockout | ❌ | ❌ | ❌ | ✅ | ✅ |
| `/tpoff` | lockout | ❌ | ❌ | ❌ | ✅ | ✅ |
| `/be` | lockout | ❌ | ❌ | ❌ | ✅ | ✅ |
| `/panic` | lockout | ❌ | ❌ | ❌ | ✅ | ✅ |
| `/accounts` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/addaccount` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/removeaccount` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/rotatetoken` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/rename` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/team` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/addmember` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/removemember` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/pausemember` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/resumemember` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/setrole` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/promote` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/demote` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/audit` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/broadcast` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/health` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/stats` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |
| `/export` | lockout | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Telegram autocomplete (`setMyCommands`) — what each role sees in the `/` menu

When a user taps the **menu button** (the `/` icon in the bottom-left of the chat input) or types `/` in their chat with the bot, Telegram shows a popup with command suggestions and short descriptions. The bot calls `setMyCommands` per-user (scoped via `BotCommandScopeChat`) and per-language (scoped via `language_code`) so each role sees a filtered, localized list.

Below is **exactly what each role sees in the popup**, in all three supported languages.

---

### Stranger — UI in Telegram

Strangers see the bot's default command list (the only command the bot exposes pre-auth):

**🇬🇧 English**
```
/start  —  Start the bot
```

**🇯🇵 日本語**
```
/start  —  ボットを開始
```

**🇻🇳 Tiếng Việt**
```
/start  —  Bắt đầu bot
```

(Note: `/getmyid` works but is intentionally **hidden** from the menu to avoid encouraging probing. Strangers are told about it inside the `⛔ This bot is private.` reply.)

---

### No access role — UI in Telegram

**🇬🇧 English**
```
/start     —  Open the bot
/help      —  Show your access status
/getmyid   —  Show my Telegram ID
/lang      —  Change language
/cancel    —  Cancel current action
```

**🇯🇵 日本語**
```
/start     —  ボットを開く
/help      —  アクセス状況を確認
/getmyid   —  Telegram IDを表示
/lang      —  言語を変更
/cancel    —  操作をキャンセル
```

**🇻🇳 Tiếng Việt**
```
/start     —  Mở bot
/help      —  Xem trạng thái truy cập
/getmyid   —  Hiển thị Telegram ID của tôi
/lang      —  Đổi ngôn ngữ
/cancel    —  Hủy thao tác hiện tại
```

---

### View role — UI in Telegram

**🇬🇧 English**
```
/menu        —  Open main menu
/status      —  Account snapshot (balance, equity, P/L)
/positions   —  List open positions
/help        —  Show available commands
/lang        —  Change language
/getmyid     —  Show my Telegram ID
```

**🇯🇵 日本語**
```
/menu        —  メインメニューを開く
/status      —  口座状況（残高・有効証拠金・損益）
/positions   —  保有ポジション一覧
/help        —  使えるコマンドを表示
/lang        —  言語を変更
/getmyid     —  Telegram IDを表示
```

**🇻🇳 Tiếng Việt**
```
/menu        —  Mở menu chính
/status      —  Trạng thái tài khoản (số dư, equity, P/L)
/positions   —  Danh sách vị thế đang mở
/help        —  Xem các lệnh có sẵn
/lang        —  Đổi ngôn ngữ
/getmyid     —  Hiển thị Telegram ID của tôi
```

---

### View + Close role — UI in Telegram

**🇬🇧 English**
```
/menu          —  Open main menu
/status        —  Account snapshot
/positions     —  List open positions
/closeall      —  Close ALL positions on this account
/closebuys     —  Close all BUY positions only
/closesells    —  Close all SELL positions only
/help          —  Show available commands
/lang          —  Change language
```

**🇯🇵 日本語**
```
/menu          —  メインメニューを開く
/status        —  口座状況
/positions     —  保有ポジション一覧
/closeall      —  全ポジションを決済
/closebuys     —  買いポジションのみ決済
/closesells    —  売りポジションのみ決済
/help          —  使えるコマンドを表示
/lang          —  言語を変更
```

**🇻🇳 Tiếng Việt**
```
/menu          —  Mở menu chính
/status        —  Trạng thái tài khoản
/positions     —  Danh sách vị thế đang mở
/closeall      —  Đóng TẤT CẢ vị thế
/closebuys     —  Chỉ đóng các lệnh BUY
/closesells    —  Chỉ đóng các lệnh SELL
/help          —  Xem các lệnh có sẵn
/lang          —  Đổi ngôn ngữ
```

---

### Full role — UI in Telegram

**🇬🇧 English**
```
/menu          —  Open main menu
/status        —  Account snapshot
/positions     —  List open positions
/closeall      —  Close ALL positions
/closebuys     —  Close BUY positions only
/closesells    —  Close SELL positions only
/sl            —  Set stop-loss price
/tp            —  Set take-profit price
/sloff         —  Remove all stop-losses
/tpoff         —  Remove all take-profits
/be            —  Apply Portfolio Breakeven
/panic         —  Emergency: close all + disable EA
/help          —  Show available commands
/lang          —  Change language
```

**🇯🇵 日本語**
```
/menu          —  メインメニューを開く
/status        —  口座状況
/positions     —  保有ポジション一覧
/closeall      —  全ポジションを決済
/closebuys     —  買いポジションのみ決済
/closesells    —  売りポジションのみ決済
/sl            —  ストップロス価格を設定
/tp            —  テイクプロフィット価格を設定
/sloff         —  全てのSLを解除
/tpoff         —  全てのTPを解除
/be            —  ポートフォリオBE適用
/panic         —  緊急停止：全決済＋EA停止
/help          —  使えるコマンドを表示
/lang          —  言語を変更
```

**🇻🇳 Tiếng Việt**
```
/menu          —  Mở menu chính
/status        —  Trạng thái tài khoản
/positions     —  Danh sách vị thế đang mở
/closeall      —  Đóng TẤT CẢ vị thế
/closebuys     —  Chỉ đóng các lệnh BUY
/closesells    —  Chỉ đóng các lệnh SELL
/sl            —  Đặt giá Stop Loss
/tp            —  Đặt giá Take Profit
/sloff         —  Gỡ tất cả SL
/tpoff         —  Gỡ tất cả TP
/be            —  Áp dụng Portfolio Breakeven
/panic         —  Khẩn cấp: đóng hết + tắt EA
/help          —  Xem các lệnh có sẵn
/lang          —  Đổi ngôn ngữ
```

---

### Admin role — UI in Telegram

Admins see all Full commands **plus** an admin section. To keep the popup readable, infrequent admin commands (rotate token, rename account, demote, export, stats) are accessible via `/menu → ⚙️ Settings` and intentionally omitted from the autocomplete popup.

**🇬🇧 English**
```
— Trading —
/menu          —  Open main menu
/status        —  Account snapshot
/positions     —  List open positions
/closeall      —  Close ALL positions
/closebuys     —  Close BUY positions only
/closesells    —  Close SELL positions only
/sl            —  Set stop-loss price
/tp            —  Set take-profit price
/sloff         —  Remove all stop-losses
/tpoff         —  Remove all take-profits
/be            —  Apply Portfolio Breakeven
/panic         —  Emergency: close all + disable EA
— Admin —
/accounts      —  List all MT5 accounts
/addaccount    —  Register a new MT5 account
/team          —  List all team members
/addmember     —  Add a new team member
/audit         —  View audit log
/broadcast     —  Send message to all members
/health        —  Bot self-check
/help          —  Show available commands
/lang          —  Change language
```

**🇯🇵 日本語**
```
— 取引 —
/menu          —  メインメニューを開く
/status        —  口座状況
/positions     —  保有ポジション一覧
/closeall      —  全ポジションを決済
/closebuys     —  買いポジションのみ決済
/closesells    —  売りポジションのみ決済
/sl            —  ストップロス価格を設定
/tp            —  テイクプロフィット価格を設定
/sloff         —  全てのSLを解除
/tpoff         —  全てのTPを解除
/be            —  ポートフォリオBE適用
/panic         —  緊急停止：全決済＋EA停止
— 管理 —
/accounts      —  全MT5口座を一覧表示
/addaccount    —  新規MT5口座を登録
/team          —  全チームメンバーを一覧表示
/addmember     —  新規メンバーを追加
/audit         —  監査ログを表示
/broadcast     —  全員に一斉送信
/health        —  ボット自己診断
/help          —  使えるコマンドを表示
/lang          —  言語を変更
```

**🇻🇳 Tiếng Việt**
```
— Giao dịch —
/menu          —  Mở menu chính
/status        —  Trạng thái tài khoản
/positions     —  Danh sách vị thế đang mở
/closeall      —  Đóng TẤT CẢ vị thế
/closebuys     —  Chỉ đóng các lệnh BUY
/closesells    —  Chỉ đóng các lệnh SELL
/sl            —  Đặt giá Stop Loss
/tp            —  Đặt giá Take Profit
/sloff         —  Gỡ tất cả SL
/tpoff         —  Gỡ tất cả TP
/be            —  Áp dụng Portfolio Breakeven
/panic         —  Khẩn cấp: đóng hết + tắt EA
— Quản trị —
/accounts      —  Liệt kê tất cả tài khoản MT5
/addaccount    —  Đăng ký tài khoản MT5 mới
/team          —  Liệt kê thành viên
/addmember     —  Thêm thành viên mới
/audit         —  Xem nhật ký kiểm toán
/broadcast     —  Gửi tin nhắn cho toàn đội
/health        —  Tự kiểm tra bot
/help          —  Xem các lệnh có sẵn
/lang          —  Đổi ngôn ngữ
```

---

### How `setMyCommands` is wired in the bot

The bot refreshes a user's popup commands at three moments:

1. **On `/start`** — first time the user opens the bot, after role lookup
2. **On role change** — when an admin runs `/setrole`, `/promote`, `/demote`, `/pausemember`, or `/resumemember` on this user
3. **On `/lang` change** — to swap the descriptions to the new language

Implementation sketch (`bot/services/menu_commands.py`):

```python
from aiogram.types import BotCommand, BotCommandScopeChat

async def refresh_user_menu(bot, user_id: int, role: str, lang: str):
    cmds = COMMAND_SETS[role][lang]   # see tables above
    await bot.set_my_commands(
        commands=[BotCommand(command=c, description=d) for c, d in cmds],
        scope=BotCommandScopeChat(chat_id=user_id),
        language_code=lang,   # 'en' | 'ja' | 'vi'
    )
```

The `COMMAND_SETS` dictionary lives in `bot/i18n/menu_commands.py` and contains the exact 3 × 6 = 18 lists shown above (one per role × language).

---

## Push alert matrix

| Alert type | Stranger | No access | View | View+Close | Full | Admin |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| 🟢 Position opened | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 🔴 Position closed (manual) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 🚨 Position closed (SL/TP hit) | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| ⚠️ Margin level < 200% | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| 📅 Daily P/L summary (with chart) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 🔔 Admin: member added/removed | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 🔔 Admin: token rotated | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 🔔 Admin: service restarted | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 🔔 Admin: abuse detected (10+ denials/5min) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

Push alerts are **per-account scoped**: users only receive alerts for accounts they have any role on. Admins receive alerts from ALL accounts.

---

## Inline keyboard navigation reference (menu-driven, no typing)

Every command above can also be accessed by tapping. The menu structure for each role:

### View role main menu
```
[📊 Status]    [📋 Positions]
[❓ Help]      [🌐 Language]
[◀️ Switch account]
```

### View + Close role main menu
```
[📊 Status]    [📋 Positions]
[❌ Close]                     ← drills into close submenu
[❓ Help]      [🌐 Language]
[◀️ Switch account]
```

### Full role main menu
```
[📊 Status]    [📋 Positions]
[❌ Close]     [🛡️ SL/TP]      ← both drill into submenus
[⚖️ Breakeven] [🚨 Panic]
[❓ Help]      [🌐 Language]
[◀️ Switch account]
```

### Admin role main menu
```
[📊 Status]    [📋 Positions]
[❌ Close]     [🛡️ SL/TP]
[⚖️ Breakeven] [🚨 Panic]
[⚙️ Settings]                  ← admin-only; drills into Team / Accounts / Audit / Broadcast
[❓ Help]      [🌐 Language]
[◀️ Switch account]
```

### Close submenu (View+Close and above)
```
[Close ALL (n positions, ±P/L)]
[Close BUYs only (n positions)]
[Close SELLs only (n positions)]
[◀️ Back]
```

### SL/TP submenu (Full and above)
```
[Set SL]       [Remove SL]
[Set TP]       [Remove TP]
[◀️ Back]
```

### Settings submenu (Admin only)
```
[👥 Team]
[🏦 Accounts]
[📜 Audit log]
[📢 Broadcast]
[🩺 Health & Stats]
[◀️ Back]
```

---

## Multi-step flows

These commands trigger guided conversational flows rather than executing immediately:

| Command | Steps |
|---|---|
| `/addmember` | 1. Bot: "Send Telegram user ID" → user types ID<br>2. Bot: "Display name?" → user types name<br>3. Bot shows account permission grid with inline buttons<br>4. Admin taps cells to set per-account roles<br>5. Tap ✅ Save → member created · or ❌ Cancel |
| `/addaccount` | 1. Bot: "Alias for this account?" → admin types<br>2. Bot generates EA token<br>3. Bot replies with token + bridge URL + EA setup snippet<br>4. Admin installs EA on Windows VPS with these values |
| `/sl <price>` (typed alone, no price) | 1. Bot: "Send the stop-loss price"<br>2. User types number<br>3. Bot shows confirm inline keyboard with affected position count<br>4. ✅ Confirm → applied · ❌ Cancel → aborted |
| `/panic` | 1. Bot: "Type the word PANIC (uppercase) to confirm closing all positions and disabling the EA on {account}"<br>2. User must reply exactly `PANIC` within 30 seconds<br>3. Anything else → flow cancelled |
| `/broadcast` | 1. Bot: "Send the message you want to broadcast"<br>2. Admin types message<br>3. Bot shows preview + recipient count<br>4. ✅ Send → fanned out · ❌ Cancel |

All flows can be aborted any time with `/cancel`.

---

## Audit log row format (admin reference)

Every command attempt — allowed or denied — writes a row:

```
2026-05-11T15:00:23+07:00  user=123456789  account=Personal-IS6FX  action=closeall  allowed=1  reason=ok
2026-05-11T15:01:45+07:00  user=987654321  account=Personal-IS6FX  action=sl        allowed=0  reason=role_insufficient (view < full)
2026-05-11T15:02:10+07:00  user=555444333  action=help               allowed=0  reason=stranger_lockout
```

Filterable via `/audit` flags.

---

## Localization (EN/JA/VI key parity)

All command descriptions, confirmation prompts, error messages, and help sections exist in three languages with **83/83 key parity** (verified in `tests/test_db.py::test_i18n_key_parity`).

User language is:
1. Auto-detected from Telegram client language on first `/start` (`vi` → Vietnamese, `ja` → Japanese, anything else → English)
2. User can switch any time via `/lang` or 🌐 button
3. Persists in `team_members.language`
4. Applied to ALL bot responses including dynamic `/help`

---

*Reference document v1.1 · Generated 2026-05-11 · Applies to sltp-tg-bot v1.0.0 + EA v1.3.0*
*Author: Thanh Nguyen · thanhglobalist@gmail.com · t.me/thanhglobalist*
