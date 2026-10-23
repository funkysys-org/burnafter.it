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
import io
import secrets
import threading
import time

import psycopg
import psycopg.sql
import qrcode
from flask import Flask, Response, jsonify, render_template, request

TEXT_CAP_BYTES = 10 * 1024          # design §6.4: text 10KB
MAXHITS_MIN, MAXHITS_MAX = 1, 100   # design §6.1
MAXTIME_MIN, MAXTIME_MAX = 1, 1440  # locked: 1 min .. 24 h

# Per-type upload caps + magic-byte allowlist (design §4.3):
# the server derives mime from the DECLARED type + actual bytes;
# client filenames never touch storage.
MEDIA_SPECS = {
    "photo": (5 * 1024 * 1024, ("image/jpeg", "image/png")),
    "audio": (25 * 1024 * 1024, ("audio/wav", "audio/mpeg", "audio/mp4")),
    "video": (50 * 1024 * 1024, ("video/mp4",)),
}
ALLOWED_MIMES = {m for _, mimes in MEDIA_SPECS.values() for m in mimes}


def _sniff_mime(data: bytes) -> str | None:
    """Magic-byte allowlist — no content-type trust, no blacklist regex."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"  # ID3-tagged or raw-frame MP3 (gate minor #8)
    if data[4:8] == b"ftyp":
        brand = data[8:12]
        return "audio/mp4" if brand in (b"M4A ", b"M4B ") else "video/mp4"
    return None


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


# Two-phase GC, phase 2 — the reaper:
#   1. flip: expired-but-active rows become inactive (burned_at set)
#   2. delete: inactive rows past the grace period are physically
#      removed; blobs go with them via ON DELETE CASCADE
#   3. prune: hit_logs older than 7 days (gate minor #7 — no FK to
#      shouts, so the reaper owns their GC too)
_REAP_FLIP_SQL = """
UPDATE shouts
   SET is_active = FALSE,
       burned_at = COALESCE(burned_at, %s)
 WHERE is_active
   AND expires_at <= %s
"""

_REAP_DELETE_SQL = """
DELETE FROM shouts
 WHERE NOT is_active
   AND burned_at <= %s
"""

_REAP_PRUNE_LOGS_SQL = """
DELETE FROM hit_logs
 WHERE claimed_at <= %s
