"""RED — gate round for Radio Puppa Live: the 3 majors + minor coverage.

#1 anonymous exhaustion: /live must rate-limit per IP; the ring must be
   LTRIM'd to a chunk budget; poll must return a bounded window.
#2 heartbeat death must be REAL: hb TTL = HEARTBEAT_S (create grace
   bounded), reap wired into the CLI cycle, reaper works via TTL lapse
   (no manual key deletes in tests).
#3 seats must expire: join returns a seat id with TTL, renewed by poll
   participation; expired seats free capacity.
minors: source token stored HASHED; /say throttled; webm sniffed.
"""

import hashlib
import io
import subprocess
import sys
import time

import pytest

from live import CREATE_GRACE_S, HEARTBEAT_S

STRONG = "test-key-0123456789abcdef0123456789abcdef"
REDIS15 = "redis://localhost:6379/15"


def _app(live_db, **over):
    from app import create_app

    cfg = {
        "TESTING": True,
        "SECRET_KEY": STRONG,
        "DATABASE_URL": live_db.info.dsn,
        **over,
    }
    app = create_app(cfg)
    app.config["REDIS_URL"] = REDIS15
    return app


def _create(c, **kw):
    return c.post("/live", json={"maxhours": 1, "cap": None, **kw})


# ── major #1a: /live is rate-limited per IP ─────────────────────────────

def test_live_create_is_rate_limited(live_db):
    app = _app(live_db, RATE_LIMIT=2)
    with app.test_client() as c:
        assert _create(c).status_code == 200
        assert _create(c).status_code == 200
        assert _create(c).status_code == 429


# ── major #1b/c: ring budget + poll window ──────────────────────────────

def test_ring_is_ltrimmed_to_budget(live_db):
    import redis as redis_lib

    app = _app(live_db, RING_MAX_CHUNKS=3)
    with app.test_client() as c:
        b = _create(c).get_json()
        h, tok = b["session_hash"], b["token"]
        for i in range(5):
            r = c.post(
                f"/live/{h}/seg?token={tok}",
                data={"data": (io.BytesIO(f"CHUNK{i}".encode() + b"\x00" * 50), "c.webm")},
                content_type="multipart/form-data",
            )
            assert r.status_code == 200
        rr = redis_lib.from_url(REDIS15)
        assert int(rr.llen(f"live:{h}")) == 3  # bounded, oldest dropped


def test_poll_returns_bounded_window(live_db):
    app = _app(live_db, RING_MAX_CHUNKS=600, POLL_MAX_SEGS=2)
    with app.test_client() as c:
        b = _create(c).get_json()
        h, tok = b["session_hash"], b["token"]
        for i in range(5):
            c.post(
                f"/live/{h}/seg?token={tok}",
                data={"data": (io.BytesIO(f"CHUNK{i}".encode() + b"\x00" * 50), "c.webm")},
                content_type="multipart/form-data",
            )
        late = c.get(f"/live/{h}/poll?after=0")
        j = late.get_json()
        assert j["seq"] == 5
        assert len(j["segments"]) == 2  # late joiner: last window only


# ── major #2: heartbeat TTL semantics + CLI wiring ───────────────────────

