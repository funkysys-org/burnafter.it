"""burnafter.it — Radio Puppa Live: ephemeral anonymous streaming.

Design: developers-team/repos/burnafter.it-analysis/60-stream-design.md
Locked: ≤24h fuse; 30s heartbeat death; optional listener cap;
save-as-shout only explicit; source token constant-time; uniform
BURNED for ended/expired/nonexistent; chunks ONLY in Redis (TTL =
session expiry) — never Postgres, never disk.
"""

import datetime
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
HEARTBEAT_S = 30
SEG_CAP = 64 * 1024
SEG_TTL_FALLBACK_S = 120

_redis_clients = {}


def _r():
    url = current_app.config.get("REDIS_URL")
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
            WHERE hash = %s AND ended_at IS NULL AND expires_at > %s""",
        (h, now_utc()),
    )
    return cur.fetchone()


@live.post("/live")
def create_session():
    body = request.get_json(silent=True) or {}
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

    h = "L" + secrets.token_hex(16)
    token = secrets.token_hex(32)
    expires_at = now_utc() + datetime.timedelta(hours=hours)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO live_sessions
                       (hash, source_token, listener_cap, expires_at)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (h, token, cap, expires_at),
            )
            (sid,) = cur.fetchone()

    r = _r()
    if r is not None:
        ttl = int((expires_at - now_utc()).total_seconds()) + 60
        r.set(f"live-hb:{h}", "1", ex=ttl)
        r.set(f"live-n:{h}", 0, ex=ttl)

    return jsonify(
        listener_url=f"/live/{h}",   # SPA live page (gate: ON AIR)
        source_url=f"/live/{h}/seg?token={token}",
        session_hash=h,
        token=token,
    )


def _token_ok(provided: str, real: str) -> bool:
    if not provided:
        return False
    try:
        return hmac.compare_digest(
            provided.encode("utf-8", "surrogatepass"),
            real.encode("utf-8", "surrogatepass"),
        )
    except Exception:  # noqa: BLE001 — reject, never 500 on crafted input
        return False


@live.get("/live/<h>/meta")
def live_meta(h):
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            if row is None:
                return _burned()
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
        return jsonify(seat=True, listeners=0)
    n = r.incr(f"live-n:{h}")
    if cap is not None and n > cap:
        r.decr(f"live-n:{h}")
        return jsonify(error="session is full — the tape has no seats left"), 409
    return jsonify(seat=True, listeners=n)


@live.post("/live/<h>/seg")
def live_seg(h):
    token = request.args.get("token", "")
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            if row is None:
                return _burned()
            sid, real_token, _cap, expires_at = row
    if not _token_ok(token, real_token):
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
    seq = int(r.rpush(f"live:{h}", data) or 1)
    r.expire(f"live:{h}", ttl)
    r.set(f"live-hb:{h}", "1", ex=ttl)  # every push IS a heartbeat
    return jsonify(seq=seq)


@live.get("/live/<h>/poll")
def live_poll(h):
    import base64

    try:
        after = int(request.args.get("after", "0"))
    except ValueError:
        return jsonify(error="after must be an integer"), 400
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            if row is None:
                return _burned()
    r = _r()
    if r is None:
        return jsonify(error="live storage unavailable"), 503
    length = int(r.llen(f"live:{h}") or 0)
    segs = []
    if length > after:
        raw = r.lrange(f"live:{h}", after, -1)
        segs = [base64.b64encode(b).decode("ascii") for b in raw]
    return jsonify(seq=length, segments=segs)


@live.post("/live/<h>/end")
def live_end(h):
    token = request.args.get("token", "")
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            if row is None:
                return _burned()
            sid, real_token, _cap, _exp = row
            if not _token_ok(token, real_token):
                return jsonify(error="bad or missing source token"), 401
            cur.execute(
                "UPDATE live_sessions SET ended_at = %s WHERE id = %s",
                (now_utc(), sid),
            )
    r = _r()
    if r is not None:
        r.delete(f"live:{h}", f"live-hb:{h}", f"live-n:{h}")
    return jsonify(ended=True)


@live.post("/live/<h>/save")
def live_save(h):
    """Explicit creator choice (#3): concatenate the buffered chunks into
    a NORMAL audio shout with a normal fuse. Chunks are consumed; the
    session ends. Only the source token may call it."""
    import secrets as _secrets

    token = request.args.get("token", "")
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
            if row is None:
                return _burned()
            sid, real_token, _cap, _exp = row
            if not _token_ok(token, real_token):
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
    if mime not in ("audio/mp4", "audio/mpeg", "audio/wav"):
        mime = "audio/mp4"  # recorded streams are audio; best-effort label

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


@live.post("/live/<h>/say")
def live_say(h):
    """Anonymous chat on the live session (#phase-2 ride-along).
    Messages die with the session (FK cascade)."""
    body = request.get_json(silent=True) or {}
    nickname = (body.get("nickname") or "").strip()[:32] or "Listener"
    text = (body.get("body") or "").strip()
    if not text or len(text) > 500:
        return jsonify(error="body must be 1..500 characters"), 400
    with _connect() as conn:
        with conn.cursor() as cur:
            row = _get_live_session(cur, h)
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
            row = _get_live_session(cur, h)
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


def reap_dead_live(conn) -> int:
    """Heartbeat-death sweep: sessions ON (not manually ended) whose
    Redis heartbeat expired get ended_at set. Called by the reaper
    cycle. Returns number of sessions reaped."""
    r = _r()
    if r is None:
        return 0
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, hash FROM live_sessions
                WHERE ended_at IS NULL AND expires_at > %s""",
            (now_utc(),),
        )
        rows = cur.fetchall()
    reaped = 0
    for sid, h in rows:
        if not r.exists(f"live-hb:{h}"):
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE live_sessions SET ended_at = %s WHERE id = %s",
                    (now_utc(), sid),
                )
            r.delete(f"live:{h}", f"live-n:{h}")
            reaped += 1
    conn.commit()
    return reaped
