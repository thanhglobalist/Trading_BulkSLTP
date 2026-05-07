"""Initialise the SQLite schema and bootstrap the first admin.

Usage::

    python scripts/init_db.py

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the package importable when this script is run from a checkout.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from sltp_tg_bot import db  # noqa: E402
from sltp_tg_bot.config import get_settings  # noqa: E402


async def main() -> None:
    settings = get_settings()
    db_path = settings.db_path
    print(f"Database path: {db_path}")
    Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    await db.init_schema(db_path)
    print("Schema OK.")

    raw = input("Admin Telegram user ID (numeric): ").strip()
    try:
        admin_id = int(raw)
    except ValueError:
        print("ERROR: not a number")
        return
    name = input("Admin display name: ").strip() or "admin"

    async with db.connect(db_path) as conn:
        existing = await db.get_member(conn, admin_id)
        if existing:
            print(f"User {admin_id} already exists; promoting to admin.")
            await db.set_member_admin(conn, admin_id, True)
        else:
            await db.upsert_member(
                conn,
                user_id=admin_id,
                display_name=name,
                language="en",
                is_admin=True,
                created_by=admin_id,
            )
        await db.audit(
            conn,
            user_id=admin_id,
            account_id=None,
            action="bootstrap_admin",
            allowed=True,
            reason="init_db",
        )
    print("✅ Admin created.")


if __name__ == "__main__":
    asyncio.run(main())