def test_hb_ttl_is_bounded_and_cli_reaps_after_lapse(live_db, monkeypatch):
    import redis as redis_lib

    app = _app(live_db)
    with app.test_client() as c:
        b = _create(c).get_json()
        h, tok = b["session_hash"], b["token"]
        rr = redis_lib.from_url(REDIS15)
        # create grace is bounded (mic permission), push renews to 30s
        assert 0 < rr.ttl(f"live-hb:{h}") <= CREATE_GRACE_S
        c.post(
            f"/live/{h}/seg?token={tok}",
            data={"data": (io.BytesIO(b"\x1aE\xdf\xa3" + b"\x00" * 40), "c.webm")},
            content_type="multipart/form-data",
        )
        assert 0 < rr.ttl(f"live-hb:{h}") <= HEARTBEAT_S

        # TTL lapse (no manual delete) + the CLI cycle reaps it
        rr.expire(f"live-hb:{h}", 1)
        time.sleep(1.2)

        monkeypatch.setenv("DATABASE_URL", live_db.info.dsn)
        monkeypatch.setenv("SECRET_KEY", STRONG)
        monkeypatch.setenv("REDIS_URL", REDIS15)
        proc = subprocess.run(
            [sys.executable, "-m", "app", "cleanup"],
            capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0
        assert "live session" in proc.stdout.lower()

        assert c.get(f"/live/{h}/meta").status_code == 404  # uniform burned


# ── major #3: seats expire and free capacity ─────────────────────────────

def test_seats_expire_and_free_capacity(live_db):
    import redis as redis_lib

    app = _app(live_db, SEAT_TTL_S=35)
    with app.test_client() as c:
        b = _create(c, cap=1).get_json()
        h = b["session_hash"]

        first = c.get(f"/live/{h}/join")
        assert first.status_code == 200
        seat = first.get_json()["seat"]
        assert isinstance(seat, str) and seat

        assert c.get(f"/live/{h}/join").status_code == 409  # cap=1 held

        # seat expires by TTL -> capacity freed
        rr = redis_lib.from_url(REDIS15)
        rr.expire(f"seat:{h}:{seat}", 1)
        time.sleep(1.2)
        again = c.get(f"/live/{h}/join")
        assert again.status_code == 200


def test_poll_renews_seat(live_db):
    import redis as redis_lib

    app = _app(live_db)
    with app.test_client() as c:
        b = _create(c).get_json()
        h = b["session_hash"]
        tok = b["token"]
        c.post(
            f"/live/{h}/seg?token={tok}",
            data={"data": (io.BytesIO(b"\x1aE\xdf\xa3" + b"\x00" * 40), "c.webm")},
            content_type="multipart/form-data",
        )
        seat = c.get(f"/live/{h}/join").get_json()["seat"]
        rr = redis_lib.from_url(REDIS15)
        rr.expire(f"seat:{h}:{seat}", 3)  # about to lapse
        r2 = c.get(f"/live/{h}/poll?after=0&seat={seat}")
        assert r2.status_code == 200
        assert rr.ttl(f"seat:{h}:{seat}") > 10  # renewed by participation


# ── re-gate finding: END in the no-Redis degraded mode ──────────────────

def test_end_works_without_redis(live_db, monkeypatch):
    """The degraded path (no REDIS_URL) is a real configuration — END
    must 200, not 500 (the seat-sweep once sat outside the guard)."""
    app = _app(live_db)
    app.config["REDIS_URL"] = None  # degraded: no Redis at all
    with app.test_client() as c:
        b = _create(c).get_json()
        h, tok = b["session_hash"], b["token"]
        assert c.get(f"/live/{h}/join").status_code == 200  # degraded join
        r = c.post(f"/live/{h}/end", query_string={"token": tok})
        assert r.status_code == 200, r.get_data(as_text=True)
        assert c.get(f"/live/{h}/meta").status_code == 404  # uniform burned


# ── minor #4: source token stored hashed ────────────────────────────────

def test_source_token_stored_hashed(live_db):
    app = _app(live_db)
    with app.test_client() as c:
        b = _create(c).get_json()
        row = live_db.execute(
            "SELECT source_token FROM live_sessions WHERE hash = %s",
            (b["session_hash"],),
        ).fetchone()
        stored = row[0]
        assert stored != b["token"]  # raw token never in PG
        assert stored == hashlib.sha256(b["token"].encode()).hexdigest()


# ── minor #7: /say throttled ─────────────────────────────────────────────

def test_say_is_throttled(live_db):
    app = _app(live_db, RATE_LIMIT=5)
    with app.test_client() as c:
        b = _create(c).get_json()
        h = b["session_hash"]
        codes = [
            c.post(
                f"/live/{h}/say",
                json={"nickname": "N", "body": f"m{i}"},
            ).status_code
            for i in range(6)
        ]
        assert codes[:5] == [200] * 5
        assert codes[5] == 429


# ── minor #6: webm sniffed end-to-end ────────────────────────────────────

def test_webm_sniffed_and_accepted_everywhere(live_db):
    webm = b"\x1aE\xdf\xa3" + b"\x00" * 40
    app = _app(live_db)
    with app.test_client() as c:
        # /post/audio accepts webm now
        r = c.post(
            "/post/audio",
            data={
                "data": (io.BytesIO(webm), "voice.webm"),
                "maxhits": "1",
                "maxtime": "60",
            },
            content_type="multipart/form-data",
        )
        assert r.status_code == 200
        served = c.get("/stream_any/audio/" + r.get_json()["url"].rsplit("/", 1)[1])
        assert served.mimetype == "audio/webm"

        # saved live session keeps the honest webm label
        b = _create(c).get_json()
        h, tok = b["session_hash"], b["token"]
        c.post(
            f"/live/{h}/seg?token={tok}",
            data={"data": (io.BytesIO(webm), "c.webm")},
            content_type="multipart/form-data",
        )
        # contract (UI order): END first, then SAVE
        c.post(f"/live/{h}/end", query_string={"token": tok})
        saved = c.post(
            f"/live/{h}/save?token={tok}",
            json={"maxhits": 3, "maxtime": 60},
        ).get_json()["url"]
        raw = saved.replace("/read/", "/stream_any/")
        s2 = c.get(raw)
        assert s2.status_code == 200
        assert s2.mimetype == "audio/webm"
