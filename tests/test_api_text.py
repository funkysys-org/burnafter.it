"""RED slice 2 — SEC API over the claim primitive (text first).

Vertical bullet: create a text shout -> claim-serve it -> burn it.
Every assertion maps to a locked design rule (40-v2-mono-design.md).
"""

LONG_TEXT = "x" * (10 * 1024 + 1)  # over the 10KB text cap


def test_create_text_shout_returns_secret_url(api):
    r = api.post(
        "/post/text",
        data={"data": "hello burn", "maxhits": "2", "maxtime": "60"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["url"].startswith("/stream_any/text/")
    h = body["url"].rsplit("/", 1)[1]
    assert 20 <= len(h) <= 64


def test_create_validates_maxhits_range(api):
    r = api.post(
        "/post/text", data={"data": "hi", "maxhits": "0", "maxtime": "60"}
    )
    assert r.status_code == 400
    r = api.post(
        "/post/text", data={"data": "hi", "maxhits": "101", "maxtime": "60"}
    )
    assert r.status_code == 400


def test_create_validates_maxtime_range(api):
    # locked: 1 min .. 24h (1440 min)
    for bad in ("0", "1441"):
        r = api.post(
            "/post/text", data={"data": "hi", "maxhits": "1", "maxtime": bad}
        )
        assert r.status_code == 400


def test_create_rejects_oversized_text(api):
    r = api.post(
        "/post/text",
        data={"data": LONG_TEXT, "maxhits": "1", "maxtime": "60"},
    )
    assert r.status_code == 413


def test_claim_serve_then_burn_cycle(api):
    r = api.post(
        "/post/text",
        data={"data": "secret words", "maxhits": "1", "maxtime": "60"},
    )
    url = r.get_json()["url"]

    first = api.get(url)
    assert first.status_code == 200
    assert first.get_data(as_text=True) == "secret words"

    second = api.get(url)
    assert second.status_code == 404
    assert "Burned" in second.get_data(as_text=True)


def test_expired_shout_is_burned(api, make_shout):
    h = make_shout(expired=True)
    r = api.get(f"/stream_any/text/{h}")
    assert r.status_code == 404


def test_hit_log_written_only_after_successful_claim(api, db):
    r = api.post(
        "/post/text",
        data={"data": "logged", "maxhits": "1", "maxtime": "60"},
    )
    url = r.get_json()["url"]
    api.get(url)          # winning claim -> logged
    api.get(url)          # burned claim -> NOT logged
    n = db.execute(
        "SELECT count(*) FROM hit_logs"
    ).fetchone()[0]
    assert n == 1


def test_content_isolation_via_storage_key(api, db):
    """Capability hash != storage key: the blob row must NOT be
    addressable by the URL hash (decoupling rule)."""
    r = api.post(
        "/post/text",
        data={"data": "decoupled", "maxhits": "1", "maxtime": "60"},
    )
    h = r.get_json()["url"].rsplit("/", 1)[1]
    row = db.execute(
        "SELECT storage_key FROM shouts WHERE hash = %s", (h,)
    ).fetchone()
    assert row is not None and row[0] != h
