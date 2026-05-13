# sltp-tg-bot — v1.0.6 (2026-05-13)

## Context

Companion release to **BulkTPSLUpdater EA v1.4.0**, which removes
`TRADE_ACTION_CLOSE_BY` from the EA's mass-close engine entirely.

Bot-side change is small and is purely documentation/wording: the help
center previously claimed hedged closes used CLOSE_BY to save
commission, which was both misleading and (as of EA v1.4.0) no longer
true.

## History note

v1.0.5 (commit `998908c`, the bot-side `close_mode="market"` flag) was
reverted from Git after we concluded that the right fix lives in the
EA, not in a bot-side flag the EA had to honor. The reverted patch
added complexity without solving the bug.

v1.0.6 is built on top of **v1.0.4** (commit `18090a0`); v1.0.5 is no
longer in the history.

## Changes

### bot/handlers/trading.py

No change. v1.0.4's close handlers (`close_all`, `close_buys`,
`close_sells`, `panic`) already dispatched plain close actions to the
EA — and the EA at v1.4.0 now uses live-market closes for all of them
unconditionally. No `close_mode` flag needed.

### i18n.py — help_v2_closing rewritten (EN / JA / VI)

**Before:**

> Every action requires a confirmation tap.
> Hedged pairs use CLOSE_BY to save commission.

**After:**

> Every action requires a confirmation tap.
> Each position closes at the live market price — BUYs at Bid,
> SELLs at Ask. No CLOSE_BY netting.

Mirror translations applied to Japanese and Vietnamese. No other help
text touched.

### Versions

- `src/sltp_tg_bot/__init__.py`: `__version__ = "1.0.6"`
- `pyproject.toml`: `version = "1.0.6"`

## Validation

- `python3 -m py_compile` clean across all modules
- i18n parity: EN / JA / VI = 136 / 136 / 136 (unchanged from v1.0.4)
- No reference to `close_mode` or `forbid_close_by` anywhere in the
  codebase
- README's commands table and quick-start still point at /accounts
  (v1.0.4 wording preserved)

## EA pairing

| Component        | Version            |
| ---------------- | ------------------ |
| sltp-tg-bot      | 1.0.6              |
| BulkTPSLUpdater  | 1.4.0              |

Both must be deployed together. Older EA (≤ v1.3.0) will still work
with this bot (the wire protocol did not change) but will continue to
use CLOSE_BY pairing and reproduce the close-at-loss bug. Upgrade the
EA on every chart to v1.4.0.

## Author

Thanh Nguyen / thanhglobalist@gmail.com / https://t.me/thanhglobalist
