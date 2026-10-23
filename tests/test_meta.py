"""RED — /meta endpoint: non-consuming shout metadata for the reader gate.

Spec §6: the SPA feature-detects GET /meta/<type>/<hash> (800ms timeout);
any failure → link-only mode. For the gate copy "Opening burns 1 of N
views · tape expires in h:mm" the endpoint must return views_left and
expires_at WITHOUT claiming. Burned/expired/never-existed must be
indistinguishable (never leak which).
"""

import datetime

import pytest

from app import now_utc


@pytest.fixture()
def shout_url(db):
    """Create a real text shout via the API; return its hash."""
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-0123456789abcdef0123456789abcdef",
            "DATABASE_URL": db.info.dsn,
        }
    )
    with app.test_client() as c:
        r = c.post(
            "/post/text",
            data={"data": "meta probe", "maxhits": "3", "maxtime": "120"},
        )
        url = r.get_json()["url"]
    return url.rsplit("/", 1)[1]  # hash


def test_meta_returns_views_left_and_expiry(db, shout_url):
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-0123456789abcdef0123456789abcdef",
            "DATABASE_URL": db.info.dsn,
        }
    )
    with app.test_client() as c:
        r = c.get(f"/meta/text/{shout_url}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["views_left"] == 3
        assert body["type"] == "text"
        assert "expires_at" in body  # ISO string


def test_meta_does_not_consume(db, shout_url):
    """THE invariant: reading meta must not touch current_hits or logs."""
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-0123456789abcdef0123456789abcdef",
            "DATABASE_URL": db.info.dsn,
        }
    )
    with app.test_client() as c:
        for _ in range(3):  # hammer it
            assert c.get(f"/meta/text/{shout_url}").status_code == 200
    row = db.execute(
        "SELECT current_hits FROM shouts WHERE hash = %s", (shout_url,)
    ).fetchone()
    assert row[0] == 0  # untouched
    assert db.execute("SELECT count(*) FROM hit_logs").fetchone()[0] == 0


def test_meta_burned_is_uniform_404(db):
    """Burned, expired, and nonexistent must look identical — no leak."""
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-0123456789abcdef0123456789abcdef",
            "DATABASE_URL": db.info.dsn,
        }
    )
    with app.test_client() as c:
        # a REAL shout via the API (has a blob), maxhits=1
        r = c.post(
            "/post/text", data={"data": "x", "maxhits": "1", "maxtime": "60"}
        )
        burned = r.get_json()["url"].rsplit("/", 1)[1]
        assert c.get(f"/stream_any/text/{burned}").status_code == 200
        assert c.get(f"/stream_any/text/{burned}").status_code == 404
        r2 = c.post(
            "/post/text", data={"data": "x", "maxhits": "1", "maxtime": "60"}
        )
        live = r2.get_json()["url"].rsplit("/", 1)[1]
        db.execute("UPDATE shouts SET expires_at = %s WHERE hash = %s",
                   (now_utc() - datetime.timedelta(minutes=5), live))
        db.commit()
        for h in (burned, live, "h" + "0" * 32):
            r = c.get(f"/meta/text/{h}")
            assert r.status_code == 404
            assert set(r.get_json().keys()) == {"error"}
