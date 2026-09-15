"""Integration tests for the Alembic migration drift fix.

These tests exercise a *real* Postgres database (native `Enum` types,
`Numeric`, and foreign-key absence checks don't translate meaningfully to a
SQLite/mocked substitute) to prove three things end to end:

1. `alembic upgrade head` actually executes DDL again (regression guard for
   the `alembic/env.py` async/sync bug where an `async def` was passed to
   `connection.run_sync()`, so migrations silently never ran).
2. The regenerated baseline migration (`001_baseline_schema.py`) is a
   byte-for-byte structural match for the current SQLAlchemy models - i.e.
   the schema-drift bug described in KNOWN_ISSUES.md is fixed, and any
   *future* drift (a model changed without a matching migration) will fail
   this test immediately instead of being silently masked.
3. The new create_all()-free `init_db()` and the "existing deployment"
   `alembic stamp head` workflow documented in the README both behave as
   described.

Requires a reachable Postgres instance. Configure it via the
`TEST_DATABASE_URL` environment variable (async DSN, e.g.
``postgresql+asyncpg://postgres:postgres@localhost:5432/v2ray_bot_schema_test``).
If it can't be reached, every test in this module is skipped rather than
failed, consistent with the rest of the (currently mock-only) suite.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT_DIR = Path(__file__).resolve().parent.parent
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/v2ray_bot_schema_test",
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _run_alembic(*args: str, db_url: str) -> subprocess.CompletedProcess:
    """Invoke Alembic exactly the way entrypoint.sh / a developer would."""
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    env.setdefault("BOT_TOKEN", "test-token")
    env.setdefault("ADMIN_IDS", "1")
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )


async def _db_reachable(db_url: str) -> bool:
    try:
        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


async def _reset_schema(db_url: str) -> None:
    """Drop and recreate the public schema so each test starts from empty."""
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


async def _table_names(db_url: str) -> list[str]:
    engine = create_async_engine(db_url)

    def _get(sync_conn):
        return sa.inspect(sync_conn).get_table_names()

    async with engine.connect() as conn:
        names = await conn.run_sync(_get)
    await engine.dispose()
    return names


async def _foreign_keys(db_url: str, table: str) -> list[dict]:
    engine = create_async_engine(db_url)

    def _get(sync_conn):
        return sa.inspect(sync_conn).get_foreign_keys(table)

    async with engine.connect() as conn:
        fks = await conn.run_sync(_get)
    await engine.dispose()
    return fks


async def _columns(db_url: str, table: str) -> dict[str, dict]:
    engine = create_async_engine(db_url)

    def _get(sync_conn):
        return {c["name"]: c for c in sa.inspect(sync_conn).get_columns(table)}

    async with engine.connect() as conn:
        cols = await conn.run_sync(_get)
    await engine.dispose()
    return cols


async def _metadata_diff(db_url: str) -> list:
    """The core drift check: compare live DB schema to Base.metadata."""
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext

    from app.database.session import Base
    import app.database.models  # noqa: F401  (registers all models on Base.metadata)

    engine = create_async_engine(db_url)

    def _compare(sync_conn):
        ctx = MigrationContext.configure(sync_conn)
        return compare_metadata(ctx, Base.metadata)

    async with engine.connect() as conn:
        diff = await conn.run_sync(_compare)
    await engine.dispose()
    return diff


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def clean_db():
    if not asyncio.run(_db_reachable(TEST_DB_URL)):
        pytest.skip(
            f"No test Postgres reachable at {TEST_DB_URL}. Set TEST_DATABASE_URL "
            "to run the Alembic schema-parity integration tests."
        )
    asyncio.run(_reset_schema(TEST_DB_URL))
    yield TEST_DB_URL
    asyncio.run(_reset_schema(TEST_DB_URL))


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


def test_upgrade_head_actually_runs_and_creates_all_tables(clean_db):
    """Regression guard for the env.py async/sync bug: before the fix,
    `alembic upgrade head` exited 0 but created nothing at all."""
    result = _run_alembic("upgrade", "head", db_url=clean_db)
    assert result.returncode == 0, result.stderr

    tables = set(asyncio.run(_table_names(clean_db)))
    expected = {
        "users",
        "products",
        "orders",
        "configs",
        "payment_receipts",
        "admin_actions",
        "alembic_version",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_alembic_version_row_matches_head(clean_db):
    """Confirms the migration was actually applied, not silently skipped."""
    _run_alembic("upgrade", "head", db_url=clean_db)

    async def _version():
        engine = create_async_engine(clean_db)
        async with engine.connect() as conn:
            row = (await conn.execute(text("SELECT version_num FROM alembic_version"))).first()
        await engine.dispose()
        return row[0] if row else None

    assert asyncio.run(_version()) is not None


def test_migration_matches_models_exactly(clean_db):
    """The headline test: zero drift between the migration-produced schema
    and the current SQLAlchemy models. If a model is ever changed without a
    matching migration, this test fails immediately instead of the drift
    being discovered only when someone runs `alembic upgrade head` for real."""
    result = _run_alembic("upgrade", "head", db_url=clean_db)
    assert result.returncode == 0, result.stderr

    diff = asyncio.run(_metadata_diff(clean_db))
    assert diff == [], f"Schema drift detected between migration and models: {diff}"


def test_admin_actions_admin_id_has_no_foreign_key(clean_db):
    """The old migration invented a FK from admin_actions.admin_id to
    users.id even though the model intentionally stores a raw Telegram ID
    with no FK (the "Bug #3 fix" design). Guard against it reappearing."""
    _run_alembic("upgrade", "head", db_url=clean_db)
    fks = asyncio.run(_foreign_keys(clean_db, "admin_actions"))
    assert fks == [], f"admin_actions should have no foreign keys, found: {fks}"


def test_previously_drifted_columns_now_match_models(clean_db):
    """Spot-check the specific columns/types KNOWN_ISSUES.md called out."""
    _run_alembic("upgrade", "head", db_url=clean_db)

    products = asyncio.run(_columns(clean_db, "products"))
    assert "duration" in products, "products.duration_days should be products.duration"
    assert "duration_days" not in products

    orders = asyncio.run(_columns(clean_db, "orders"))
    assert "unit_price" in orders
    assert orders["unit_price"]["nullable"] is False
    assert "receipt_file_unique_id" in orders

    receipts = asyncio.run(_columns(clean_db, "payment_receipts"))
    assert "chat_id" in receipts
    assert receipts["chat_id"]["nullable"] is False
    assert receipts["message_id"]["nullable"] is False

    users = asyncio.run(_columns(clean_db, "users"))
    assert "is_admin" not in users, "users.is_admin should not exist (it's a hardcoded property)"

    for table, pk_col in (
        ("products", "id"),
        ("orders", "id"),
        ("configs", "id"),
        ("payment_receipts", "id"),
        ("admin_actions", "id"),
    ):
        cols = asyncio.run(_columns(clean_db, table))
        assert "BIGINT" in str(cols[pk_col]["type"]).upper(), (
            f"{table}.{pk_col} should be BigInteger, got {cols[pk_col]['type']}"
        )


def test_init_db_no_longer_creates_schema(clean_db, monkeypatch):
    """Phase 2 regression guard: init_db() must not call create_all() anymore.
    Against a schema-less database it should only verify connectivity."""
    from app.database import session as session_module

    test_engine = create_async_engine(clean_db)
    monkeypatch.setattr(session_module, "engine", test_engine)

    asyncio.run(session_module.init_db())

    tables = asyncio.run(_table_names(clean_db))
    assert tables == [], (
        "init_db() created tables - the create_all() safety net should have "
        "been removed so schema drift surfaces loudly instead of being masked."
    )

    asyncio.run(test_engine.dispose())


def test_stamp_head_on_preexisting_create_all_schema_then_upgrade_is_noop(clean_db):
    """Simulates upgrading an existing deployment per the README:
    a database whose tables were provisioned by the old create_all()
    behaviour, with no alembic_version row yet.
    """
    import app.database.models  # noqa: F401
    from app.database.session import Base

    async def _create_all_like_old_behaviour():
        engine = create_async_engine(clean_db)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create_all_like_old_behaviour())

    # Running upgrade head directly (without stamping first) should fail,
    # because Alembic doesn't know the tables already exist.
    result = _run_alembic("upgrade", "head", db_url=clean_db)
    assert result.returncode != 0, (
        "Expected `alembic upgrade head` to fail against an unstamped "
        "pre-existing schema (tables already exist) - if this now succeeds, "
        "the migration's create_table calls may have started using "
        "if_not_exists semantics and this scenario should be revisited."
    )

    # Per README: `alembic stamp head` should mark it current without DDL.
    stamp_result = _run_alembic("stamp", "head", db_url=clean_db)
    assert stamp_result.returncode == 0, stamp_result.stderr

    # Now upgrade head should be a true no-op.
    upgrade_result = _run_alembic("upgrade", "head", db_url=clean_db)
    assert upgrade_result.returncode == 0, upgrade_result.stderr

    diff = asyncio.run(_metadata_diff(clean_db))
    assert diff == [], f"Stamped existing deployment still drifted: {diff}"
