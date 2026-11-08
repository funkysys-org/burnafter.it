"""Storage honesty: 'messages die with the session' must be true of
STORAGE, not just access — expired live_sessions rows are DELETED by
the reap cycle and their messages cascade."""

import time


def _app(live_db, **over):
    from app import create_app

    cfg = {
        "TESTING": True,
        "SECRET_KEY": "test-key-0123456789abcdef0123456789abcdef",
        "DATABASE_URL": live_db.info.dsn,
        **over,
    }
    app = create_app(cfg)
    app.config["REDIS_URL"] = "redis://localhost:6379/15"
    return app


def _create(c, **kw):
    return c.post("/live", json={"maxhours": 1, "cap": None, **kw})


def test_expired_sessions_and_messages_are_deleted(live_db):
    import psycopg

    from live import reap_dead_live

    app = _app(live_db)
    with app.test_client() as c:
        b = _create(c).get_json()
        h, tok = b["session_hash"], b["token"]
        # a message on the session
        r = c.post(
            f"/live/{h}/say",
            json={"nickname": "X", "body": "dies with the tape"},
        )
        assert r.status_code == 200
        # END it, then expire the fuse in the DB (past expires_at)
        c.post(f"/live/{h}/end", query_string={"token": tok})
        live_db.execute(
            "UPDATE live_sessions SET expires_at = %s WHERE hash = %s",
            (live_db.execute("SELECT now() AT TIME ZONE 'utc'").fetchone()[0], h),
        )
        # NOTE: expires_at now ~ now; ensure strictly past
        import datetime

        live_db.execute(
            "UPDATE live_sessions SET expires_at = %s WHERE hash = %s",
            (live_db.execute("SELECT now() AT TIME ZONE 'utc'").fetchone()[0]
             - datetime.timedelta(seconds=1), h),
        )
        live_db.commit()

        sid = live_db.execute(
            "SELECT id FROM live_sessions WHERE hash = %s", (h,)
        ).fetchone()
        assert sid is not None
        n_msgs = live_db.execute(
            "SELECT count(*) FROM live_messages WHERE session_id = %s", (sid[0],)
        ).fetchone()[0]
        assert n_msgs == 1

        ended, deleted = reap_dead_live(live_db)
        assert deleted >= 1
        assert live_db.execute(
            "SELECT 1 FROM live_sessions WHERE hash = %s", (h,)
        ).fetchone() is None  # row gone
        assert live_db.execute(
            "SELECT count(*) FROM live_messages WHERE session_id = %s", (sid[0],)
        ).fetchone()[0] == 0  # messages cascaded


def test_unexpired_sessions_survive_the_reap(live_db):
    from live import reap_dead_live

    app = _app(live_db)
    with app.test_client() as c:
        b = _create(c).get_json()  # fresh 1h fuse
        h = b["session_hash"]
        reap_dead_live(live_db)
        assert live_db.execute(
            "SELECT 1 FROM live_sessions WHERE hash = %s", (h,)
        ).fetchone() is not None
