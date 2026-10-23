"""Passenger entry point (deploy-agnostic re-entry path, design §6.3).

The v1 shim used imp.load_source — removed in Python 3.12 — and was
dead code on any modern host. This one is a plain import.

Passenger (Apache) usage: point the app root at this directory; set
DATABASE_URL (+ REDIS_URL optionally) in the Passenger env. All state
lives in the central Postgres/Redis — this host holds NO local state.
"""

from app import create_app

application = create_app()