"""


def reap(conn, grace: datetime.timedelta = datetime.timedelta(hours=1)):
    """Sweep pass. Returns (flipped, deleted, logs_pruned). Never
    touches live rows."""
    now = now_utc()
    with conn.cursor() as cur:
        cur.execute(_REAP_FLIP_SQL, (now, now))
        flipped = cur.rowcount
        cutoff = now - grace
        cur.execute(_REAP_DELETE_SQL, (cutoff,))
        deleted = cur.rowcount
        log_cutoff = now - datetime.timedelta(days=7)
        cur.execute(_REAP_PRUNE_LOGS_SQL, (log_cutoff,))
        pruned = cur.rowcount
    conn.commit()
    return flipped, deleted, pruned


# ─── Rate limiting: Redis when configured, in-process fallback if not ─────────
# Burns/hits NEVER touch this layer — it only throttles the create path.

_RL_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


class RateLimiter:
    """Per-IP create throttle. Same semantics with or without Redis."""

    def __init__(self, app):
        self.limit = int(app.config.get("RATE_LIMIT") or 10)
        self.window = int(app.config.get("RATE_WINDOW") or 60)
        url = app.config.get("REDIS_URL")
        self.redis = None
        self._script = None
        if url:
            try:
                import redis as redis_lib

                client = redis_lib.from_url(url)
                client.ping()
                self.redis = client
                self._script = client.register_script(_RL_SCRIPT)
                app.logger.info("rate limiting: Redis-backed")
            except Exception:  # noqa: BLE001 — degrade, never block boot
                app.logger.warning(
                    "Redis unreachable (%s) — in-process rate limit fallback",
                    url,
                )
                self.redis = None
        else:
            app.logger.info("rate limiting: in-process (no REDIS_URL)")
        self._local = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """True -> under the limit for this window; False -> 429."""
        if self.redis is not None:
            n = self._script(keys=[f"rl:{key}"], args=[self.window])
            return int(n) <= self.limit
        now = time.time()
        with self._lock:
            bucket = self._local.get(key)
            if bucket and now - bucket[0] < self.window:
                bucket[1] += 1
                return bucket[1] <= self.limit
            self._local[key] = [now, 1]
            return True


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
    # 12-factor: every knob comes from the environment unless an
    # explicit override is passed (tests do that).
    import os

    app.config.update(
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        REDIS_URL=os.environ.get("REDIS_URL"),
        RATE_LIMIT=os.environ.get("RATE_LIMIT", 10),
        RATE_WINDOW=os.environ.get("RATE_WINDOW", 60),
        # Design §6.4: global ceiling — Flask rejects oversized bodies
        # PRE-READ (gate major #1); per-type caps then narrow further.
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        # Gate major #5: opt-in — only behind a trusted proxy does the
        # app key rate limits on X-Forwarded-For instead of proxy IP.
        TRUSTED_PROXY=os.environ.get("TRUSTED_PROXY", "0"),
    )
    if config_overrides:
        app.config.update(config_overrides)

    if not app.config["DATABASE_URL"]:
        raise RuntimeError(
            "DATABASE_URL is required (Postgres holds all state in v2-mono)"
        )

    # Boot-guard (design §4.5/6a): the per-process SECRET_KEY of v1 is
    # the tombstone — fail loud on missing/weak/default session keys.
    secret = app.config.get("SECRET_KEY")
    known_weak = {"change-me-in-production", "change-me-in-prod", "test-key"}
    if not secret or secret in known_weak or len(str(secret)) < 32:
        raise RuntimeError(
            "SECRET_KEY is missing, too short (<32 chars), or a known "
            "default — provide a strong key via the environment; "
            "v2-mono refuses to boot on weak session keys."
        )

    # Redis sessions (§6.3): server-side sessions when REDIS_URL is set;
    # plain cookie sessions otherwise — either way the app boots.
    if app.config.get("REDIS_URL"):
        try:
            import redis as redis_lib

            from flask_session.redis import RedisSessionInterface

            app.session_interface = RedisSessionInterface(
                app=app,
                client=redis_lib.from_url(app.config["REDIS_URL"]),
                key_prefix="session:",
            )
            app.config["SESSION_REDIS_ACTIVE"] = True
        except Exception:  # noqa: BLE001 — sessions must not block boot
            app.logger.warning(
                "Redis session backend unavailable — cookie sessions"
            )

    if str(app.config.get("TRUSTED_PROXY", "0")) == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix

        # Keying stays on remote_addr — ProxyFix rewrites it from the
        # trusted proxy's X-Forwarded-For (gate major #5).
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    rate_limiter = RateLimiter(app)
    app.extensions["rate_limiter"] = rate_limiter

    def _connect():
        return psycopg.connect(app.config["DATABASE_URL"])

    @app.get("/health")
    def health():
        """Liveness with substance (design §5): DB + Redis + disk."""
        status = {"db": "ok", "redis": "absent"}
        try:
            conn = _connect()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            conn.close()
        except Exception:  # noqa: BLE001
            status["db"] = "error"
        rl = app.extensions.get("rate_limiter")
        if rl is not None and rl.redis is not None:
            status["redis"] = "ok" if rl.redis.ping() else "error"
        return jsonify(status), (200 if status["db"] == "ok" else 503)

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/message")
    def message_form():
        return render_template("message.html")

    @app.get("/get_qrimg/<posttype>/<shout_hash>")
    def qr_img(posttype, shout_hash):
        """QR for a capability URL. Renders the URL only — never the hash
        alone with attacker-controlled prefix (v1 lesson)."""
        buf = io.BytesIO()
        img = qrcode.make(request.host_url.rstrip("/") + f"/stream_any/{posttype}/{shout_hash}")
        img.save(buf)
        buf.seek(0)
        return Response(buf, mimetype="image/png",
                        headers={"X-Robots-Tag": "noindex, noarchive"})

    _META_SQL = """
SELECT shout_type, max_hits, max_hits - current_hits AS views_left,
       expires_at
  FROM shouts
 WHERE hash = %s AND is_active
   AND current_hits < max_hits
   AND expires_at > %s
