"""SCATOLA A OROLOGERIA — timed-release shouts and chat rooms.

Maintainer-locked semantics (2026-11-17):
  * applies to SHOUTS (text/photo/audio/video) and ESC CHAT rooms only —
    radio/call are excluded on purpose
  * link+QR exist immediately (shareable); the box is SEALED until open_at
  * sealed is a VISIBLE state: anyone with the link sees the countdown —
    the anticipation is the feature (locked: "countdown visibile ovviamente")
  * looking at the sealed box consumes NOTHING: claim starts at open_at,
    fuse (maxtime/maxhours) counts from open_at, not from creation
  * premature claims: HTTP 425 Too Early + opens_at (locked: "supercazzola")
  * no open_at sent -> open_at = now() (normal shout, zero behavior change)
  * open_at capped at 7 days in the future (beyond that = a storage
    service, which this is not)
"""

import datetime
import io

NAIVE = lambda dt: dt.replace(tzinfo=None)  # noqa: E731
UTCNOW = lambda: NAIVE(datetime.datetime.now(datetime.timezone.utc))  # noqa: E731


def _in(minutes):
    return (UTCNOW() + datetime.timedelta(minutes=minutes)).isoformat()


def _create_room(live_api):
    """Local copy of the ESC room helper (no cross-test imports)."""
    r = live_api.post("/live", json={"kind": "chat", "maxhours": 2})
    assert r.status_code == 200, r.get_data(as_text=True)
    return r


# ── shouts ────────────────────────────────────────────────────────────────────


def _post_text(api, **extra):
    return api.post(
        "/post/text",
        data={"data": "sealed box contents", "maxhits": "1", "maxtime": "60", **extra},
        content_type="multipart/form-data",
    )


def test_sealed_text_meta_shows_countdown_and_claim_is_425(api, db):
    r = _post_text(api, open_at=_in(60))
    assert r.status_code == 200, r.get_data(as_text=True)
    h = r.get_json()["url"].rsplit("/", 1)[1]

    m = api.get(f"/meta/text/{h}")
    assert m.status_code == 200
    j = m.get_json()
    assert j["sealed"] is True
    assert "opens_at" in j and j["opens_at"].endswith("Z")

    # premature claim: 425 Too Early, with the honest opens_at in the body
    c = api.get(f"/stream_any/text/{h}")
    assert c.status_code == 425
    assert c.get_json()["opens_at"].endswith("Z")

    # and the peek consumed NOTHING: still sealed, views intact
    m2 = api.get(f"/meta/text/{h}")
    assert m2.get_json()["sealed"] is True
    assert m2.get_json()["views_left"] == 1


def test_sealed_shout_opens_and_behaves_normally(api, db):
    r = _post_text(api, open_at=_in(60))
    h = r.get_json()["url"].rsplit("/", 1)[1]

    # deterministic time travel: open the box in the DB
    db.execute(
        "UPDATE shouts SET open_at = %s WHERE hash = %s",
        (UTCNOW() - datetime.timedelta(seconds=1), h),
    )
    db.commit()

    m = api.get(f"/meta/text/{h}")
    assert m.get_json()["sealed"] is False
    assert m.get_json()["views_left"] == 1

    c = api.get(f"/stream_any/text/{h}")
    assert c.status_code == 200
    assert c.get_data() == b"sealed box contents"

    # maxhits=1: second claim burns
    c2 = api.get(f"/stream_any/text/{h}")
    assert c2.status_code == 404


def test_early_claims_never_flip_a_sealed_row(api, db):
    """The claim primitive's flip path must not burn a sealed box."""
    r = _post_text(api, open_at=_in(60))
    h = r.get_json()["url"].rsplit("/", 1)[1]

    for _ in range(3):
        assert api.get(f"/stream_any/text/{h}").status_code == 425

    # still active, not flipped
    assert db.execute(
        "SELECT is_active FROM shouts WHERE hash = %s", (h,)
    ).fetchone()[0] is True
    db.commit()

    # open it — the view slot is still there
    db.execute(
        "UPDATE shouts SET open_at = %s WHERE hash = %s",
        (UTCNOW() - datetime.timedelta(seconds=1), h),
    )
    db.commit()
    assert api.get(f"/stream_any/text/{h}").status_code == 200


def test_fuse_counts_from_open_not_creation(api, db):
    r = _post_text(api, open_at=_in(10))  # 10 min seal, 60 min fuse
    h = r.get_json()["url"].rsplit("/", 1)[1]
    open_at, expires_at = db.execute(
        "SELECT open_at, expires_at FROM shouts WHERE hash = %s", (h,)
    ).fetchone()
    db.commit()
    # fuse starts when the box OPENS, not when it was made
    assert expires_at - open_at == datetime.timedelta(minutes=60)


def test_open_at_validation(api, db):
    # too far out (cap = 7 days)
    r = _post_text(api, open_at=_in(8 * 24 * 60))
    assert r.status_code == 400
    assert "7" in r.get_json()["error"]
    # in the past
    r = _post_text(api, open_at=(UTCNOW() - datetime.timedelta(minutes=1)).isoformat())
    assert r.status_code == 400
    # malformed
    r = _post_text(api, open_at="not-a-date")
    assert r.status_code == 400


