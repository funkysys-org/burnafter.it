"""Gate-round regressions — every @reviewer finding becomes a test.

Findings addressed here stay fixed: a probe that found a bypass is a
regression test forever (squad doctrine).
"""

import io

import pytest

from app import claim, reap, now_utc

JPEG_MAGIC = b"\xff\xd8\xff" + b"\x00" * 29
MP3_ID3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 8
MP3_RAW = b"\xff\xfb\x90\x00" + b"\x00" * 12
M4A_MAGIC = b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 8


def _post_file(api, posttype, data, extra=None):
    form = {"maxhits": "1", "maxtime": "60"}
    if extra:
        form.update(extra)
    return api.post(
        f"/post/{posttype}",
        data={"data": (io.BytesIO(data), "f.bin"), **form},
        content_type="multipart/form-data",
    )


# ── Major #1: global MAX_CONTENT_LENGTH (parse-level DoS) ──────────────

def test_global_content_length_rejects_oversize_pre_read(api):
    """20MB body against the TEXT route: Flask must 413 BEFORE the
    handler runs (the reviewer's probe returned 200 pre-fix)."""
    big = b"x" * (20 * 1024 * 1024)
    r = api.post(
        "/post/text",
        data={"data": big.decode("latin1"), "maxhits": "1", "maxtime": "60"},
    )
    assert r.status_code == 413


def test_empty_text_shout_rejected(api):
    r = api.post(
        "/post/text", data={"data": "", "maxhits": "1", "maxtime": "60"}
    )
    assert r.status_code == 400


# ── Major #3: hardening headers on served content ──────────────────────

def test_served_content_has_hardening_headers(api):
    r = api.post(
        "/post/text",
        data={"data": "hard headers", "maxhits": "1", "maxtime": "60"},
    )
    served = api.get(r.get_json()["url"])
    assert served.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'none'" in served.headers["Content-Security-Policy"]


# ── Minor #7: hit_logs GC ───────────────────────────────────────────────

def test_reaper_prunes_old_hit_logs(db, make_shout):
    import datetime as dt

    from app import now_utc

    h = make_shout(max_hits=1)
    # claim() doesn't log — hit_logs come from the API's _log_hit;
    # create one directly, then age it past the 7-day prune window.
    db.execute("INSERT INTO hit_logs (shout_hash) VALUES (%s)", (h,))
    db.execute(
        "UPDATE hit_logs SET claimed_at = %s",
        (now_utc() - dt.timedelta(days=8),),
    )
    db.commit()
    _, _, pruned = reap(db)
    assert pruned >= 1
    assert db.execute("SELECT count(*) FROM hit_logs").fetchone()[0] == 0


# ── Minor #8: phone audio formats ──────────────────────────────────────

@pytest.mark.parametrize("payload,mime", [
    (MP3_ID3, "audio/mpeg"),
    (MP3_RAW, "audio/mpeg"),
    (M4A_MAGIC, "audio/mp4"),
])
def test_phone_audio_formats_accepted(api, payload, mime):
    r = _post_file(api, "audio", payload)
    assert r.status_code == 200
    served = api.get(r.get_json()["url"])
    assert served.status_code == 200
    assert served.mimetype == mime


# ── Minor #10: CLI rejects unknown args ─────────────────────────────────

def test_cleanup_cli_rejects_unknown_args(db, monkeypatch):
    import subprocess
    import sys

    monkeypatch.setenv("DATABASE_URL", db.info.dsn)
    proc = subprocess.run(
        [sys.executable, "-m", "app", "cleanup", "--extra"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 64
    assert "usage" in (proc.stderr + proc.stdout).lower()


# ── Major #4: quickstart env shape ──────────────────────────────────────

def test_env_example_does_not_ship_a_broken_default():
    """The .env.example must NOT pre-set DATABASE_URL (the compose
    fallback derives it; a CHANGE_ME literal breaks the quickstart)."""
    import os

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".env.example",
    )
    with open(path) as fh:
        lines = fh.read().splitlines()
    active = [l for l in lines if l.startswith("DATABASE_URL=")]
    assert active == [], "DATABASE_URL must ship commented-out only"
