"""Image manifest regression — the app image must COPY every runtime module.

Live-deploy lesson 2026-11-08: live.py shipped in the repo but was never
added to the Dockerfile COPY list — every in-repo test passed (imports
resolve from the working tree), and the container crash-looped with
ModuleNotFoundError: No module named 'live'. The image manifest is a
seam: assert it explicitly. Same for the compose schema mounts: a fresh
Postgres volume must get BOTH schemas (initdb runs them alphabetically;
schema-live.sql and schema.sql are independent).
"""

import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _dockerfile():
    with open(os.path.join(REPO, "Dockerfile")) as fh:
        return fh.read()


def test_dockerfile_copies_all_runtime_modules():
    required = {
        "app.py",
        "live.py",           # the 2026-11-08 miss
        "schema.sql",
        "schema-live.sql",   # and its schema twin
        "passenger_wsgi.py",
    }
    df = _dockerfile()
    copy_lines = [
        line for line in df.splitlines() if line.startswith("COPY ")
    ]
    assert copy_lines, "no COPY lines found — wrong file?"
    copied = set()
    for line in copy_lines:
        copied.update(line.split()[1:-1])  # skip COPY and the dest
    missing = required - copied
    assert not missing, (
        f"runtime files not COPYed into the image: {sorted(missing)} — "
        "the container will crash-loop exactly like live.py did"
    )


def test_web_image_builds_from_source_not_a_gitignored_dist():
    """The web image must BUILD the SPA from source (multi-stage) — never
    COPY a pre-built web/dist, which git does not ship: the maintainer's
    deploy kept serving a stale phase-1.5 bundle because his local dist
    predated GO LIVE. (Build-vs-source seam, live-reported.)"""
    with open(os.path.join(REPO, "Dockerfile.web")) as fh:
        df = fh.read()
    copy_sources = [
        line.split()[1] for line in df.splitlines() if line.startswith("COPY ")
    ]
    stale = [s for s in copy_sources if s.startswith("web/dist")]
    assert not stale, (
        f"the web image COPYes {stale} — a gitignored build artifact; "
        "deployments without a fresh local build serve a stale bundle. "
        "Use a multi-stage build (node stage builds, nginx stage serves)."
    )
    assert "FROM node" in df, "expected a node build stage"
    assert "npm run build" in df, "the bundle must be built inside the image"


def test_compose_mounts_both_schemas_for_fresh_volumes():
    with open(os.path.join(REPO, "docker-compose.yml")) as fh:
        compose = fh.read()
    assert (
        "schema-live.sql:/docker-entrypoint-initdb.d/schema-live.sql:ro"
        in compose
    ), "fresh Postgres volumes must create live_sessions/live_messages too"
