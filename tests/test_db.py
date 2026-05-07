"""Smoke tests for db.py — schema, accounts CRUD, permissions CRUD,
and i18n key parity across all three supported languages.

Run with::

    pytest -q tests/test_db.py
"""

from __future__ import annotations

import os
import tempfile

import pytest

from sltp_tg_bot import db
from sltp_tg_bot.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, all_keys


@pytest.fixture
async def dbpath():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.db")
        await db.init_schema(path)
        yield path


@pytest.mark.asyncio
async def test_schema_creates_all_tables(dbpath):
    async with db.connect(dbpath) as conn:
        cur = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = [r[0] for r in await cur.fetchall()]
    for table in (
        "accounts", "team_members", "permissions",
        "jobs", "alerts", "audit_log", "sessions",
    ):
        assert table in rows


@pytest.mark.asyncio
async def test_accounts_crud(dbpath):
    async with db.connect(dbpath) as conn:
        aid, token = await db.add_account(conn, alias="A1")
        assert aid > 0 and token
        row = await db.get_account_by_id(conn, aid)
        assert row["alias"] == "A1"
        same = await db.get_account_by_token(conn, token)
        assert same["id"] == aid
        new_token = await db.rotate_account_token(conn, "A1")
        assert new_token != token
        # old token is invalid now
        old = await db.get_account_by_token(conn, token)
        assert old is None


@pytest.mark.asyncio
async def test_permissions_crud(dbpath):
    async with db.connect(dbpath) as conn:
        aid, _ = await db.add_account(conn, alias="A1")
        await db.upsert_member(
            conn, user_id=42, display_name="bob",
            language="vi", is_admin=False,
        )
        # default role: none
        assert await db.get_role(conn, user_id=42, account_id=aid) == db.ROLE_NONE

        await db.set_permission(
            conn, user_id=42, account_id=aid, role="view", granted_by=1,
        )
        assert await db.get_role(conn, user_id=42, account_id=aid) == "view"

        await db.set_permission(
            conn, user_id=42, account_id=aid, role="full", granted_by=1,
        )
        assert await db.get_role(conn, user_id=42, account_id=aid) == "full"

        await db.revoke_permission(conn, user_id=42, account_id=aid)
        assert await db.get_role(conn, user_id=42, account_id=aid) == db.ROLE_NONE


# ---------------------------------------------------------------------------
# i18n parity check — required by the build spec.
# ---------------------------------------------------------------------------


def test_i18n_key_parity():
    """Every translation dict must contain the same set of keys."""
    union = all_keys()
    for lang in SUPPORTED_LANGUAGES:
        assert lang in TRANSLATIONS, f"missing language: {lang}"
        missing = sorted(union - set(TRANSLATIONS[lang].keys()))
        assert not missing, f"language '{lang}' is missing keys: {missing}"


def test_i18n_lockout_present_in_all_languages():
    for lang in SUPPORTED_LANGUAGES:
        assert TRANSLATIONS[lang]["lockout"]