"""

    @app.get("/meta/<posttype>/<shout_hash>")
    def meta(posttype, shout_hash):
        """NON-CONSUMING metadata for the reader gate (spec §6).

        Reads only — never claims, never logs, never flips. Uniform
        404 {"error": ...} for burned/expired/consumed/never-existed:
        no leak which (a fully-consumed-but-unflipped row 404s too —
        gate major #2). views_left ALREADY includes the next view.
        """
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(_META_SQL, (shout_hash, now_utc()))
                row = cur.fetchone()
                if row is None:
                    return jsonify(error="no such shout"), 404
                shout_type, max_hits, views_left, expires_at = row
        return jsonify(
            type=shout_type,
            max_hits=max_hits,
            views_left=views_left,
            expires_at=expires_at.isoformat() + "Z",
        )

    @app.post("/post/text")
    def post_text():
        if not rate_limiter.allow(request.remote_addr or "unknown"):
            return jsonify(error="too many requests"), 429
        try:
            maxhits, maxtime = _parse_limits(request.form)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

        data = request.form.get("data", "")
        encoded = data.encode("utf-8")
        if not encoded:
            return jsonify(error="empty shout"), 400
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

    @app.post("/post/<posttype>")
    def post_media(posttype):
        if posttype not in MEDIA_SPECS or posttype == "text":
            return jsonify(error="unsupported content type"), 404
        if not rate_limiter.allow(request.remote_addr or "unknown"):
            return jsonify(error="too many requests"), 429
        cap, allowed = MEDIA_SPECS[posttype]

        try:
            maxhits, maxtime = _parse_limits(request.form)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

        f = request.files.get("data")
        if f is None:
            return jsonify(error="missing data file"), 400

        # NOTE (design §5, stream-not-buffer): the read below is bounded
        # by the per-type cap; bytea INSERT requires the whole payload.
        data = f.stream.read(cap + 1)
        if len(data) > cap:
            return jsonify(error=f"{posttype} exceeds the size cap"), 413
        if not data:
            return jsonify(error="empty upload"), 400

        mime = _sniff_mime(data)
        if mime is None or mime not in allowed:
            return jsonify(error="content does not match the declared type"), 415

        shout_hash = "h" + secrets.token_hex(16)
        storage_key = "s" + secrets.token_hex(16)
        expires_at = now_utc() + datetime.timedelta(minutes=maxtime)

        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _INSERT_SHOUT_SQL,
                    (shout_hash, storage_key, posttype, maxhits, expires_at),
                )
                cur.execute(
                    _INSERT_BLOB_SQL,
                    (storage_key, mime, len(data), data),
                )
            conn.commit()
        except Exception:  # noqa: BLE001
            conn.rollback()
            app.logger.exception("create %s shout failed", posttype)
            return jsonify(error="could not store the shout"), 500
        finally:
            conn.close()

        return jsonify(url=f"/stream_any/{posttype}/{shout_hash}")

    @app.get("/stream_any/<posttype>/<shout_hash>")
    def stream_any(posttype, shout_hash):
        valid_types = ("text",) + tuple(MEDIA_SPECS)
        if posttype not in valid_types:
            return jsonify(error="unsupported content type"), 404

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

            if posttype != "text" and mime not in ALLOWED_MIMES:
                # defense-in-depth: only the create path writes mimes
                app.logger.error("shout %r has bad mime %r", shout_hash, mime)
                return jsonify(error="storage error"), 500

            _log_hit(conn, shout_hash)
            resp = Response(bytes(content), mimetype=mime)
            # Anti-preview as METADATA (design §4.2): possession of the
            # URL is the capability; robots directives keep preview bots
            # from archiving what the referrer gate failed to protect.
            resp.headers["X-Robots-Tag"] = "noindex, noarchive"
            resp.headers["Cache-Control"] = "no-store"
            # Gate major #3: untrusted bytes served inline — kill the
            # browser-sniffing residual and cage any active content.
            resp.headers["X-Content-Type-Options"] = "nosniff"
            resp.headers["Content-Security-Policy"] = (
                "default-src 'none'; img-src 'self' data:; media-src 'self'"
            )
            return resp
        finally:
            conn.close()

    return app


# ─── CLI: cleanup is a PROCESS, never an unauthenticated HTTP route ───────────

def _cli_cleanup() -> int:
    """Run the reaper. cron/systemd/container-friendly: exits 0/1."""
    import os
    import sys

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print(
            "DATABASE_URL is not set — point me at the Postgres that "
            "holds the state (see .env.example).",
            file=sys.stderr,
        )
        return 2
    with psycopg.connect(dsn) as conn:
        flipped, deleted, pruned = reap(conn)
    print(
        f"reaped: {flipped} flipped, {deleted} deleted, "
        f"{pruned} hit-logs pruned"
    )
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "cleanup":
        sys.exit(_cli_cleanup())
    print("usage: python -m app [cleanup]", file=sys.stderr)
    sys.exit(64)
