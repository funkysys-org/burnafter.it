# BurnAfterIt v2-mono

Shouts that burn after N views or T minutes. No accounts — the secret
URL is the credential. Ephemeral text/photo/audio/video sharing with
a real burn guarantee.

- **Repo**: `v2-mono` branch (v1 remains on `main` and in history)
- **Design**: the full locked design lives in the squad analysis
  archive (`40-v2-mono-design.md`, Scenario C: Postgres + Redis,
  stateless app tier, deploy-agnostic).

## Architecture

One stateless Flask app + external state:

| Service | Holds | Notes |
|---|---|---|
| app (gunicorn) | nothing | stateless ×N; scale with round-robin DNS |
| Postgres | shouts, blobs (bytea), hit_logs | THE burn authority |
| Redis (optional) | sessions, rate limits | app boots without it |

The burn is **one atomic statement** (`app.py:claim`):

```sql
UPDATE shouts SET current_hits = current_hits + 1
 WHERE hash = %s AND is_active AND current_hits < max_hits AND expires_at > %s;
```

rowcount 1 = you won a view slot; rowcount 0 = burned/expired. Exactly
`max_hits` winners are possible, across any number of app replicas.
Redis never participates in burn accounting.

## Quickstart (all-in-one)

```bash
cp .env.example .env         # then set SECRET_KEY + POSTGRES_PASSWORD
docker compose up -d         # app + postgres + redis
docker compose exec app python -m app cleanup   # cron me daily
```

The app boots only with a strong SECRET_KEY (≥32 chars; known-default
keys are rejected). Postgres runs the schema on first boot via
`docker-entrypoint-initdb.d`.

## Multi-host (round-robin DNS)

1. Run `postgres` + `redis` somewhere central (this same compose,
   `docker compose up -d postgres redis`, ports uncommented +
   firewalled to app hosts).
2. On each app host: `.env` points DATABASE_URL/REDIS_URL at the
   central services, then `docker compose up -d --no-deps app`.
3. DNS round-robin the app hostname across the app hosts. Done —
   the app tier holds no state.

## Passenger (deploy-agnostic re-entry)

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
export DATABASE_URL=postgres://... REDIS_URL=redis://... SECRET_KEY=...
# Apache/Passenger app root: this directory (passenger_wsgi.py)
```

## API

- `POST /post/text` — form: `data` (≤10KB), `maxhits` (1–100), `maxtime` (minutes, 1–1440) → `{"url": "/stream_any/text/<hash>"}`
- `POST /post/{photo|audio|video}` — multipart `data` file (5/25/50MB caps, magic-byte verified) + same limits → `{"url": ...}`
- `GET /stream_any/<type>/<hash>` — THE claim: serves content or 404 "Burned!"
- `GET /health` — `{"db": "ok", "redis": "ok|absent"}`

Every served byte carries `X-Robots-Tag: noindex, noarchive` +
`Cache-Control: no-store`.

## Operations

- Cleanup: `python -m app cleanup` (flips expired, deletes past a 1h
  grace). Cron it. There is deliberately NO HTTP cleanup route.
- Backups: `pg_dump` the database; Redis needs none.
- Tests: `pytest tests/` — needs local Postgres (creates its own
  throwaway DB) and, for the Redis tests, local Redis.

## Security notes

- Parameterized SQL only; `|safe` is banned in templates (CI test).
- Uploads: server-side limits, magic-byte allowlist, server-chosen
  mime; client filenames never touch storage.
- Sessions: Redis-backed when configured, signed cookies otherwise.
- Secret URLs are bearer capabilities — treat the link like a
  password. Serve over TLS (terminate at Apache/nginx/certbot).
