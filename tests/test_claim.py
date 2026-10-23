"""RED slice 1 — the atomic claim primitive.

Every read of every content type must go through claim(). These tests
fail until app.py provides: now_utc(), claim(), and get_shout().
"""

import concurrent.futures
import datetime as dt

import psycopg

from app import claim, now_utc


def test_claim_wins_and_increments(db, make_shout):
    h = make_shout(max_hits=3)
    assert claim(db, h) is True
    row = db.execute(
        "SELECT current_hits, is_active FROM shouts WHERE hash = %s", (h,)
    ).fetchone()
    assert row[0] == 1 and row[1] is True


def test_claim_rejects_at_max_hits(db, make_shout):
    h = make_shout(max_hits=2)
    assert claim(db, h) is True
    assert claim(db, h) is True
    assert claim(db, h) is False  # burned on the 3rd attempt
    row = db.execute(
        "SELECT current_hits FROM shouts WHERE hash = %s", (h,)
    ).fetchone()
    assert row[0] == 2  # never exceeded max


def test_claim_rejects_expired(db, make_shout):
    h = make_shout(expired=True)
    assert claim(db, h) is False
    # and it must FLIP the row inactive (two-phase GC, phase 1)
    row = db.execute(
        "SELECT is_active, burned_at IS NOT NULL FROM shouts WHERE hash = %s",
        (h,),
    ).fetchone()
    assert row == (False, True)


def test_claim_rejects_inactive(db, make_shout):
    h = make_shout(max_hits=5)
    db.execute("UPDATE shouts SET is_active = FALSE WHERE hash = %s", (h,))
    db.commit()
    assert claim(db, h) is False


def test_claim_nonexistent_hash(db):
    assert claim(db, "doesnotexist" + "0" * 12) is False


def test_claim_is_atomic_under_concurrency(db, make_shout):
    """THE test: max_hits concurrent claims -> exactly max_hits winners.

    Fresh connection per claim, like N app replicas would have.
    """
    h = make_shout(max_hits=3)
    dsn = db.info.dsn  # same DB, separate connections

    def one_claim(_):
        with psycopg.connect(dsn) as conn:
            return claim(conn, h)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(one_claim, range(12)))

    assert sum(results) == 3  # exactly max_hits winners, never more
    row = db.execute(
        "SELECT current_hits FROM shouts WHERE hash = %s", (h,)
    ).fetchone()
    assert row[0] == 3


def test_now_utc_is_naive():
    """Design rule: naive-UTC everywhere (the v2 TypeError tombstone)."""
    val = now_utc()
    assert isinstance(val, dt.datetime)
    assert val.tzinfo is None