def test_no_open_at_is_now_and_zero_regression(api, db):
    r = _post_text(api)
    assert r.status_code == 200
    h = r.get_json()["url"].rsplit("/", 1)[1]

    m = api.get(f"/meta/text/{h}")
    assert m.get_json()["sealed"] is False

    # claimable immediately — the pre-feature behavior, byte for byte
    c = api.get(f"/stream_any/text/{h}")
    assert c.status_code == 200
    assert c.get_data() == b"sealed box contents"


def test_sealed_photo_425_then_serves(api, db):
    jpg = b"\xff\xd8\xff" + b"\x00" * 64
    r = api.post(
        "/post/photo",
        data={
            "data": (io.BytesIO(jpg), "box.jpg"),
            "maxhits": "1",
            "maxtime": "30",
            "open_at": _in(60),
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    h = r.get_json()["url"].rsplit("/", 1)[1]

    assert api.get(f"/stream_any/photo/{h}").status_code == 425
    db.execute(
        "UPDATE shouts SET open_at = %s WHERE hash = %s",
        (UTCNOW() - datetime.timedelta(seconds=1), h),
    )
    db.commit()
    c = api.get(f"/stream_any/photo/{h}")
    assert c.status_code == 200
    assert c.mimetype == "image/jpeg"


# ── ESC chat rooms ───────────────────────────────────────────────────────────


def _create_room_with_open_at(live_api, open_at):
    return live_api.post(
        "/live",
        json={"kind": "chat", "maxhours": 2, "open_at": open_at},
    )


def test_sealed_room_meta_say_chat_gated(live_api, live_db):
    r = _create_room_with_open_at(live_api, _in(120))
    assert r.status_code == 200, r.get_data(as_text=True)
    h = r.get_json()["session_hash"]

    m = live_api.get(f"/live/{h}/meta")
    assert m.status_code == 200
    j = m.get_json()
    assert j["sealed"] is True
    assert j["opens_at"].endswith("Z")

    s = live_api.post(f"/live/{h}/say", json={"nickname": "x", "body": "early bird"})
    assert s.status_code == 425
    assert s.get_json()["opens_at"].endswith("Z")

    c = live_api.get(f"/live/{h}/chat?after=0")
    assert c.status_code == 425

    # open the room
    live_db.execute(
        "UPDATE live_sessions SET open_at = %s WHERE hash = %s",
        (UTCNOW() - datetime.timedelta(seconds=1), h),
    )
    live_db.commit()
    assert live_api.post(f"/live/{h}/say", json={"nickname": "x", "body": "hello"}).status_code == 200
    c = live_api.get(f"/live/{h}/chat?after=0")
    assert c.status_code == 200
    assert len(c.get_json()["messages"]) == 1


def test_room_fuse_counts_from_open(live_api, live_db):
    r = _create_room_with_open_at(live_api, _in(60))  # opens in 1h, fuse 2h
    h = r.get_json()["session_hash"]
    open_at, expires_at = live_db.execute(
        "SELECT open_at, expires_at FROM live_sessions WHERE hash = %s", (h,)
    ).fetchone()
    live_db.commit()
    assert expires_at - open_at == datetime.timedelta(hours=2)


def test_room_without_open_at_and_live_call_exclude_sealing(live_api, live_db):
    # plain room: immediate
    r = _create_room(live_api)
    assert r.status_code == 200
    h = r.get_json()["session_hash"]
    m = live_api.get(f"/live/{h}/meta")
    assert m.get_json().get("sealed") is False
    assert (
        live_api.post(f"/live/{h}/say", json={"nickname": "x", "body": "now"}).status_code == 200
    )

    # radio/call: open_at is IGNORED — no sealed state ever
    for kind in ("live", "call"):
        r = live_api.post(
            "/live", json={"kind": kind, "maxhours": 1, "open_at": _in(120)}
        )
        assert r.status_code == 200
        h = r.get_json()["session_hash"]
        m = live_api.get(f"/live/{h}/meta")
        j = m.get_json()
        assert j.get("sealed", False) is False, f"{kind} must never be sealed"


def test_room_open_at_validation(live_api):
    r = _create_room_with_open_at(live_api, _in(8 * 24 * 60))
    assert r.status_code == 400
    r = _create_room_with_open_at(live_api, (UTCNOW() - datetime.timedelta(minutes=1)).isoformat())
    assert r.status_code == 400
    r = _create_room_with_open_at(live_api, "garbage")
    assert r.status_code == 400


def test_sealed_shout_survives_reaper(api, db):
    """A sealed box is not expired — the reaper must not flip it."""
    r = _post_text(api, open_at=_in(60 * 24 * 3))  # opens in 3 days
    h = r.get_json()["url"].rsplit("/", 1)[1]

    import app as app_mod

    app_mod.reap(db)  # the `db` fixture is a live psycopg connection

    assert db.execute(
        "SELECT is_active FROM shouts WHERE hash = %s", (h,)
    ).fetchone()[0] is True
    db.commit()
    assert api.get(f"/stream_any/text/{h}").status_code == 425
