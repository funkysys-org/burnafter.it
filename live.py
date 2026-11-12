"""burnafter.it — Radio Puppa Live: ephemeral anonymous streaming.

Design: developers-team/repos/burnafter.it-analysis/60-stream-design.md
Locked: ≤24h fuse; 30s heartbeat death; optional listener cap;
save-as-shout only explicit; source token constant-time; uniform
BURNED for ended/expired/nonexistent; chunks ONLY in Redis (TTL =
session expiry) — never Postgres, never disk.
"""

import datetime
import hashlib
import hmac
import secrets


def now_utc():
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)

import psycopg
import redis as redis_lib
from flask import Blueprint, current_app, jsonify, request

live = Blueprint("live", __name__)

MAX_HOURS = 24
HEARTBEAT_S = 30          # gate major #2: hb TTL — the death that's real
CREATE_GRACE_S = 300      # mic-permission grace before the first push
SEAT_TTL_S = 35           # gate major #3: seats lapse; polls renew them
SEG_CAP = 64 * 1024
SEG_TTL_FALLBACK_S = 120
RING_MAX_CHUNKS = 600     # gate major #1b: ~30min of 3s audio, then LTRIM
POLL_MAX_SEGS = 20        # gate major #1c: ~60s per poll response window

_redis_clients = {}


def _cfg(name, default):
    return current_app.config.get(name) or default


def _rate_limiter():
    return current_app.extensions.get("rate_limiter")


def _r():
    from flask import has_app_context

    if has_app_context():
        url = current_app.config.get("REDIS_URL")
    else:
        import os

        url = os.environ.get("REDIS_URL")  # CLI context (cleanup cycle)
    if not url:
        return None
    # cache per URL: test apps with different REDIS_URL must not share
    # a client (and None must never be cached as a stale client)
    client = _redis_clients.get(url)
    if client is None:
        client = redis_lib.from_url(url)
        _redis_clients[url] = client
    return client


def _connect():
    return psycopg.connect(current_app.config["DATABASE_URL"])


def _burned():
    return jsonify(error="this tape is over"), 404


def _get_live_session(cur, h):
    cur.execute(
        """SELECT id, source_token, listener_cap, expires_at
             FROM live_sessions
            WHERE hash = %s AND kind = 'live'
              AND ended_at IS NULL AND expires_at > %s""",
        (h, now_utc()),
    )
    return cur.fetchone()


def _get_call_session(cur, h):
    """Call lookup: kind='call', active, unexpired."""
    cur.execute(
        """SELECT id, source_token, callee_token, expires_at
             FROM live_sessions
            WHERE hash = %s AND kind = 'call'
              AND ended_at IS NULL AND expires_at > %s""",
        (h, now_utc()),
    )
    return cur.fetchone()


@live.post("/live/<h>/accept")
def call_accept(h):
    """The callee answers the 'ring' (the call link). Mints the callee's
    push token — rotating on each ACCEPT, so a stale tab can't hijack a
    later call on the same link. Returns both roles' ring names."""
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_call_session(cur, h)
            if row is None:
                return _burned()
            sid = row[0]
            callee_token = secrets.token_hex(32)
            callee_hash = hashlib.sha256(callee_token.encode()).hexdigest()
            cur.execute(
                "UPDATE live_sessions SET callee_token = %s WHERE id = %s",
                (callee_hash, sid),
            )
    r = _r()
    if r is not None:
        r.set(f"call-accepted:{h}", "1", ex=CALL_GRACE_S)
    return jsonify(token=callee_token, kind="call")


CALL_GRACE_S = 120  # accepted-flag window: the caller's UI polls for it


@live.get("/live/<h>/ringing")
def call_ringing(h):
    """Caller-side poll: has the callee accepted yet?"""
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_call_session(cur, h)
            if row is None:
                return _burned()
    r = _r()
    if r is None:
        return jsonify(accepted=False)
    return jsonify(accepted=bool(r.exists(f"call-accepted:{h}")))


