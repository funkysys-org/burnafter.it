-- burnafter.it v2-mono — Postgres schema (Scenario C)
-- Conventions (per 40-v2-mono-design.md):
--  * Timestamps are TIMESTAMP WITHOUT TIME ZONE holding naive-UTC values.
--    (v2's aware/naive TypeError is the tombstone this avoids.)
--  * The capability hash (URL) and the storage key are DECOUPLED.
--  * ALL content — text included — is a blobs row; one storage shape,
--    one GC path, one claim primitive.
--  * Burns/hits are accounted ONLY here, never in Redis.

CREATE TABLE IF NOT EXISTS shouts (
    hash         TEXT PRIMARY KEY CHECK (length(hash) BETWEEN 20 AND 64),
    storage_key  TEXT NOT NULL UNIQUE CHECK (length(storage_key) BETWEEN 20 AND 64),
    shout_type   TEXT NOT NULL CHECK (shout_type IN ('text', 'photo', 'audio', 'video')),
    max_hits     INTEGER NOT NULL CHECK (max_hits BETWEEN 1 AND 100),
    current_hits INTEGER NOT NULL DEFAULT 0,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    expires_at   TIMESTAMP NOT NULL,
    burned_at    TIMESTAMP
);

-- Row-level claim: the ONE primitive every read of every content type
-- goes through. rowcount==1 -> won a view slot; rowcount==0 -> burned
-- or expired. Postgres serializes concurrent claims on the same row.
CREATE INDEX IF NOT EXISTS idx_shouts_active ON shouts (is_active) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_shouts_expiry ON shouts (expires_at) WHERE is_active;

CREATE TABLE IF NOT EXISTS blobs (
    storage_key TEXT PRIMARY KEY REFERENCES shouts (storage_key) ON DELETE CASCADE,
    mime_type   TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL CHECK (size_bytes >= 0),
    content     BYTEA NOT NULL
);

-- Written only AFTER a successful claim; a failure here must never
-- un-burn content (the claim transaction is already committed).
CREATE TABLE IF NOT EXISTS hit_logs (
    id         BIGSERIAL PRIMARY KEY,
    shout_hash TEXT NOT NULL,
    claimed_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);
