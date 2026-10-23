"""RED slice 5 — Redis layer + health check.

Locked maintainer choices (§6.3): Redis = sessions + rate limiting,
ENABLED in the shipped compose, app must still boot WITHOUT it.
Burn/hit accounting NEVER touches Redis (all previous tests run
Redis-less and stay green — that IS the proof).
"""

import pytest

import redis as redis_lib

STRONG = "test-key-0123456789abcdef0123456789abcdef"
REDIS_URL = "redis://localhost:6379/15"


@pytest.fixture()
def api_rl(db):
    """App WITH Redis configured; tight limit for testability."""
    import importlib

    import app as app_mod

    app_mod = importlib.reload(app_mod)
    flask_app = app_mod.create_app(
        {
            "TESTING": True,
            "SECRET_KEY": STRONG,
            "DATABASE_URL": db.info.dsn,
            "REDIS_URL": REDIS_URL,
            "RATE_LIMIT": 3,
            "RATE_WINDOW": 60,
        }
    )
    r = redis_lib.from_url(REDIS_URL)
    r.flushdb()
    with flask_app.test_client() as client:
        yield client
    r.flushdb()


@pytest.fixture()
def api_noredis(db):
    """App WITHOUT Redis — in-process fallback, same semantics."""
    import importlib

    import app as app_mod

    app_mod = importlib.reload(app_mod)
    flask_app = app_mod.create_app(
        {
            "TESTING": True,
            "SECRET_KEY": STRONG,
            "DATABASE_URL": db.info.dsn,
            "RATE_LIMIT": 3,
            "RATE_WINDOW": 60,
        }
    )
    with flask_app.test_client() as client:
        yield client


def _post_text(api, i=0):
    return api.post(
        "/post/text",
        data={"data": f"rl {i}", "maxhits": "1", "maxtime": "60"},
    )


def test_rate_limit_enforced_with_redis(api_rl):
    for i in range(3):
        assert _post_text(api_rl, i).status_code == 200
    r = _post_text(api_rl, 99)
    assert r.status_code == 429


def test_rate_limit_in_process_fallback_without_redis(api_noredis):
    for i in range(3):
        assert _post_text(api_noredis, i).status_code == 200
    r = _post_text(api_noredis, 99)
    assert r.status_code == 429


def test_rate_limit_counter_lives_in_redis(api_rl):
    r = redis_lib.from_url(REDIS_URL)
    for i in range(2):
        assert _post_text(api_rl, i).status_code == 200
    keys = [k for k in r.keys("rl:*")]
    assert keys, "rate-limit counter must live in Redis when configured"


def test_health_reports_db_and_redis(api_rl):
    r = api_rl.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["db"] == "ok"
    assert body["redis"] == "ok"


def test_health_reports_redis_absent_without_url(api_noredis):
    r = api_noredis.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["db"] == "ok"
    assert body["redis"] == "absent"


def test_burn_still_atomic_with_redis_active(api_rl):
    """The invariant: Redis present must change NOTHING about burns."""
    r = _post_text(api_rl)
    url = r.get_json()["url"]
    assert api_rl.get(url).status_code == 200
    assert api_rl.get(url).status_code == 404


def test_session_backend_is_redis_when_configured(api_rl):
    """Sessions land in Redis when REDIS_URL is set (server-side)."""
    r = redis_lib.from_url(REDIS_URL)
    with api_rl.session_transaction() as sess:
        sess["probe"] = "in-redis"
    keys = [k for k in r.keys("session:*")]
    assert keys, "session data must be stored in Redis when configured"
