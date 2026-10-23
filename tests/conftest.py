"""Test fixtures — REAL Postgres for the claim suite (no mocks).

The suite creates its own test database (bumped random suffix so
parallel runs never collide), applies ../../schema.sql, and truncates
between tests. Requires a local postgres the current user can reach.

Env overrides (CI-friendly):
    BAI_TEST_DSN  — full DSN, e.g. postgres:///bai_test
    BAI_PG_ADMIN  — DSN of a maintenance DB for creating the test DB
                   (default: postgres:///postgres)
"""

import os
import secrets
import time

import psycopg

import pytest

ADMIN_DSN = os.environ.get("BAI_PG_ADMIN", "postgres:///postgres")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(REPO_ROOT, "schema.sql")


def _wait_for_postgres(dsn: str, timeout: float = 30.0) -> None:
    """Retry-loop: the PG daemon may still be starting when tests launch."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with psycopg.connect(dsn, autocommit=True):
                return
        except Exception as exc:  # noqa: BLE001 — probe loop
            last = exc
            time.sleep(0.5)
    raise RuntimeError(f"postgres not reachable at {dsn!r}: {last}")


_wait_for_postgres(ADMIN_DSN)

TEST_DB = "bai_test_" + secrets.token_hex(4)
TEST_DSN = os.environ.get("BAI_TEST_DSN", f"postgres:///{TEST_DB}")

with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
    conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}"')
    conn.execute(f'CREATE DATABASE "{TEST_DB}"')

with psycopg.connect(TEST_DSN, autocommit=True) as conn:
    with open(SCHEMA_PATH) as fh:
        conn.execute(fh.read())


@pytest.fixture()
def db():
    """A fresh connection with all tables truncated — test isolation."""
    with psycopg.connect(TEST_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE hit_logs, blobs, shouts RESTART IDENTITY CASCADE"
            )
        conn.commit()
        yield conn
        conn.rollback()


@pytest.fixture()
def api(db):
    """Flask test client wired to the SAME real test database."""
    import importlib

    import app as app_mod

    app_mod = importlib.reload(app_mod)
    flask_app = app_mod.create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-0123456789abcdef0123456789abcdef",
            "DATABASE_URL": db.info.dsn,
        }
    )
    with flask_app.test_client() as client:
        yield client


@pytest.fixture()
def make_shout(db):
    """Factory: insert a shout row (no blob) with controllable fields."""

    def _make(
        *,
        shout_type: str = "text",
        max_hits: int = 1,
        expires_in_s: float = 3600.0,
        expired: bool = False,
    ) -> str:
        from app import now_utc  # the production module under test

        h = "h" + secrets.token_hex(16)
        sk = "s" + secrets.token_hex(16)
        exp = now_utc()
        exp = exp.replace(
            second=0, microsecond=0
        )  # keep deterministic-ish; deltas use seconds below
        import datetime as dt

        delta = dt.timedelta(seconds=-60 if expired else expires_in_s)
        db.execute(
            """INSERT INTO shouts
                   (hash, storage_key, shout_type, max_hits, expires_at)
               VALUES (%s, %s, %s, %s, %s)""",
            (h, sk, shout_type, max_hits, exp + delta),
        )
        db.commit()
        return h

    return _make
