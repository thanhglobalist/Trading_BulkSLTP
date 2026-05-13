"""Internationalization tables.

Three supported languages:
  * "en" — English (default)
  * "ja" — Japanese
  * "vi" — Vietnamese

All user-facing strings MUST be looked up via :func:`t` so language toggling
works uniformly across handlers, formatters, and alert templates.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

from typing import Iterable

# Languages we support. Order is meaningful for the language picker keyboard.
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "ja", "vi")
DEFAULT_LANGUAGE = "en"


def detect_language_from_client(client_lang: str | None) -> str:
    """Map a Telegram ``language_code`` to one of our supported codes."""
    if not client_lang:
        return DEFAULT_LANGUAGE
    code = client_lang.lower().split("-")[0]
    if code in SUPPORTED_LANGUAGES:
        return code
    return DEFAULT_LANGUAGE


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------
# IMPORTANT: keep all three language dicts in key parity. The unit test
# ``tests/test_db.py`` (and the build report) verifies this.
# ---------------------------------------------------------------------------

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # ---- Lockout / privacy ----
        "lockout": "⛔ This bot is private.",
        # ---- Welcome ----
        "welcome_title": "👋 Welcome to *SLTP Bot*",
        "welcome_body": (
            "This bot lets you control your MT5 trading account from Telegram.\n"
            "Use /accounts to begin or /help to see what you can do."
        ),
        "pick_language": "Please pick your language:",
        "language_set": "✅ Language updated.",
        # ---- Common buttons ----
        "btn_status": "📊 Status",
        "btn_positions": "📋 Positions",
        "btn_close": "❌ Close",
        "btn_close_all": "❌ Close ALL",
        "btn_close_buys": "❌ Close BUYs",
        "btn_close_sells": "❌ Close SELLs",
        "btn_sltp": "🛡️ SL/TP",
        "btn_sl": "🛡️ Set SL",
        "btn_tp": "🎯 Set TP",
        "btn_sloff": "🚫 Remove SL",
        "btn_tpoff": "🚫 Remove TP",
        "btn_be": "⚖️ Breakeven",
        "btn_panic": "🚨 Panic",
        "btn_help": "❓ Help",
        "btn_lang": "🌐 Language",
        "btn_switch_account": "◀️ Switch account",
        "btn_settings": "⚙️ Settings",
        "btn_confirm": "✅ Confirm",
        "btn_cancel": "❌ Cancel",
        "btn_back": "◀️ Back",
        # ---- Command descriptions (Telegram autocomplete) ----
        "cmd_desc_menu": "🏦 Switch trading account",
        "cmd_desc_status": "📊 Quick account status",
        "cmd_desc_positions": "📋 List open positions",
        "cmd_desc_help": "❓ Show help",
        "cmd_desc_lang": "🌐 Change language",
        "cmd_desc_getmyid": "🆔 Show your Telegram ID",
        "cmd_desc_settings": "⚙️ Admin settings",
        # ---- Header ----
        "header_fmt": "{alias} · Eq {equity} · P/L {pl} · v{ver}",
        "header_no_data": "{alias} · (no heartbeat) · v{ver}",
        # ---- Account picker ----
        "pick_account": "🏦 Pick a trading account to control",
        "no_accounts": "You don't have access to any account yet. Please contact your admin.",
        # ---- Confirm prompts ----
        "confirm_close_all": "Confirm: Close ALL {n} positions on *{alias}*?",
        "confirm_close_buys": "Confirm: Close all BUY positions on *{alias}*?",
        "confirm_close_sells": "Confirm: Close all SELL positions on *{alias}*?",
        "confirm_sl": "Confirm: Set SL = {price} on *{alias}* ({n} positions)?",
        "confirm_tp": "Confirm: Set TP = {price} on *{alias}* ({n} positions)?",
        "confirm_sloff": "Confirm: Remove SL on *{alias}* ({n} positions)?",
        "confirm_tpoff": "Confirm: Remove TP on *{alias}* ({n} positions)?",
        "confirm_be": "Confirm: Move to Breakeven on *{alias}*?",
        # ---- Panic ----
        "panic_prompt": (
            "🚨 *PANIC MODE*\n"
            "This will close *every* position on *{alias}* and disable trading.\n\n"
            "To proceed, type the word `PANIC` (uppercase) in the chat."
        ),
        "panic_armed": "🚨 Panic command sent for *{alias}*.",
        "panic_cancelled": "Panic cancelled.",
        # ---- Result strings ----
        "processing": "⏳ Processing…",
        "result_ok": "✅ Done: {summary}",
        "result_fail": "❌ Failed: {reason}",
        "result_timeout": "⌛ Timed out waiting for the EA. Please retry.",
        "cancelled": "Cancelled.",
        # ---- SL/TP entry ----
        "ask_sl_price": "Send the new SL price (e.g. `1.0850`).",
        "ask_tp_price": "Send the new TP price (e.g. `1.0950`).",
        "invalid_price": "❌ Invalid price. Send a number like `1.0850`.",
        # ---- Status / positions ----
        "status_title": "📊 *Status — {alias}*",
        "positions_title": "📋 *Positions — {alias}*",
        "no_positions": "No open positions.",
        # ---- Help sections ----
        "help_title": "📖 *Help*",
        "help_navigation": "*Navigation*\n• `/accounts` — pick a trading account\n• `/status` — quick status\n• `/positions` — list open positions\n• `/lang` — change language",
        "help_reading": "*Reading the Market*\nEvery screen header shows the account alias, equity, floating P/L and bot version.",
        "help_closing": "*Closing Positions*\n❌ Close → Close ALL / BUYs / SELLs. Each action requires a confirmation tap.",
        "help_sltp": "*Bulk SL/TP*\n🛡️ SL/TP applies a single price to every open position. Removing SL/TP clears the level.",
        "help_be": "*Portfolio Breakeven*\n⚖️ moves the SL of every open position to its entry price (after a small buffer).",
        "help_emergency": "*Emergency*\n🚨 Panic closes everything and disables trading until you re-enable it. You must type `PANIC` to confirm.",
        "help_admin": "*Admin*\n⚙️ Settings → manage team members, accounts, audit log and broadcasts.",
        "help_alerts": "*Push Alerts*\nThe bot pushes position open/close, margin warnings and a daily summary in your language.",
        "help_tips": "*Tips*\n• Use Switch account to manage multiple MT5 logins.\n• Permissions are per account — you may have View on one and Full on another.",
        "help_no_access": "You currently have no account access. Please contact your admin.",
        # ---- Help v2 (v1.0.3) ----
        "help_v2_title": "📖 Help — IS6FX Bulk SL/TP Bot",
        "help_v2_body": "Pick a topic.",
        "help_v2_stranger_title": "📖 Help",
        "help_v2_stranger_body": (
            "You have no account access yet.\n"
            "Send your Telegram ID to your admin so they can add you.\n\n"
            "🆔 Your Telegram ID: {user_id}"
        ),
        "help_v2_back_to_help": "⬅️ Back to help",
        "help_v2_back_to_menu": "⬅️ Back to menu",
        "help_v2_btn_navigation": "🧭 Navigation",
        "help_v2_btn_reading": "📊 Reading screens",
        "help_v2_btn_closing": "❌ Closing positions",
        "help_v2_btn_sltp": "🛡️ Bulk SL/TP",
        "help_v2_btn_be": "⚖️ Breakeven",
        "help_v2_btn_emergency": "🚨 Emergency",
        "help_v2_btn_alerts": "🔔 Push alerts",
        "help_v2_btn_roles": "👥 Roles & permissions",
        "help_v2_btn_commands": "💬 Commands list",
        "help_v2_btn_admin": "⚙️ Admin guide",
        "help_v2_btn_lang": "🌐 Language: {label}",
        "help_v2_btn_open_status": "📊 Open Status",
        "help_v2_btn_open_positions": "📋 Open Positions",
        "help_v2_btn_open_close": "❌ Open Close screen",
        "help_v2_btn_open_sltp": "🛡️ Open SL/TP screen",
        "help_v2_btn_open_be": "⚖️ Open Breakeven",
        "help_v2_btn_open_settings": "⚙️ Open Settings",
        "help_v2_btn_switch_account": "🔁 Switch account",
        "help_v2_nav": (
            "🧭 Navigation\n\n"
            "/accounts        Open the main panel\n"
            "/status      Quick equity & P/L\n"
            "/positions   List open trades\n"
            "/lang        Change language (EN / JA / VI)\n"
            "/help        This help (you're here)\n"
            "/getmyid     Show your Telegram ID\n\n"
            "Tip: Use 🔁 Switch account if you have access to more than one MT5."
        ),
        "help_v2_reading": (
            "📊 Reading screens\n\n"
            "Every screen header shows:\n"
            "  • Account alias\n"
            "  • Equity (live)\n"
            "  • Floating P/L\n"
            "  • Bot version\n\n"
            "Example: 🏦 IS6FX-Main · eq $12,480.50 · P/L +$184.20 · v1.0.3\n\n"
            "If …heartbeat lost… appears, the EA on the Windows VPS is offline."
        ),
        "help_v2_closing": (
            "❌ Closing positions (requires role: view+close or above)\n\n"
            "Tap ❌ Close on /accounts, then pick:\n"
            "  • Close ALL — every open position\n"
            "  • Close BUYs — only long positions 🔵\n"
            "  • Close SELLs — only short positions 🔴\n\n"
            "Every action requires a confirmation tap.\n"
            "Hedged pairs use CLOSE_BY to save commission."
        ),
        "help_v2_sltp": (
            "🛡️ Bulk SL/TP (requires role: full)\n\n"
            "Apply ONE Stop Loss or Take Profit price to every open position\n"
            "on the current account in a single round-trip.\n\n"
            "  • 🛡️ Set SL → send a price (e.g. 2350.0000 for XAUUSD.std)\n"
            "  • 🎯 Set TP → send a price\n"
            "  • 🗑️ Remove SL / 🗑️ Remove TP → clear that level\n\n"
            "Example: you have 4 open trades. Tap 🛡️ Set SL, send 2348.5000.\n"
            "All 4 trades get SL = 2348.5000 (buys below entry, sells above).\n\n"
            "Hedged BUY and SELL positions stay on their own sides correctly."
        ),
        "help_v2_be": (
            "⚖️ Portfolio Breakeven (requires role: full)\n\n"
            "Moves the SL of every open position to its entry price plus a\n"
            "small buffer (configured per account).\n\n"
            "Use after a winning move to lock in a no-loss state on the basket."
        ),
        "help_v2_emergency": (
            "🚨 Emergency / Panic\n\n"
            "If something goes wrong:\n"
            "  1. /accounts → 🚨 Emergency\n"
            "  2. Type PANIC in capital letters to confirm\n"
            "  3. The bot closes ALL positions and DISABLES trading until an\n"
            "     admin re-enables it.\n\n"
            "Use this only as a last resort."
        ),
        "help_v2_alerts": (
            "🔔 Push alerts\n\n"
            "The bot pushes these events in your language:\n"
            "  • Position opened / closed\n"
            "  • Margin warning when < 150%\n"
            "  • Daily summary at 23:59 server time\n\n"
            "To silence them temporarily, mute the chat in Telegram."
        ),
        "help_v2_roles": (
            "👥 Roles & permissions\n\n"
            "Roles are set per account by an admin:\n\n"
            "  none        no access\n"
            "  view        see status & positions\n"
            "  view_close  + close positions\n"
            "  full        + set SL/TP, breakeven, panic\n"
            "  admin       team, accounts, audit, broadcast\n\n"
            "You may have View on one account and Full on another.\n"
            "Need access to another account? Contact your admin."
        ),
        "help_v2_commands_user": (
            "💬 Commands list\n\n"
            "Public (everyone):\n"
            "  /accounts /status /positions /help /lang /getmyid\n\n"
            "Trading (role: view+close or full):\n"
            "  /closeall /closebuys /closesells\n\n"
            "Trading (role: full only):\n"
            "  /sl <price> /tp <price>\n"
            "  /sloff /tpoff\n"
            "  /be /panic\n\n"
            "The bot only accepts commands you have the role for."
        ),
        "help_v2_commands_admin_extra": (
            "\n\nAdmin only:\n"
            "  /addaccount /rename <old> <new> /rotate <alias>\n"
            "  /addmember /removemember <id> /pausemember <id> /resumemember <id>\n"
            "  /setrole <user_id> <alias> <role> /promote <user_id>\n"
            "  /audit /broadcast <message>\n\n"
            "Or use /settings for the inline UI."
        ),
        "help_v2_admin": (
            "⚙️ Admin guide\n\n"
            "Account management:\n"
            "  /addaccount               register a new MT5 + token\n"
            "  /rename <old> <new>       change account alias\n"
            "  /rotate <alias>           reissue token (old one dies)\n\n"
            "Team management:\n"
            "  /addmember   multi-step add\n"
            "  /removemember <id>        hard-delete (audit kept)\n"
            "  /pausemember <id>         soft-disable\n"
            "  /resumemember <id>        re-enable\n"
            "  /setrole <user_id> <alias> <role>\n"
            "  /promote <user_id>        grant admin\n\n"
            "Audit & broadcast:\n"
            "  /audit (filter by user, account, or action)\n"
            "  /broadcast <message>\n\n"
            "Or use /settings for the inline UI for everything above."
        ),
        "help_v2_pick_language": "🌐 Choose language",
        "help_accounts_label": "*Your accounts*",
        # ---- Errors ----
        "err_not_allowed": "🚫 Action not allowed.",
        "err_unknown": "Something went wrong. Please retry.",
        "err_admin_only": "🚫 Admins only.",
        "err_last_admin": "🚫 You can't remove the last admin.",
        # ---- Admin labels ----
        "admin_team": "👥 Team",
        "admin_accounts": "🏦 Accounts",
        "admin_audit": "📜 Audit",
        "admin_broadcast": "📢 Broadcast",
        "admin_add_member": "➕ Add member",
        "admin_ask_user_id": "Send the new member's Telegram user ID (numeric).",
        "admin_ask_display_name": "Send a display name for this member.",
        "admin_pick_perms": "Tap a cell to set the role for that account, then ✅ Save.",
        "admin_member_added": "✅ Member added.",
        "admin_account_added": "✅ Account added. Token (shown ONCE):\n`{token}`",
        "admin_token_rotated": "🔁 Token rotated. New token (shown ONCE):\n`{token}`",
        # ---- Account actions (rename / inline rotate) ----
        "admin_rename_btn": "✏️ Rename",
        "admin_rotate_btn": "🔁 Rotate token",
        "admin_account_header": "*Account:* `{alias}`\n\nPick an action below.",
        "admin_accounts_empty": "_No accounts registered yet. Use_ /addaccount `<alias>`.",
        "admin_accounts_tap_hint": "_Tap an account to rename or rotate its token._",
        "admin_rename_prompt": "Send the *new alias* for `{alias}` (1–32 chars, A–Z a–z 0–9 \\- \\_ only). Send /cancel to abort.",
        "admin_rename_ok": "✅ Renamed: {old} → {new}",
        "admin_rename_taken": "🚫 Alias '{alias}' is already in use by another account.",
        "admin_rename_invalid": "🚫 Invalid alias. Use 1–32 chars: letters, digits, '-' or '_'.",
        "admin_account_not_found": "🚫 Account not found.",
        # ---- Alerts ----
        "alert_pos_open": "🟢 *{alias}* — opened {side} {volume} {symbol} @ {price}",
        "alert_pos_close": "🔴 *{alias}* — closed {side} {volume} {symbol} @ {price} (P/L {pl})",
        "alert_margin": "⚠️ *{alias}* — margin level {level}% (warning)",
        "alert_daily_summary": "📅 *{alias}* — daily summary: {trades} trades, P/L {pl}",
        # ---- Misc ----
        "your_id": "Your Telegram user ID is `{user_id}`.",
    },

    "ja": {
        # ---- Lockout ----
        "lockout": "⛔ このボットは非公開です。",
        # ---- Welcome ----
        "welcome_title": "👋 *SLTP Bot* へようこそ",
        "welcome_body": (
            "このボットでは Telegram から MT5 口座を操作できます。\n"
            "/accounts で開始、/help で機能一覧を表示します。"
        ),
        "pick_language": "言語を選択してください：",
        "language_set": "✅ 言語を変更しました。",
        # ---- Common buttons ----
        "btn_status": "📊 状況",
        "btn_positions": "📋 ポジション",
        "btn_close": "❌ クローズ",
        "btn_close_all": "❌ 全部クローズ",
        "btn_close_buys": "❌ 買いをクローズ",
        "btn_close_sells": "❌ 売りをクローズ",
        "btn_sltp": "🛡️ SL/TP",
        "btn_sl": "🛡️ SL設定",
        "btn_tp": "🎯 TP設定",
        "btn_sloff": "🚫 SL解除",
        "btn_tpoff": "🚫 TP解除",
        "btn_be": "⚖️ 建値移動",
        "btn_panic": "🚨 パニック",
        "btn_help": "❓ ヘルプ",
        "btn_lang": "🌐 言語",
        "btn_switch_account": "◀️ 口座切替",
        "btn_settings": "⚙️ 設定",
        "btn_confirm": "✅ 実行",
        "btn_cancel": "❌ 取消",
        "btn_back": "◀️ 戻る",
        # ---- Command descriptions (Telegram autocomplete) ----
        "cmd_desc_menu": "🏦 取引口座を切替",
        "cmd_desc_status": "📊 口座ステータスを確認",
        "cmd_desc_positions": "📋 ポジション一覧",
        "cmd_desc_help": "❓ ヘルプを表示",
        "cmd_desc_lang": "🌐 言語を変更",
        "cmd_desc_getmyid": "🆔 Telegram ID を表示",
        "cmd_desc_settings": "⚙️ 管理者設定",
        # ---- Header ----
        "header_fmt": "{alias} · 残高 {equity} · 損益 {pl} · v{ver}",
        "header_no_data": "{alias} · (未接続) · v{ver}",
        # ---- Account picker ----
        "pick_account": "🏦 操作する取引口座を選択",
        "no_accounts": "アクセス可能な口座がありません。管理者にお問い合わせください。",
        # ---- Confirm prompts ----
        "confirm_close_all": "確認：*{alias}* の全 {n} ポジションをクローズしますか？",
        "confirm_close_buys": "確認：*{alias}* の買いポジションを全てクローズしますか？",
        "confirm_close_sells": "確認：*{alias}* の売りポジションを全てクローズしますか？",
        "confirm_sl": "確認：*{alias}* の SL を {price} に設定しますか？（{n} 件）",
        "confirm_tp": "確認：*{alias}* の TP を {price} に設定しますか？（{n} 件）",
        "confirm_sloff": "確認：*{alias}* の SL を解除しますか？（{n} 件）",
        "confirm_tpoff": "確認：*{alias}* の TP を解除しますか？（{n} 件）",
        "confirm_be": "確認：*{alias}* を建値移動しますか？",
        # ---- Panic ----
        "panic_prompt": (
            "🚨 *パニックモード*\n"
            "*{alias}* の全ポジションをクローズし、取引を停止します。\n\n"
            "実行するには、チャットに `PANIC`（大文字）と入力してください。"
        ),
        "panic_armed": "🚨 *{alias}* にパニック指示を送信しました。",
        "panic_cancelled": "パニックを取り消しました。",
        # ---- Result strings ----
        "processing": "⏳ 処理中…",
        "result_ok": "✅ 完了：{summary}",
        "result_fail": "❌ 失敗：{reason}",
        "result_timeout": "⌛ EA からの応答がタイムアウトしました。再度お試しください。",
        "cancelled": "取消しました。",
        # ---- SL/TP entry ----
        "ask_sl_price": "新しい SL 価格を入力してください（例：`1.0850`）。",
        "ask_tp_price": "新しい TP 価格を入力してください（例：`1.0950`）。",
        "invalid_price": "❌ 価格が不正です。`1.0850` のような数値を送信してください。",
        # ---- Status / positions ----
        "status_title": "📊 *状況 — {alias}*",
        "positions_title": "📋 *ポジション — {alias}*",
        "no_positions": "オープンポジションはありません。",
        # ---- Help sections ----
        "help_title": "📖 *ヘルプ*",
        "help_navigation": "*ナビゲーション*\n• `/accounts` — メインメニュー\n• `/status` — 状況確認\n• `/positions` — ポジション一覧\n• `/lang` — 言語変更",
        "help_reading": "*画面の見方*\n各画面の上部に口座名・残高・含み損益・バージョンが表示されます。",
        "help_closing": "*ポジションのクローズ*\n❌ クローズ → 全部 / 買い / 売り。各操作には確認タップが必要です。",
        "help_sltp": "*一括 SL/TP*\n🛡️ SL/TP は全オープンポジションに同一価格を適用します。解除で値を消去します。",
        "help_be": "*建値移動*\n⚖️ 全オープンポジションの SL を建値（小バッファ込）に移動します。",
        "help_emergency": "*緊急停止*\n🚨 パニックは全決済し、再有効化まで取引を停止します。`PANIC` の入力が必要です。",
        "help_admin": "*管理者機能*\n⚙️ 設定 → メンバー、口座、監査ログ、ブロードキャストの管理。",
        "help_alerts": "*プッシュ通知*\n建玉開閉、証拠金警告、日次サマリーを選択言語で送信します。",
        "help_tips": "*ヒント*\n• 口座切替で複数の MT5 を管理できます。\n• 権限は口座ごとです（口座Aは閲覧のみ、口座Bはフルなど）。",
        "help_no_access": "現在アクセス可能な口座がありません。管理者にお問い合わせください。",
        # ---- Help v2 (v1.0.3) ----
        "help_v2_title": "📖 ヘルプ — IS6FX Bulk SL/TP Bot",
        "help_v2_body": "トピックを選択してください。",
        "help_v2_stranger_title": "📖 ヘルプ",
        "help_v2_stranger_body": (
            "まだ口座へのアクセス権がありません。\n"
            "下記の Telegram ID を管理者に送付し、登録を依頼してください。\n\n"
            "🆔 あなたの Telegram ID: {user_id}"
        ),
        "help_v2_back_to_help": "⬅️ ヘルプに戻る",
        "help_v2_back_to_menu": "⬅️ メニューに戻る",
        "help_v2_btn_navigation": "🧭 ナビゲーション",
        "help_v2_btn_reading": "📊 画面の見方",
        "help_v2_btn_closing": "❌ ポジション決済",
        "help_v2_btn_sltp": "🛡️ 一括 SL/TP",
        "help_v2_btn_be": "⚖️ ブレイクイーブン",
        "help_v2_btn_emergency": "🚨 緊急停止",
        "help_v2_btn_alerts": "🔔 プッシュ通知",
        "help_v2_btn_roles": "👥 役割と権限",
        "help_v2_btn_commands": "💬 コマンド一覧",
        "help_v2_btn_admin": "⚙️ 管理者ガイド",
        "help_v2_btn_lang": "🌐 言語: {label}",
        "help_v2_btn_open_status": "📊 ステータスを開く",
        "help_v2_btn_open_positions": "📋 ポジション一覧を開く",
        "help_v2_btn_open_close": "❌ 決済画面を開く",
        "help_v2_btn_open_sltp": "🛡️ SL/TP 画面を開く",
        "help_v2_btn_open_be": "⚖️ ブレイクイーブンを開く",
        "help_v2_btn_open_settings": "⚙️ 設定を開く",
        "help_v2_btn_switch_account": "🔁 口座切替",
        "help_v2_nav": (
            "🧭 ナビゲーション\n\n"
            "/accounts        メインパネルを開く\n"
            "/status      残高と損益を確認\n"
            "/positions   保有ポジション一覧\n"
            "/lang        言語切替 (EN / JA / VI)\n"
            "/help        このヘルプ\n"
            "/getmyid     自分の Telegram ID 表示\n\n"
            "ヒント：複数の MT5 口座をお使いの場合は 🔁 口座切替 をご利用ください。"
        ),
        "help_v2_reading": (
            "📊 画面の見方\n\n"
            "各画面のヘッダーに表示される情報：\n"
            "  • 口座エイリアス\n"
            "  • 有効証拠金（リアルタイム）\n"
            "  • 含み損益\n"
            "  • ボットのバージョン\n\n"
            "例： 🏦 IS6FX-Main · eq $12,480.50 · P/L +$184.20 · v1.0.3\n\n"
            "…heartbeat lost… と表示された場合、Windows VPS の EA がオフラインです。"
        ),
        "help_v2_closing": (
            "❌ ポジション決済 (必要な権限：view+close 以上)\n\n"
            "/accounts の ❌ 決済 から選択：\n"
            "  • 全決済 — 保有中の全ポジション\n"
            "  • 買い決済 — 買いポジションのみ 🔵\n"
            "  • 売り決済 — 売りポジションのみ 🔴\n\n"
            "操作には確認タップが必要です。\n"
            "ヘッジ建てでは手数料節約のため CLOSE_BY を使用します。"
        ),
        "help_v2_sltp": (
            "🛡️ 一括 SL/TP (必要な権限：full)\n\n"
            "現在の口座の 全ポジション に対し、ひとつの SL または TP 価格を\n"
            "一括で適用します。\n\n"
            "  • 🛡️ SL 設定 → 価格を送信（例 XAUUSD.std なら 2350.0000）\n"
            "  • 🎯 TP 設定 → 価格を送信\n"
            "  • 🗑️ SL/TP 解除 → 該当ラインを削除\n\n"
            "例： 4 つのポジションがある場合、🛡️ SL 設定で 2348.5000 を送信すると、\n"
            "4 つ全てに SL = 2348.5000 が設定されます（買いは下、売りは上）。\n\n"
            "両建ての買い・売りも正しくそれぞれの側に配置されます。"
        ),
        "help_v2_be": (
            "⚖️ ポートフォリオ・ブレイクイーブン (必要な権限：full)\n\n"
            "全ポジションの SL をエントリー価格＋小バッファに移動します\n"
            "（バッファは口座ごとに設定）。\n\n"
            "含み益が出ている場合に、損失をなくす形でロックするのに使います。"
        ),
        "help_v2_emergency": (
            "🚨 緊急停止 / Panic\n\n"
            "緊急時の手順：\n"
            "  1. /accounts → 🚨 Emergency\n"
            "  2. 確認のため大文字で PANIC と入力\n"
            "  3. ボットが全ポジションを決済し、管理者が再開するまで\n"
            "     取引を停止します。\n\n"
            "最終手段としてのみ使用してください。"
        ),
        "help_v2_alerts": (
            "🔔 プッシュ通知\n\n"
            "選択された言語で以下のイベントを通知します：\n"
            "  • ポジションのオープン／クローズ\n"
            "  • 証拠金維持率が 150% を下回った時の警告\n"
            "  • サーバー時間 23:59 の日次サマリー\n\n"
            "一時的に止めたい場合は Telegram でチャットをミュートしてください。"
        ),
        "help_v2_roles": (
            "👥 役割と権限\n\n"
            "役割は口座ごとに管理者が設定します：\n\n"
            "  none        アクセス不可\n"
            "  view        ステータス／ポジション閲覧\n"
            "  view_close  ＋ ポジション決済\n"
            "  full        ＋ SL/TP 設定、BE、Panic\n"
            "  admin       チーム、口座、監査、ブロードキャスト\n\n"
            "口座 A は閲覧のみ、口座 B はフル権限といった設定も可能です。\n"
            "他の口座のアクセスが必要な場合は管理者にご連絡ください。"
        ),
        "help_v2_commands_user": (
            "💬 コマンド一覧\n\n"
            "共通（全員）：\n"
            "  /accounts /status /positions /help /lang /getmyid\n\n"
            "取引コマンド (view+close または full):\n"
            "  /closeall /closebuys /closesells\n\n"
            "取引コマンド (full のみ):\n"
            "  /sl <価格> /tp <価格>\n"
            "  /sloff /tpoff\n"
            "  /be /panic\n\n"
            "権限のあるコマンドのみ受け付けます。"
        ),
        "help_v2_commands_admin_extra": (
            "\n\n管理者専用：\n"
            "  /addaccount /rename <旧> <新> /rotate <エイリアス>\n"
            "  /addmember /removemember <id> /pausemember <id> /resumemember <id>\n"
            "  /setrole <user_id> <エイリアス> <役割> /promote <user_id>\n"
            "  /audit /broadcast <メッセージ>\n\n"
            "または /settings でインライン UI が利用可能です。"
        ),
        "help_v2_admin": (
            "⚙️ 管理者ガイド\n\n"
            "口座管理：\n"
            "  /addaccount               新規 MT5 とトークンを登録\n"
            "  /rename <旧> <新>         エイリアス変更\n"
            "  /rotate <エイリアス>      トークン再発行（旧トークン無効化）\n\n"
            "チーム管理：\n"
            "  /addmember   多段階追加\n"
            "  /removemember <id>        ハード削除（監査ログは保持）\n"
            "  /pausemember <id>         一時停止\n"
            "  /resumemember <id>        再開\n"
            "  /setrole <user_id> <エイリアス> <役割>\n"
            "  /promote <user_id>        管理者権限付与\n\n"
            "監査とブロードキャスト：\n"
            "  /audit (ユーザー／口座／アクションでフィルタ)\n"
            "  /broadcast <メッセージ>\n\n"
            "または /settings で全機能のインライン UI が使えます。"
        ),
        "help_v2_pick_language": "🌐 言語を選択",
        "help_accounts_label": "*ご利用可能な口座*",
        # ---- Errors ----
        "err_not_allowed": "🚫 この操作は許可されていません。",
        "err_unknown": "エラーが発生しました。再度お試しください。",
        "err_admin_only": "🚫 管理者専用です。",
        "err_last_admin": "🚫 最後の管理者は削除できません。",
        # ---- Admin labels ----
        "admin_team": "👥 メンバー",
        "admin_accounts": "🏦 口座",
        "admin_audit": "📜 監査",
        "admin_broadcast": "📢 配信",
        "admin_add_member": "➕ メンバー追加",
        "admin_ask_user_id": "新しいメンバーの Telegram ユーザーID（数値）を送信してください。",
        "admin_ask_display_name": "このメンバーの表示名を入力してください。",
        "admin_pick_perms": "セルをタップして口座ごとの権限を設定し、✅ 保存してください。",
        "admin_member_added": "✅ メンバーを追加しました。",
        "admin_account_added": "✅ 口座を追加しました。トークン（一度のみ表示）：\n`{token}`",
        "admin_token_rotated": "🔁 トークンを更新しました（一度のみ表示）：\n`{token}`",
        # ---- Account actions (rename / inline rotate) ----
        "admin_rename_btn": "✏️ 名称変更",
        "admin_rotate_btn": "🔁 トークン更新",
        "admin_account_header": "*口座:* `{alias}`\n\n下のボタンから操作を選んでください。",
        "admin_accounts_empty": "_登録されている口座はありません。_ /addaccount `<alias>` _を使用してください。_",
        "admin_accounts_tap_hint": "_名称変更またはトークン更新は口座をタップしてください。_",
        "admin_rename_prompt": "`{alias}` の *新しいエイリアス* を送信してください（1–32文字、A–Z a–z 0–9 \\- \\_ のみ）。/cancel で中止。",
        "admin_rename_ok": "✅ 名称変更完了：{old} → {new}",
        "admin_rename_taken": "🚫 エイリアス '{alias}' は他の口座で使用中です。",
        "admin_rename_invalid": "🚫 エイリアスが不正です。1–32文字、英数字、'-' または '_' のみ使用可能です。",
        "admin_account_not_found": "🚫 口座が見つかりません。",
        # ---- Alerts ----
        "alert_pos_open": "🟢 *{alias}* — 新規 {side} {volume} {symbol} @ {price}",
        "alert_pos_close": "🔴 *{alias}* — 決済 {side} {volume} {symbol} @ {price}（損益 {pl}）",
        "alert_margin": "⚠️ *{alias}* — 証拠金維持率 {level}%（警告）",
        "alert_daily_summary": "📅 *{alias}* — 日次サマリー：{trades} 件、損益 {pl}",
        # ---- Misc ----
        "your_id": "あなたの Telegram ユーザーID は `{user_id}` です。",
    },

    "vi": {
        # ---- Lockout ----
        "lockout": "⛔ Bot này là riêng tư.",
        # ---- Welcome ----
        "welcome_title": "👋 Chào mừng đến với *SLTP Bot*",
        "welcome_body": (
            "Bot này giúp Quý khách điều khiển tài khoản MT5 ngay trên Telegram.\n"
            "Dùng /accounts để bắt đầu hoặc /help để xem hướng dẫn."
        ),
        "pick_language": "Vui lòng chọn ngôn ngữ:",
        "language_set": "✅ Đã cập nhật ngôn ngữ.",
        # ---- Common buttons ----
        "btn_status": "📊 Trạng thái",
        "btn_positions": "📋 Vị thế",
        "btn_close": "❌ Đóng",
        "btn_close_all": "❌ Đóng TẤT CẢ",
        "btn_close_buys": "❌ Đóng lệnh MUA",
        "btn_close_sells": "❌ Đóng lệnh BÁN",
        "btn_sltp": "🛡️ SL/TP",
        "btn_sl": "🛡️ Đặt SL",
        "btn_tp": "🎯 Đặt TP",
        "btn_sloff": "🚫 Bỏ SL",
        "btn_tpoff": "🚫 Bỏ TP",
        "btn_be": "⚖️ Hòa vốn",
        "btn_panic": "🚨 Khẩn cấp",
        "btn_help": "❓ Trợ giúp",
        "btn_lang": "🌐 Ngôn ngữ",
        "btn_switch_account": "◀️ Đổi tài khoản",
        "btn_settings": "⚙️ Cài đặt",
        "btn_confirm": "✅ Xác nhận",
        "btn_cancel": "❌ Hủy",
        "btn_back": "◀️ Quay lại",
        # ---- Command descriptions (Telegram autocomplete) ----
        "cmd_desc_menu": "🏦 Đổi tài khoản giao dịch",
        "cmd_desc_status": "📊 Trạng thái tài khoản",
        "cmd_desc_positions": "📋 Danh sách vị thế",
        "cmd_desc_help": "❓ Xem trợ giúp",
        "cmd_desc_lang": "🌐 Đổi ngôn ngữ",
        "cmd_desc_getmyid": "🆔 Xem Telegram ID",
        "cmd_desc_settings": "⚙️ Cài đặt quản trị",
        # ---- Header ----
        "header_fmt": "{alias} · Vốn {equity} · L/L {pl} · v{ver}",
        "header_no_data": "{alias} · (chưa kết nối) · v{ver}",
        # ---- Account picker ----
        "pick_account": "🏦 Chọn tài khoản giao dịch để điều khiển",
        "no_accounts": "Bạn chưa có quyền truy cập tài khoản nào. Vui lòng liên hệ quản trị viên.",
        # ---- Confirm prompts ----
        "confirm_close_all": "Xác nhận: Đóng TẤT CẢ {n} vị thế trên *{alias}*?",
        "confirm_close_buys": "Xác nhận: Đóng tất cả lệnh MUA trên *{alias}*?",
        "confirm_close_sells": "Xác nhận: Đóng tất cả lệnh BÁN trên *{alias}*?",
        "confirm_sl": "Xác nhận: Đặt SL = {price} trên *{alias}* ({n} vị thế)?",
        "confirm_tp": "Xác nhận: Đặt TP = {price} trên *{alias}* ({n} vị thế)?",
        "confirm_sloff": "Xác nhận: Bỏ SL trên *{alias}* ({n} vị thế)?",
        "confirm_tpoff": "Xác nhận: Bỏ TP trên *{alias}* ({n} vị thế)?",
        "confirm_be": "Xác nhận: Đưa về hòa vốn trên *{alias}*?",
        # ---- Panic ----
        "panic_prompt": (
            "🚨 *CHẾ ĐỘ KHẨN CẤP*\n"
            "Lệnh này sẽ đóng *toàn bộ* vị thế trên *{alias}* và tạm dừng giao dịch.\n\n"
            "Để tiếp tục, hãy gõ `PANIC` (chữ in hoa) vào khung chat."
        ),
        "panic_armed": "🚨 Đã gửi lệnh khẩn cấp cho *{alias}*.",
        "panic_cancelled": "Đã hủy lệnh khẩn cấp.",
        # ---- Result strings ----
        "processing": "⏳ Đang xử lý…",
        "result_ok": "✅ Hoàn tất: {summary}",
        "result_fail": "❌ Thất bại: {reason}",
        "result_timeout": "⌛ Quá thời gian chờ phản hồi từ EA. Vui lòng thử lại.",
        "cancelled": "Đã hủy.",
        # ---- SL/TP entry ----
        "ask_sl_price": "Gửi mức SL mới (ví dụ `1.0850`).",
        "ask_tp_price": "Gửi mức TP mới (ví dụ `1.0950`).",
        "invalid_price": "❌ Giá không hợp lệ. Vui lòng gửi số như `1.0850`.",
        # ---- Status / positions ----
        "status_title": "📊 *Trạng thái — {alias}*",
        "positions_title": "📋 *Vị thế — {alias}*",
        "no_positions": "Không có vị thế đang mở.",
        # ---- Help sections ----
        "help_title": "📖 *Trợ giúp*",
        "help_navigation": "*Điều hướng*\n• `/accounts` — mở menu chính\n• `/status` — xem trạng thái nhanh\n• `/positions` — danh sách vị thế\n• `/lang` — đổi ngôn ngữ",
        "help_reading": "*Đọc thị trường*\nDòng tiêu đề mỗi màn hình hiển thị tên tài khoản, vốn, lãi/lỗ trôi nổi và phiên bản bot.",
        "help_closing": "*Đóng vị thế*\n❌ Đóng → TẤT CẢ / MUA / BÁN. Mỗi thao tác cần xác nhận thêm một lần.",
        "help_sltp": "*SL/TP hàng loạt*\n🛡️ SL/TP áp dụng một mức giá cho mọi vị thế đang mở. Bỏ SL/TP sẽ xóa mức hiện có.",
        "help_be": "*Hòa vốn danh mục*\n⚖️ Đưa SL của mọi vị thế đang mở về giá vào lệnh (cộng đệm nhỏ).",
        "help_emergency": "*Khẩn cấp*\n🚨 Lệnh khẩn cấp đóng toàn bộ và tạm dừng giao dịch cho đến khi bật lại. Cần gõ `PANIC` để xác nhận.",
        "help_admin": "*Quản trị*\n⚙️ Cài đặt → quản lý thành viên, tài khoản, nhật ký kiểm toán và phát thông báo.",
        "help_alerts": "*Cảnh báo đẩy*\nBot gửi cảnh báo mở/đóng vị thế, cảnh báo ký quỹ và tóm tắt cuối ngày bằng ngôn ngữ của bạn.",
        "help_tips": "*Mẹo*\n• Dùng Đổi tài khoản để quản lý nhiều MT5.\n• Quyền là theo từng tài khoản (có thể chỉ Xem ở tài khoản này, Toàn quyền ở tài khoản khác).",
        "help_no_access": "Hiện bạn chưa có quyền trên tài khoản nào. Vui lòng liên hệ quản trị viên.",
        # ---- Help v2 (v1.0.3) ----
        "help_v2_title": "📖 Trợ giúp — IS6FX Bulk SL/TP Bot",
        "help_v2_body": "Chọn một chủ đề.",
        "help_v2_stranger_title": "📖 Trợ giúp",
        "help_v2_stranger_body": (
            "Bạn chưa có quyền truy cập tài khoản nào.\n"
            "Gửi Telegram ID của bạn cho quản trị viên để được thêm vào hệ thống.\n\n"
            "🆔 Telegram ID của bạn: {user_id}"
        ),
        "help_v2_back_to_help": "⬅️ Quay lại trợ giúp",
        "help_v2_back_to_menu": "⬅️ Quay lại menu",
        "help_v2_btn_navigation": "🧭 Điều hướng",
        "help_v2_btn_reading": "📊 Đọc màn hình",
        "help_v2_btn_closing": "❌ Đóng lệnh",
        "help_v2_btn_sltp": "🛡️ SL/TP hàng loạt",
        "help_v2_btn_be": "⚖️ Hòa vốn",
        "help_v2_btn_emergency": "🚨 Khẩn cấp",
        "help_v2_btn_alerts": "🔔 Cảnh báo đẩy",
        "help_v2_btn_roles": "👥 Vai trò & quyền",
        "help_v2_btn_commands": "💬 Danh sách lệnh",
        "help_v2_btn_admin": "⚙️ Hướng dẫn quản trị",
        "help_v2_btn_lang": "🌐 Ngôn ngữ: {label}",
        "help_v2_btn_open_status": "📊 Mở Trạng thái",
        "help_v2_btn_open_positions": "📋 Mở Danh sách lệnh",
        "help_v2_btn_open_close": "❌ Mở màn hình Đóng",
        "help_v2_btn_open_sltp": "🛡️ Mở màn hình SL/TP",
        "help_v2_btn_open_be": "⚖️ Mở Hòa vốn",
        "help_v2_btn_open_settings": "⚙️ Mở Cài đặt",
        "help_v2_btn_switch_account": "🔁 Đổi tài khoản",
        "help_v2_nav": (
            "🧭 Điều hướng\n\n"
            "/accounts        Mở bảng điều khiển chính\n"
            "/status      Xem nhanh equity & P/L\n"
            "/positions   Danh sách lệnh đang mở\n"
            "/lang        Đổi ngôn ngữ (EN / JA / VI)\n"
            "/help        Trợ giúp (bạn đang ở đây)\n"
            "/getmyid     Hiển thị Telegram ID\n\n"
            "Mẹo: Dùng 🔁 Đổi tài khoản nếu bạn có nhiều MT5."
        ),
        "help_v2_reading": (
            "📊 Đọc màn hình\n\n"
            "Mỗi màn hình có header hiển thị:\n"
            "  • Tên tài khoản (alias)\n"
            "  • Equity (thời gian thực)\n"
            "  • P/L đang trôi\n"
            "  • Phiên bản bot\n\n"
            "Ví dụ: 🏦 IS6FX-Main · eq $12,480.50 · P/L +$184.20 · v1.0.3\n\n"
            "Nếu thấy …heartbeat lost…, EA trên Windows VPS đang offline."
        ),
        "help_v2_closing": (
            "❌ Đóng lệnh (yêu cầu vai trò: view+close trở lên)\n\n"
            "Trong /accounts chạm ❌ Đóng, sau đó chọn:\n"
            "  • Đóng TẤT CẢ — toàn bộ lệnh đang mở\n"
            "  • Đóng BUY — chỉ lệnh mua 🔵\n"
            "  • Đóng SELL — chỉ lệnh bán 🔴\n\n"
            "Mọi thao tác đều cần xác nhận thêm 1 lần.\n"
            "Lệnh đối ứng (hedged) dùng CLOSE_BY để tiết kiệm phí."
        ),
        "help_v2_sltp": (
            "🛡️ SL/TP hàng loạt (yêu cầu vai trò: full)\n\n"
            "Áp một mức Stop Loss hoặc Take Profit cho tất cả lệnh đang mở\n"
            "trên tài khoản hiện tại trong một lần.\n\n"
            "  • 🛡️ Đặt SL → gửi giá (vd. 2350.0000 cho XAUUSD.std)\n"
            "  • 🎯 Đặt TP → gửi giá\n"
            "  • 🗑️ Bỏ SL / 🗑️ Bỏ TP → xóa mức tương ứng\n\n"
            "Ví dụ: bạn có 4 lệnh. Chạm 🛡️ Đặt SL, gửi 2348.5000.\n"
            "Cả 4 lệnh sẽ có SL = 2348.5000 (buy ở dưới, sell ở trên).\n\n"
            "Lệnh hedge BUY/SELL được giữ đúng phía của mình."
        ),
        "help_v2_be": (
            "⚖️ Hòa vốn toàn danh mục (yêu cầu vai trò: full)\n\n"
            "Dời SL của mọi lệnh về giá vào lệnh cộng một buffer nhỏ\n"
            "(được cấu hình riêng cho từng tài khoản).\n\n"
            "Dùng sau khi giá đi đúng hướng để khóa trạng thái không-lỗ."
        ),
        "help_v2_emergency": (
            "🚨 Khẩn cấp / Panic\n\n"
            "Khi có sự cố:\n"
            "  1. /accounts → 🚨 Emergency\n"
            "  2. Nhập PANIC in hoa để xác nhận\n"
            "  3. Bot đóng TẤT CẢ lệnh và TẠM KHÓA giao dịch cho đến khi\n"
            "     quản trị viên mở lại.\n\n"
            "Chỉ dùng như phương án cuối cùng."
        ),
        "help_v2_alerts": (
            "🔔 Cảnh báo đẩy\n\n"
            "Bot đẩy các sự kiện sau bằng ngôn ngữ bạn chọn:\n"
            "  • Mở / đóng lệnh\n"
            "  • Cảnh báo margin khi < 150%\n"
            "  • Tóm tắt ngày lúc 23:59 giờ server\n\n"
            "Muốn im lặng tạm thời, hãy mute hội thoại trong Telegram."
        ),
        "help_v2_roles": (
            "👥 Vai trò & quyền\n\n"
            "Vai trò được quản trị viên gán theo từng tài khoản:\n\n"
            "  none        không truy cập\n"
            "  view        xem trạng thái & lệnh\n"
            "  view_close  + đóng lệnh\n"
            "  full        + đặt SL/TP, hòa vốn, panic\n"
            "  admin       quản lý team, tài khoản, audit, broadcast\n\n"
            "Bạn có thể chỉ Xem ở tài khoản này và Toàn quyền ở tài khoản khác.\n"
            "Cần thêm quyền? Liên hệ quản trị viên."
        ),
        "help_v2_commands_user": (
            "💬 Danh sách lệnh\n\n"
            "Công khai (mọi người):\n"
            "  /accounts /status /positions /help /lang /getmyid\n\n"
            "Lệnh giao dịch (vai trò: view+close hoặc full):\n"
            "  /closeall /closebuys /closesells\n\n"
            "Lệnh giao dịch (chỉ full):\n"
            "  /sl <giá> /tp <giá>\n"
            "  /sloff /tpoff\n"
            "  /be /panic\n\n"
            "Bot chỉ chấp nhận lệnh phù hợp với vai trò của bạn."
        ),
        "help_v2_commands_admin_extra": (
            "\n\nChỉ quản trị viên:\n"
            "  /addaccount /rename <cũ> <mới> /rotate <alias>\n"
            "  /addmember /removemember <id> /pausemember <id> /resumemember <id>\n"
            "  /setrole <user_id> <alias> <role> /promote <user_id>\n"
            "  /audit /broadcast <thông điệp>\n\n"
            "Hoặc dùng /settings để có UI inline."
        ),
        "help_v2_admin": (
            "⚙️ Hướng dẫn quản trị\n\n"
            "Quản lý tài khoản:\n"
            "  /addaccount               đăng ký MT5 + token mới\n"
            "  /rename <cũ> <mới>        đổi alias tài khoản\n"
            "  /rotate <alias>           cấp lại token (token cũ bị hủy)\n\n"
            "Quản lý thành viên:\n"
            "  /addmember   thêm theo nhiều bước\n"
            "  /removemember <id>        xóa cứng (audit vẫn lưu)\n"
            "  /pausemember <id>         tạm khóa\n"
            "  /resumemember <id>        mở lại\n"
            "  /setrole <user_id> <alias> <role>\n"
            "  /promote <user_id>        cấp quyền admin\n\n"
            "Audit và broadcast:\n"
            "  /audit (lọc theo user, tài khoản, hành động)\n"
            "  /broadcast <thông điệp>\n\n"
            "Hoặc dùng /settings để có UI inline cho mọi tác vụ trên."
        ),
        "help_v2_pick_language": "🌐 Chọn ngôn ngữ",
        "help_accounts_label": "*Tài khoản của bạn*",
        # ---- Errors ----
        "err_not_allowed": "🚫 Thao tác không được phép.",
        "err_unknown": "Đã xảy ra lỗi. Vui lòng thử lại.",
        "err_admin_only": "🚫 Chỉ dành cho quản trị viên.",
        "err_last_admin": "🚫 Không thể xóa quản trị viên cuối cùng.",
        # ---- Admin labels ----
        "admin_team": "👥 Thành viên",
        "admin_accounts": "🏦 Tài khoản",
        "admin_audit": "📜 Kiểm toán",
        "admin_broadcast": "📢 Thông báo",
        "admin_add_member": "➕ Thêm thành viên",
        "admin_ask_user_id": "Gửi Telegram user ID (số) của thành viên mới.",
        "admin_ask_display_name": "Gửi tên hiển thị cho thành viên này.",
        "admin_pick_perms": "Chạm vào ô để chọn vai trò cho từng tài khoản, sau đó ✅ Lưu.",
        "admin_member_added": "✅ Đã thêm thành viên.",
        "admin_account_added": "✅ Đã thêm tài khoản. Token (chỉ hiển thị MỘT LẦN):\n`{token}`",
        "admin_token_rotated": "🔁 Đã xoay token (chỉ hiển thị MỘT LẦN):\n`{token}`",
        # ---- Account actions (rename / inline rotate) ----
        "admin_rename_btn": "✏️ Đổi tên",
        "admin_rotate_btn": "🔁 Xoay token",
        "admin_account_header": "*Tài khoản:* `{alias}`\n\nChọn thao tác bên dưới.",
        "admin_accounts_empty": "_Chưa có tài khoản nào. Dùng_ /addaccount `<alias>`.",
        "admin_accounts_tap_hint": "_Chạm vào một tài khoản để đổi tên hoặc xoay token._",
        "admin_rename_prompt": "Gửi *tên mới* cho `{alias}` (1–32 ký tự, chỉ dùng A–Z a–z 0–9 \\- \\_). Gửi /cancel để hủy.",
        "admin_rename_ok": "✅ Đã đổi tên: {old} → {new}",
        "admin_rename_taken": "🚫 Tên '{alias}' đã được dùng cho tài khoản khác.",
        "admin_rename_invalid": "🚫 Tên không hợp lệ. Dùng 1–32 ký tự: chữ cái, số, '-' hoặc '_'.",
        "admin_account_not_found": "🚫 Không tìm thấy tài khoản.",
        # ---- Alerts ----
        "alert_pos_open": "🟢 *{alias}* — mở {side} {volume} {symbol} @ {price}",
        "alert_pos_close": "🔴 *{alias}* — đóng {side} {volume} {symbol} @ {price} (L/L {pl})",
        "alert_margin": "⚠️ *{alias}* — mức ký quỹ {level}% (cảnh báo)",
        "alert_daily_summary": "📅 *{alias}* — tóm tắt cuối ngày: {trades} lệnh, L/L {pl}",
        # ---- Misc ----
        "your_id": "Telegram user ID của bạn là `{user_id}`.",
    },
}


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Translate ``key`` into ``lang`` (falling back to English).

    Any keyword arguments are passed to :py:meth:`str.format` so callers can
    interpolate values, e.g. ``t("confirm_close_all", "vi", n=3, alias="A1")``.
    """
    code = lang if lang in TRANSLATIONS else DEFAULT_LANGUAGE
    table = TRANSLATIONS[code]
    template = table.get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def all_keys() -> set[str]:
    """Return the union of keys across all languages (used in tests)."""
    keys: set[str] = set()
    for table in TRANSLATIONS.values():
        keys.update(table.keys())
    return keys


def missing_keys_per_language() -> dict[str, list[str]]:
    """Diagnostic: list of keys missing per language vs. the union."""
    union = all_keys()
    return {
        lang: sorted(union - set(table.keys()))
        for lang, table in TRANSLATIONS.items()
    }


def language_label(code: str) -> str:
    """Human-readable label for the language picker."""
    return {
        "en": "🇬🇧 English",
        "ja": "🇯🇵 日本語",
        "vi": "🇻🇳 Tiếng Việt",
    }.get(code, code)


def supported_languages() -> Iterable[str]:
    return SUPPORTED_LANGUAGES