def _get_session_for_save(cur, h):
    """Save's contract: a session the creator manually ENDED (the UI
    order: END -> SAVE button) is saveable until its fuse expires;
    an expired/heartbeat-dead/nonexistent one is not. Live listeners
    never see this row — every listener route stays on the uniform
    burned 404."""
    cur.execute(
        """SELECT id, source_token, saved_shout_hash, expires_at
             FROM live_sessions
            WHERE hash = %s
              AND ended_at IS NOT NULL
              AND expires_at > %s
              AND saved_shout_hash IS NULL""",
        (h, now_utc()),
    )
    return cur.fetchone()


def _ensure_live_schema(conn):
    """Boot-time migration: existing Postgres volumes created before the
    `kind` column (ESC chat rooms) don't get initdb re-runs — ALTER on
    boot keeps them current. Idempotent; tolerates fresh DBs where
    create_app runs before any live table exists (live tables are
    created by initdb/schema-live.sql on first boot)."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='live_sessions' AND column_name='kind'"
            )
            if cur.fetchone() is None:
                cur.execute(
                    "ALTER TABLE live_sessions ADD COLUMN kind TEXT "
                    "NOT NULL DEFAULT 'live' "
                    "CHECK (kind IN ('live', 'chat', 'call'))"
                )
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='live_sessions' AND column_name='callee_token'"
            )
            if cur.fetchone() is None:
                cur.execute(
                    "ALTER TABLE live_sessions ADD COLUMN callee_token TEXT"
                )
        conn.commit()
    except Exception:  # noqa: BLE001 — live tables may not exist yet
        conn.rollback()


def _ensure_chat_indexes(conn):
    """Index for the ESC room lookup by kind+hash. Same boot-time rules."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_kind "
                "ON live_sessions (kind, hash)"
            )
        conn.commit()
    except Exception:  # noqa: BLE001
        conn.rollback()


@live.post("/live")
def create_session():
    # gate major #1a: anonymous create is THE entry — rate-limit it
    rl = _rate_limiter()
    if rl is not None and not rl.allow(request.remote_addr or "unknown"):
        return jsonify(error="too many requests"), 429
    body = request.get_json(silent=True) or {}
    # ESC: a chat ROOM is a session of kind='chat' (no audio, no source
    # token — the room link is the only credential, as in the original)
    kind = body.get("kind", "live")
    if kind not in ("live", "chat", "call"):
        return jsonify(error="kind must be live, chat or call"), 400
    try:
        hours = float(body.get("maxhours", MAX_HOURS))
    except (TypeError, ValueError):
        return jsonify(error="maxhours must be a number"), 400
    if not 0 < hours <= MAX_HOURS:
        return jsonify(error=f"maxhours must be within 1..{MAX_HOURS}"), 400
    cap = body.get("cap")
    if cap is not None:
        try:
            cap = int(cap)
        except (TypeError, ValueError):
            return jsonify(error="cap must be an integer or null"), 400
        if not 0 < cap <= 10000:
            return jsonify(error="cap must be within 1..10000"), 400

    h = ("L" if kind in ("live", "call") else "C") + secrets.token_hex(16)
    token = secrets.token_hex(32)
    # gate minor #4: store the HASH, never the raw token (constant-time
    # compare below works identically against the hash)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = now_utc() + datetime.timedelta(hours=hours)

    with _connect() as conn:
        _ensure_live_schema(conn)
        _ensure_chat_indexes(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO live_sessions
                       (hash, kind, source_token, listener_cap, expires_at)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (h, kind, token_hash, cap, expires_at),
            )
            (sid,) = cur.fetchone()

    r = _r()
    if r is not None and kind == "live":
        # gate major #2: hb dies HEARTBEAT_S after the last push —
        # create gets the bounded mic-permission grace, pushes renew 30s
        r.set(f"live-hb:{h}", "1", ex=CREATE_GRACE_S)

    if kind == "chat":
        # ESC room: the link is the ONLY credential (no source token
        # needed — no audio to push); returned for URL symmetry but
        # never required by any chat route
        return jsonify(
            listener_url=f"/chat/{h}",
            session_hash=h,
            token=None,
            kind="chat",
        )

    if kind == "call":
        # SEC CALL: one lifecycle, one fuse, one burn — two directions.
        # The CALLER gets the source token now; the CALLEE mints one at
        # ACCEPT. Rings are per-participant: live:<h>:A (caller pushes,
        # callee polls) and live:<h>:B (callee pushes, caller polls).
        # No server-side mixing: each browser plays the other's ring.
        return jsonify(
            listener_url=f"/call/{h}",   # the callee gate (the "ring")
            session_hash=h,
            token=token,                # caller's push token
            kind="call",
        )

    return jsonify(
        listener_url=f"/live/{h}",   # SPA live page (gate: ON AIR)
        source_url=f"/live/{h}/seg?token={token}",
        session_hash=h,
        token=token,
        kind="live",
    )


