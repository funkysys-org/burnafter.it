"""burnafter.it v2-mono — application module (Scenario C).

Design: developers-team/repos/burnafter.it-analysis/40-v2-mono-design.md

Slice 1 — the atomic claim primitive. Every read of every content type
(text, photo, audio, video; chat in phase 2) goes through claim().

House rules (design §3/§4):
  * Timestamps are naive-UTC everywhere. The v2 aware/naive TypeError
    is the tombstone this convention exists to avoid.
  * Burn/hit accounting lives ONLY here (Postgres), never in Redis.
  * claim() losing (rowcount 0) self-disables the row: the two-phase
    GC phase 1 (is_active=FALSE + burned_at); the reaper (phase 2)
    is a later slice.
"""

import datetime
import secrets

import psycopg
import psycopg.sql
from flask import Flask, Response, jsonify, request

TEXT_CAP_BYTES = 10 * 1024          # design §6.4: text 10KB
MAXHITS_MIN, MAXHITS_MAX = 1, 100   # design §6.1
MAXTIME_MIN, MAXTIME_MAX = 1, 1440  # locked: 1 min .. 24 h


def now_utc() -> datetime.datetime:
    """Naive UTC 'now' — the ONLY time representation in v2-mono."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


# The ONE claim primitive. rowcount==1 -> this request won a view slot.
# Postgres serializes concurrent claims on the row: exactly max_hits
# winners are possible, across any number of app replicas.
_CLAIM_SQL = """
UPDATE shouts
   SET current_hits = current_hits + 1
 WHERE hash = %s
   AND is_active
   AND current_hits < max_hits
   AND expires_at > %s
"""

# Two-phase GC, phase 1: a failed claim against a still-active row
# self-disables it (burned by hits or by TTL — either way it is dead).
_FLIP_SQL = """
UPDATE shouts
   SET is_active = FALSE, burned_at = %s
 WHERE hash = %s
   AND is_active
"""

_SERVE_SQL = """
SELECT hash, storage_key, shout_type, max_hits, current_hits,
       is_active, created_at, expires_at
  FROM shouts
 WHERE hash = %s
   AND is_active
   AND expires_at > %s
"""


def claim(conn, shout_hash: str) -> bool:
    """Atomically consume one of the shout's max_hits view slots.

    True  -> this request may serve the content.
    False -> burned (max hits), expired, inactive, or nonexistent.

    The connection's transaction is committed here: the claim is the
    unit of work; hit_logs are written separately AFTER a successful
    claim (a logging failure must never un-burn content).
    """
    now = now_utc()
    with conn.cursor() as cur:
        cur.execute(_CLAIM_SQL, (shout_hash, now))
        if cur.rowcount == 1:
            conn.commit()
            return True
    with conn.cursor() as cur:
        cur.execute(_FLIP_SQL, (now, shout_hash))
    conn.commit()
    return False


def get_shout(conn, shout_hash: str):
    """Serve-side metadata lookup: only active, unexpired shouts.

    Returns a dict (or None). The capability decision is claim()'s;
    this only reads what a winner may be served.
    """
    with conn.cursor() as cur:
        cur.execute(_SERVE_SQL, (shout_hash, now_utc()))
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d.name for d in cur.description]
        return dict(zip(cols, row))


# ─── Flask application factory (slice 2) ──────────────────────────────────────

_INSERT_SHOUT_SQL = """
INSERT INTO shouts (hash, storage_key, shout_type, max_hits, expires_at)
VALUES (%s, %s, %s, %s, %s)
"""

_INSERT_BLOB_SQL = """
INSERT INTO blobs (storage_key, mime_type, size_bytes, content)
VALUES (%s, %s, %s, %s)
"""

_SERVE_TEXT_SQL = """
SELECT b.content, b.mime_type
  FROM blobs b
  JOIN shouts s ON s.storage_key = b.storage_key
 WHERE s.hash = %s
"""

_LOG_HIT_SQL = """
INSERT INTO hit_logs (shout_hash) VALUES (%s)
"""


def _parse_limits(form):
    """Validate maxhits/maxtime from the form — server-side, never trusted.

    Returns (maxhits, maxtime) or raises ValueError.
    """
    try:
        maxhits = int(form["maxhits"])
        maxtime = int(form["maxtime"])
    except (KeyError, ValueError):
        raise ValueError("maxhits and maxtime must be integers") from None
    if not MAXHITS_MIN <= maxhits <= MAXHITS_MAX:
        raise ValueError(f"maxhits must be {MAXHITS_MIN}..{MAXHITS_MAX}")
    if not MAXTIME_MIN <= maxtime <= MAXTIME_MAX:
        raise ValueError(f"maxtime must be {MAXTIME_MIN}..{MAXTIME_MAX} minutes")
    return maxhits, maxtime


def _log_hit(conn, shout_hash: str) -> None:
    """Best-effort hit log — a failure here must never un-burn content."""
    try:
        with conn.cursor() as cur:
            cur.execute(_LOG_HIT_SQL, (shout_hash,))
        conn.commit()
    except Exception:  # noqa: BLE001 — logging must not break serving
        conn.rollback()


def _burned_response():
    # v1's personality, kept (design §1: funky 404s).
    return Response(
        "Burned! This shout expired or was already seen.\n", status=404
    )


def create_app(config_overrides=None):
    """Application factory — stateless; all state in Postgres/Redis."""
    app = Flask(__name__)
    app.config.update(
        DATABASE_URL=None,  # must be provided (env or override)
        SECRET_KEY=None,
    )
    if config_overrides:
        app.config.update(config_overrides)
    import os

    if not app.config["DATABASE_URL"]:
        app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL")
    if not app.config["DATABASE_URL"]:
        raise RuntimeError(
            "DATABASE_URL is required (Postgres holds all state in v2-mono)"
        )

    def _connect():
        return psycopg.connect(app.config["DATABASE_URL"])

    @app.post("/post/text")
    def post_text():
        try:
            maxhits, maxtime = _parse_limits(request.form)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

        data = request.form.get("data", "")
        encoded = data.encode("utf-8")
        if len(encoded) > TEXT_CAP_BYTES:
            return jsonify(error="text exceeds the 10KB cap"), 413

        shout_hash = "h" + secrets.token_hex(16)
        storage_key = "s" + secrets.token_hex(16)
        expires_at = now_utc() + datetime.timedelta(minutes=maxtime)

        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _INSERT_SHOUT_SQL,
                    (shout_hash, storage_key, "text", maxhits, expires_at),
                )
                cur.execute(
                    _INSERT_BLOB_SQL,
                    (storage_key, "text/plain", len(encoded), encoded),
                )
            conn.commit()
        except Exception:  # noqa: BLE001 — fail loud to the log, 500-free UX
            conn.rollback()
            app.logger.exception("create text shout failed")
            return jsonify(error="could not store the shout"), 500
        finally:
            conn.close()

        return jsonify(url=f"/stream_any/text/{shout_hash}")

    @app.get("/stream_any/text/<shout_hash>")
    def stream_text(shout_hash):
        conn = _connect()
        try:
            if not claim(conn, shout_hash):
                return _burned_response()

            with conn.cursor() as cur:
                cur.execute(_SERVE_TEXT_SQL, (shout_hash,))
                row = cur.fetchone()
                if row is None:
                    app.logger.error(
                        "claimed shout %r has no blob row", shout_hash
                    )
                    return jsonify(error="storage error"), 500
                content, mime = row

            _log_hit(conn, shout_hash)
            return Response(bytes(content), mimetype=mime)
        finally:
            conn.close()

    return app
