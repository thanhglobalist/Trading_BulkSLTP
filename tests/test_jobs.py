"""Jobs lifecycle: enqueue → claim → complete, plus expire on timeout."""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

from sltp_tg_bot import db


@pytest.fixture
async def setup_db():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "jobs.db")
        await db.init_schema(path)
        async with db.connect(path) as conn:
            aid, _ = await db.add_account(conn, alias="A1")
            await db.upsert_member(
                conn, user_id=1, display_name="admin",
                language="en", is_admin=True,
            )
        yield path, aid


@pytest.mark.asyncio
async def test_enqueue_claim_complete(setup_db):
    path, aid = setup_db
    async with db.connect(path) as conn:
        job_id = await db.enqueue_job(
            conn,
            account_id=aid,
            requested_by=1,
            action="status",
            args={},
            timeout_seconds=30,
        )
        assert job_id

        claimed = await db.claim_next_job(conn, account_id=aid)
        assert claimed["id"] == job_id
        assert claimed["status"] == "claimed"

        # No second job to claim
        empty = await db.claim_next_job(conn, account_id=aid)
        assert empty is None

        await db.complete_job(
            conn, job_id=job_id, success=True, payload={"summary": "ok"}
        )
        row = await db.get_job(conn, job_id=job_id)
        assert row["status"] == "completed"
        assert "summary" in row["result_json"]


@pytest.mark.asyncio
async def test_expire_stale_jobs(setup_db):
    path, aid = setup_db
    async with db.connect(path) as conn:
        # Enqueue with a 0-second timeout → already expired by the time we look
        job_id = await db.enqueue_job(
            conn,
            account_id=aid,
            requested_by=1,
            action="status",
            args={},
            timeout_seconds=0,
        )
        # Allow real-time clock to tick past
        await asyncio.sleep(0.01)
        n = await db.expire_stale_jobs(conn)
        assert n >= 1
        row = await db.get_job(conn, job_id=job_id)
        assert row["status"] == "expired"


@pytest.mark.asyncio
async def test_tenant_scoped_claim(setup_db):
    """A job for account A must NOT be claimable by account B."""
    path, aid = setup_db
    async with db.connect(path) as conn:
        bid, _ = await db.add_account(conn, alias="B1")
        job_id = await db.enqueue_job(
            conn, account_id=aid, requested_by=1, action="status",
            args={}, timeout_seconds=30,
        )
        # Account B's claim must come back empty
        empty = await db.claim_next_job(conn, account_id=bid)
        assert empty is None
        # Account A still has it pending
        own = await db.claim_next_job(conn, account_id=aid)
        assert own is not None and own["id"] == job_id