def _token_ok(provided: str, real_hash: str) -> bool:
    """Constant-time compare of the provided RAW token against the
    stored SHA-256 (gate minor #4: PG never holds the raw token)."""
    if not provided:
        return False
    try:
        provided_hash = hashlib.sha256(
            provided.encode("utf-8", "surrogatepass")
        ).hexdigest()
        return hmac.compare_digest(
            provided_hash.encode(),
            real_hash.encode("utf-8", "surrogatepass"),
        )
    except Exception:  # noqa: BLE001 — reject, never 500 on crafted input
        return False


@live.get("/live/<h>/meta")
def live_meta(h):
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            if row is None:
                # ESC room? meta works for rooms too (no listeners count
                # without seats — but cap/fuse matter for the gate page)
                room = _get_room_session(cur, h)
                if room is None:
                    return _burned()
                cur.execute(
                    "SELECT listener_cap, expires_at FROM live_sessions WHERE id = %s",
                    (room[0],),
                )
                cap, expires_at = cur.fetchone()
                return jsonify(
                    on_air=True, kind="chat", listeners=None, cap=cap,
                    expires_at=expires_at.isoformat() + "Z",
                )
            sid, _tok, cap, expires_at = row
    n = 0
    r = _r()
    if r is not None:
        n = int(r.get(f"live-n:{h}") or 0)
    return jsonify(
        on_air=True,
        listeners=n,
        cap=cap,
        expires_at=expires_at.isoformat() + "Z",
    )


@live.get("/live/<h>/join")
def live_join(h):
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            if row is None:
                return _burned()
            sid, _tok, cap, _exp = row
    r = _r()
    if r is None:  # no Redis: no seat accounting — allow (degrade honestly)
        return jsonify(seat="", listeners=0)
    # gate major #3: SEATS EXPIRE. Each join gets a TTL seat key
    # (renewed by poll participation); listeners = live seat count.
    seat_ttl = int(_cfg("SEAT_TTL_S", SEAT_TTL_S))
    seat = secrets.token_hex(8)
    r.set(f"seat:{h}:{seat}", "1", ex=seat_ttl)
    n = len(r.keys(f"seat:{h}:*"))
    if cap is not None and n > cap:
        r.delete(f"seat:{h}:{seat}")  # the overflow seat never counted
        return jsonify(error="session is full — the tape has no seats left"), 409
    return jsonify(seat=seat, listeners=n)


