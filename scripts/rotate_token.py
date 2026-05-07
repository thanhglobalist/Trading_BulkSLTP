"""CLI: rotate an account's EA bearer token.

Usage::

    python scripts/rotate_token.py <account_alias>

Prints the new token to stdout exactly once. Update the EA configuration
on the Windows VPS with this new token immediately — the previous token
becomes invalid.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from sltp_tg_bot import db  # noqa: E402
from sltp_tg_bot.config import get_settings  # noqa: E402


async def main(alias: str) -> int:
    settings = get_settings()
    async with db.connect(settings.db_path) as conn:
        token = await db.rotate_account_token(conn, alias)
        if token is None:
            print(f"ERROR: account alias not found: {alias}", file=sys.stderr)
            return 2
        await db.audit(
            conn,
            user_id=None,
            account_id=None,
            action="rotate_token_cli",
            allowed=True,
            reason=alias,
        )
    print(f"NEW EA TOKEN for '{alias}':")
    print(token)
    print("Set this in your MT5 EA configuration immediately.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(asyncio.run(main(sys.argv[1])))
