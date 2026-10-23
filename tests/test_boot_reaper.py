"""RED slice 4 — boot-guard + reaper (two-phase GC, phase 2).

Boot-guard (design §4.5, 6a): fail loud on missing/weak SECRET_KEY.
Reaper (design §3): flip expired-active rows, physically delete
inactive rows + their blobs only after a grace period.
"""

import datetime as dt

import psycopg
import pytest

from app import now_utc, reap

STRONG_KEY = "x" * 32


def test_boot_guard_requires_strong_secret(db):
    from app import create_app

    dsn = db.info.dsn
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"DATABASE_URL": dsn})  # no SECRET_KEY at all
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"DATABASE_URL": dsn, "SECRET_KEY": "change-me-in-production"})
    app = create_app({"DATABASE_URL": dsn, "SECRET_KEY": STRONG_KEY})
    assert app is not None


def test_reaper_flips_expired_active_rows(db, make_shout):
    h = make_shout(expired=True)  # active=TRUE, expires_at in the past
    reap(db)
    row = db.execute(
        "SELECT is_active, burned_at IS NOT NULL FROM shouts WHERE hash=%s",
        (h,),
    ).fetchone()
    assert row == (False, True)  # phase 1 applied by the reaper


def test_reaper_deletes_only_past_grace(db, make_shout):
    h = make_shout(max_hits=1, expired=True)
    # give it a blob so cascade-delete is observable
    sk = db.execute(
        "SELECT storage_key FROM shouts WHERE hash=%s", (h,)
    ).fetchone()[0]
    db.execute(
        "INSERT INTO blobs VALUES (%s, 'text/plain', 1, 'x')", (sk,)
    )
    db.commit()

    reap(db)  # flips it inactive NOW -> inside grace -> must survive
    assert db.execute("SELECT 1 FROM shouts WHERE hash=%s", (h,)).fetchone()
    assert db.execute("SELECT 1 FROM blobs WHERE storage_key=%s", (sk,)).fetchone()

    # simulate grace elapsed: burned_at pushed past the cutoff
    db.execute(
        "UPDATE shouts SET burned_at = %s",
        (now_utc() - dt.timedelta(hours=2),),
    )
    db.commit()
    reap(db)
    assert db.execute("SELECT 1 FROM shouts WHERE hash=%s", (h,)).fetchone() is None
    assert db.execute("SELECT 1 FROM blobs WHERE storage_key=%s", (sk,)).fetchone() is None


def test_reaper_never_touches_live_shouts(db, make_shout):
    h = make_shout(max_hits=5, expires_in_s=3600)
    sk = db.execute(
        "SELECT storage_key FROM shouts WHERE hash=%s", (h,)
    ).fetchone()[0]
    db.execute(
        "INSERT INTO blobs VALUES (%s, 'text/plain', 1, 'x')", (sk,)
    )
    db.commit()
    reap(db)
    assert db.execute("SELECT is_active FROM shouts WHERE hash=%s", (h,)).fetchone()[0]
    assert db.execute("SELECT 1 FROM blobs WHERE storage_key=%s", (sk,)).fetchone()