@live.post("/live/<h>/seg")
def live_seg(h):
    token = request.args.get("token", "")
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            ring = f"live:{h}"      # the radio ring (per-session key)
            if row is None:
                # SEC CALL: either participant pushes — the token
                # decides WHICH ring (A=caller, B=callee). No mixing.
                crow = _get_call_session(cur, h)
                if crow is None:
                    return _burned()
                sid, caller_hash, callee_hash, expires_at = crow
                if callee_hash and _token_ok(token, callee_hash):
                    ring = f"live:{h}:B"
                    real_hash = callee_hash
                elif _token_ok(token, caller_hash):
                    ring = f"live:{h}:A"
                    real_hash = caller_hash
                else:
                    return jsonify(error="bad or missing source token"), 401
                row = (sid, token, None, expires_at)  # shape-compat below
            else:
                sid, real_hash, _cap, expires_at = row
                if not _token_ok(token, real_hash):
                    return jsonify(error="bad or missing source token"), 401
    f = request.files.get("data")
    if f is None:
        return jsonify(error="missing data chunk"), 400
    data = f.stream.read(SEG_CAP + 1)
    if len(data) > SEG_CAP:
        return jsonify(error="segment too large"), 413
    if not data:
        return jsonify(error="empty segment"), 400

    r = _r()
    if r is None:
        return jsonify(error="live storage unavailable"), 503

    ttl = max(
        int((expires_at - now_utc()).total_seconds()) + 60,
        SEG_TTL_FALLBACK_S,
    )
    seq = int(r.rpush(ring, data) or 1)
    # gate major #1b: ring budget — keep only the last RING_MAX_CHUNKS
    r.ltrim(ring, -int(_cfg("RING_MAX_CHUNKS", RING_MAX_CHUNKS)), -1)
    r.expire(ring, ttl)
    # gate major #2: every push renews the 30s heartbeat
    r.set(f"live-hb:{h}", "1", ex=HEARTBEAT_S)
    return jsonify(seq=seq)


@live.get("/live/<h>/poll")
def live_poll(h):
    import base64

    try:
        after = int(request.args.get("after", "0"))
    except ValueError:
        return jsonify(error="after must be an integer"), 400
    ring_name = request.args.get("ring", "live")
    if ring_name not in ("live", "A", "B"):
        return jsonify(error="ring must be live, A or B"), 400
    ring = f"live:{h}" if ring_name == "live" else f"live:{h}:{ring_name}"
    with _connect() as conn:
        with conn.cursor() as cur:
            # calls and live sessions both poll; rooms don't poll
            row = _get_live_session(cur, h) or _get_call_session(cur, h)
            if row is None:
                return _burned()
    r = _r()
    if r is None:
        return jsonify(error="live storage unavailable"), 503
    # gate major #3: poll participation renews the caller's seat
    seat = request.args.get("seat", "")
    if seat:
        seat_ttl = int(_cfg("SEAT_TTL_S", SEAT_TTL_S))
        r.expire(f"seat:{h}:{seat}", seat_ttl)
    # gate major #1c: bounded response window — a late joiner gets the
    # last POLL_MAX_SEGS segments, not the whole ring
    length = int(r.llen(ring) or 0)
    start = max(after, length - int(_cfg("POLL_MAX_SEGS", POLL_MAX_SEGS)))
    segs = []
    if length > start:
        raw = r.lrange(ring, start, -1)
        segs = [base64.b64encode(b).decode("ascii") for b in raw]
    return jsonify(seq=length, segments=segs)


@live.post("/live/<h>/end")
def live_end(h):
    token = request.args.get("token", "")
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            if row is None:
                # SEC CALL: EITHER party's hang-up burns it for BOTH
                # (maintainer-locked): caller token OR callee token.
                crow = _get_call_session(cur, h)
                if crow is None:
                    return _burned()
                sid, caller_hash, callee_hash, _exp = crow
                if not (
                    (callee_hash and _token_ok(token, callee_hash))
                    or _token_ok(token, caller_hash)
                ):
                    return jsonify(error="bad or missing source token"), 401
                cur.execute(
                    "UPDATE live_sessions SET ended_at = %s WHERE id = %s",
                    (now_utc(), sid),
                )
                conn.commit()
                r = _r()
                if r is not None:
                    r.delete(f"live:{h}", f"live:{h}:A", f"live:{h}:B",
                             f"live-hb:{h}", f"call-accepted:{h}")
                return jsonify(ended=True)
            sid, real_hash, _cap, _exp = row
            if not _token_ok(token, real_hash):
                return jsonify(error="bad or missing source token"), 401
            cur.execute(
                "UPDATE live_sessions SET ended_at = %s WHERE id = %s",
                (now_utc(), sid),
            )
    r = _r()
    if r is not None:
        r.delete(f"live-hb:{h}", f"live-n:{h}")
        # gate-major-#3 fix + save-after-end: the RING SURVIVES END —
        # the creator's SAVE button (UI order: END then SAVE) needs the
        # chunks. TTL still bounds it (max fuse), so ephemerality holds:
        # unsaved audio dies with the Redis key, never later.
        for key in r.keys(f"seat:{h}:*") or []:
            r.delete(key)
    return jsonify(ended=True)


