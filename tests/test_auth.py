"""Authorization checks — role hierarchy, tenant isolation, admin invariant."""

from __future__ import annotations

import os
import tempfile

import pytest

from sltp_tg_bot import db
from sltp_tg_bot.bot.auth import can_remove_or_demote_admin, check_action


@pytest.fixture
async def setup_db():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "auth.db")
        await db.init_schema(path)
        async with db.connect(path) as conn:
            # Two accounts
            a1, _ = await db.add_account(conn, alias="A1")
            a2, _ = await db.add_account(conn, alias="A2")
            # Two team members
            await db.upsert_member(
                conn, user_id=1, display_name="alice",
                language="en", is_admin=True,
            )
            await db.upsert_member(
                conn, user_id=2, display_name="bob",
                language="en", is_admin=False,
            )
            # bob has 'view' on A1 only
            await db.set_permission(
                conn, user_id=2, account_id=a1, role="view", granted_by=1,
            )
        yield path, a1, a2


@pytest.mark.asyncio
async def test_view_role_can_status_but_not_close(setup_db):
    path, a1, _ = setup_db
    async with db.connect(path) as conn:
        ok = await check_action(
            conn, user_id=2, account_id=a1, action="status"
        )
        assert ok.allowed and ok.role == "view"
        bad = await check_action(
            conn, user_id=2, account_id=a1, action="close_all"
        )
        assert not bad.allowed


@pytest.mark.asyncio
async def test_tenant_isolation_no_cross_account(setup_db):
    """bob must NOT have any role on A2."""
    path, _, a2 = setup_db
    async with db.connect(path) as conn:
        bad = await check_action(
            conn, user_id=2, account_id=a2, action="status"
        )
        assert not bad.allowed
        accounts = await db.list_accounts_for_user(conn, 2)
        aliases = [a["alias"] for a in accounts]
        assert aliases == ["A1"]


@pytest.mark.asyncio
async def test_admin_implicit_full(setup_db):
    """Admins always get FULL role on every account."""
    path, _, a2 = setup_db
    async with db.connect(path) as conn:
        ok = await check_action(
            conn, user_id=1, account_id=a2, action="panic"
        )
        assert ok.allowed
        # admin sees both accounts
        accounts = await db.list_accounts_for_user(conn, 1)
        assert {a["alias"] for a in accounts} == {"A1", "A2"}


@pytest.mark.asyncio
async def test_at_least_one_admin_invariant(setup_db):
    path, _, _ = setup_db
    async with db.connect(path) as conn:
        # Only one admin (alice). Demoting her must be blocked.
        assert not await can_remove_or_demote_admin(conn, target_user_id=1)
        # Add a second admin → demoting alice now allowed.
        await db.upsert_member(
            conn, user_id=99, display_name="carol",
            language="en", is_admin=True,
        )
        assert await can_remove_or_demote_admin(conn, target_user_id=1)


@pytest.mark.asyncio
async def test_unknown_action_denied(setup_db):
    path, a1, _ = setup_db
    async with db.connect(path) as conn:
        res = await check_action(
            conn, user_id=2, account_id=a1, action="hack_admin",
        )
        assert not res.allowed and res.reason == "unknown_action"


@pytest.mark.asyncio
async def test_stranger_denied(setup_db):
    path, a1, _ = setup_db
    async with db.connect(path) as conn:
        res = await check_action(
            conn, user_id=99999, account_id=a1, action="status",
        )
        assert not res.allowed and res.reason == "not_member"
