"""RED slice 7 — CLI surface: cleanup (reaper) with auth-shaped safety.

Design §4.4: NO unauthenticated destructive HTTP route — the primary
cleanup trigger is CLI/in-process; a `python -m app cleanup` entry.
Tests: runs reap(), reports counts, refuses weird args, and the HTTP
surface must NOT exist (the v1 critical stays dead).
"""

import io
import json
import subprocess
import sys

import pytest

from app import reap


def test_cleanup_cli_runs_reaper(db, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", db.info.dsn)
    proc = subprocess.run(
        [sys.executable, "-m", "app", "cleanup"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0
    assert "reaped" in proc.stdout.lower()
    # idempotent second run
    proc2 = subprocess.run(
        [sys.executable, "-m", "app", "cleanup"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc2.returncode == 0


def test_cleanup_cli_needs_database_url(db, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    proc = subprocess.run(
        [sys.executable, "-m", "app", "cleanup"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode != 0
    assert "DATABASE_URL" in (proc.stderr + proc.stdout)


def test_no_unauthenticated_cleanup_http_route(api):
    """The v1 top-critical must stay dead: no HTTP cleanup surface."""
    for path in ("/api/admin/cleanup", "/cleanup", "/admin/cleanup"):
        for method in ("get", "post"):
            r = getattr(api, method)(path)
            assert r.status_code == 404, f"{method} {path}"


def test_reaper_via_api_state(db, make_shout):
    h = make_shout(expired=True)
    from app import reap as reap_fn

    reap_fn(db)
    row = db.execute(
        "SELECT is_active FROM shouts WHERE hash=%s", (h,)
    ).fetchone()
    assert row == (False,)