@live.post("/live/<h>/save")
def live_save(h):
    """Explicit creator choice (#3): concatenate the buffered chunks into
    a NORMAL audio shout with a normal fuse. Works on a manually-ENDED,
    unexpired session (the StudioPage order: END -> SAVE), exactly once.
    Only the source token may call it. NOTE (minor #8): independent webm
    clusters concatenate mostly-cleanly — minor glitches possible near
    chunk boundaries; documented at the SAVE button."""
    import secrets as _secrets

    token = request.args.get("token", "")
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_session_for_save(cur, h)
            if row is None:
                return _burned()  # expired / never existed / already saved
            sid, real_token_hash, _saved, _exp = row
            if not _token_ok(token, real_token_hash):
                return jsonify(error="bad or missing source token"), 401

    body = request.get_json(silent=True) or {}
    try:
        maxhits = int(body.get("maxhits", 1))
        maxtime = int(body.get("maxtime", 240))
    except (TypeError, ValueError):
        return jsonify(error="maxhits/maxtime must be integers"), 400
    if not 1 <= maxhits <= 100:
        return jsonify(error="maxhits must be 1..100"), 400
    if not 1 <= maxtime <= 1440:
        return jsonify(error="maxtime must be 1..1440 minutes"), 400

    r = _r()
    if r is None:
        return jsonify(error="live storage unavailable"), 503
    raw = r.lrange(f"live:{h}", 0, -1)
    if not raw:
        return jsonify(error="nothing recorded to save"), 400
    data = b"".join(raw)

    # classify with the app's sniffer (import deferred: no cycle)
    from app import _sniff_mime, now_utc as _now_utc
    import datetime as _dt

    mime = _sniff_mime(data)
    if mime not in ("audio/mp4", "audio/mpeg", "audio/wav", "audio/webm"):
        mime = "audio/webm"  # MediaRecorder output; honest label (minor #6)

    shout_hash = "h" + _secrets.token_hex(16)
    storage_key = "s" + _secrets.token_hex(16)
    expires_at = _now_utc() + _dt.timedelta(minutes=maxtime)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO shouts
                       (hash, storage_key, shout_type, max_hits, expires_at)
                   VALUES (%s, %s, 'audio', %s, %s)""",
                (shout_hash, storage_key, maxhits, expires_at),
            )
            cur.execute(
                """INSERT INTO blobs
                       (storage_key, mime_type, size_bytes, content)
                   VALUES (%s, %s, %s, %s)""",
                (storage_key, mime, len(data), data),
            )
            cur.execute(
                """UPDATE live_sessions
                      SET ended_at = %s, saved_shout_hash = %s
                    WHERE id = %s""",
                (_now_utc(), shout_hash, sid),
            )
    r.delete(f"live:{h}", f"live-hb:{h}", f"live-n:{h}")
    # human link goes to the gated reader (/read), raw clients use
    # /stream_any — same contract as the creator page (gate major #1)
    return jsonify(url=f"/read/audio/{shout_hash}")


@live.get("/live/stats")
def live_stats():
    """Tiny aggregate for the home page: REAL counts only — active live
    sessions and open chat rooms. No per-item data, no hashes leaked."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT
                       count(*) FILTER (WHERE kind = 'live' AND ended_at IS NULL AND expires_at > %s),
                       count(*) FILTER (WHERE kind = 'chat' AND ended_at IS NULL AND expires_at > %s)
                     FROM live_sessions""",
                (now_utc(), now_utc()),
            )
            live_now, chat_now = cur.fetchone()
    return jsonify(live_now=live_now, chat_now=chat_now)


def _get_room_session(cur, h):
    """ESC room lookup: kind='chat', active, unexpired. Rooms have no
    source token — the link is the credential (as in the original
    project). Same uniform-burned contract as everything else."""
    cur.execute(
        """SELECT id FROM live_sessions
            WHERE hash = %s AND kind = 'chat'
              AND ended_at IS NULL AND expires_at > %s""",
        (h, now_utc()),
    )
    return cur.fetchone()


@live.post("/live/<h>/say")
def live_say(h):
    # gate minor #7: anonymous chat throttled per SESSION+IP (a separate
    # bucket from /live create — talking shouldn't eat the go-live quota)
    rl = _rate_limiter()
    if rl is not None and not rl.allow(f"say:{h}:{request.remote_addr or 'unknown'}"):
        return jsonify(error="too many requests"), 429
    body = request.get_json(silent=True) or {}
    nickname = (body.get("nickname") or "").strip()[:32] or "Listener"
    text = (body.get("body") or "").strip()
    if not text or len(text) > 500:
        return jsonify(error="body must be 1..500 characters"), 400
    with _connect() as conn:
        with conn.cursor() as cur:
            # ESC: rooms (kind='chat') have no source token — the link
            # is the credential; live sessions use the standard lookup
            row = _get_room_session(cur, h) or _get_live_session(cur, h)
            if row is None:
                return _burned()
            sid = row[0]
            cur.execute(
                """INSERT INTO live_messages (session_id, nickname, body)
                   VALUES (%s, %s, %s) RETURNING id, said_at""",
                (sid, nickname, text),
            )
            mid, said_at = cur.fetchone()
    return jsonify(id=mid, said_at=said_at.isoformat() + "Z")


@live.get("/live/<h>/chat")
def live_chat(h):
    try:
        after = int(request.args.get("after", "0"))
    except ValueError:
        return jsonify(error="after must be an integer"), 400
    with _connect() as conn:
        with conn.cursor() as cur:
            # ESC: rooms and live sessions share the same tail route
            row = _get_room_session(cur, h) or _get_live_session(cur, h)
            if row is None:
                return _burned()
            sid = row[0]
            cur.execute(
                """SELECT id, nickname, body, said_at
                     FROM live_messages
                    WHERE session_id = %s AND id > %s
                    ORDER BY id""",
                (sid, after),
            )
            msgs = [
                {
                    "id": i,
                    "nickname": n,
                    "body": b,
                    "said_at": s.isoformat() + "Z",
                }
                for (i, n, b, s) in cur.fetchall()
            ]
    return jsonify(messages=msgs)


def reap_dead_live(conn) -> tuple:
    """Sweep for the CLI cycle: (1) heartbeat-death — sessions ON whose
    Redis hb expired get ended_at set; (2) STORAGE HONESTY — expired
    rows are DELETED so 'messages die with the session' is true of
    storage, not just access (messages cascade). Returns
    (heartbeat_ended, expired_deleted). Tolerates a missing
    live_sessions table (shout-only deployments)."""
    r = _r()
    ended = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, hash FROM live_sessions
                    WHERE ended_at IS NULL AND expires_at > %s""",
                (now_utc(),),
            )
            rows = cur.fetchall()
        if r is not None:
            for sid, h in rows:
                if not r.exists(f"live-hb:{h}"):
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE live_sessions SET ended_at = %s WHERE id = %s",
                            (now_utc(), sid),
                        )
                    r.delete(f"live:{h}", f"live-n:{h}")
                    ended += 1
        # expired rows (any end reason): delete outright — chat cascades
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM live_sessions WHERE expires_at <= %s",
                (now_utc(),),
            )
            deleted = cur.rowcount
        conn.commit()
        return (ended, deleted)
    except psycopg.errors.UndefinedTable:
        conn.rollback()
        return (0, 0)
