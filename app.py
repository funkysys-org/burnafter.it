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
