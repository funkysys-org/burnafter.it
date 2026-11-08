-- burnafter.it — live sessions (Radio Puppa Live), design 60-stream-design.md
CREATE TABLE IF NOT EXISTS live_sessions (
    id               BIGSERIAL PRIMARY KEY,
    hash             TEXT NOT NULL UNIQUE CHECK (length(hash) BETWEEN 20 AND 64),
    source_token     TEXT NOT NULL,          -- SHA-256 hex of the source
                                                -- token; raw token never
                                                -- stored; constant-time
                                                -- compare against the hash;
                                                -- dies with session
    listener_cap     INTEGER,                -- NULL = unlimited (locked #2)
    created_at       TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    expires_at       TIMESTAMP NOT NULL,     -- ≤ 24h from creation (locked #1)
    ended_at         TIMESTAMP,              -- manual end / heartbeat death
    saved_shout_hash TEXT                    -- set only by explicit save (#3)
);

CREATE INDEX IF NOT EXISTS idx_live_active
    ON live_sessions (expires_at) WHERE ended_at IS NULL;

-- chat-on-stream (phase 2) rides the same session; messages die with it
CREATE TABLE IF NOT EXISTS live_messages (
    id          BIGSERIAL PRIMARY KEY,
    session_id  BIGINT NOT NULL REFERENCES live_sessions (id) ON DELETE CASCADE,
    nickname    TEXT NOT NULL,
    body        TEXT NOT NULL CHECK (length(body) <= 500),
    said_at     TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);
