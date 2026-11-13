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


def test_no_spa_page_route_is_swallowed_by_the_api_proxy():
    """nginx regex locations evaluate in FILE ORDER — first match wins.
    Any SPA page path whose FIRST matching location is the API proxy
    gets sent to Flask and 404s (live-reported twice: /read in the 1.5
    gate, /live/<hash> on the production deploy). Faithful simulation:
    parse every location, evaluate in file order, and assert that for
    each SPA page URL the winning location serves the SPA, not the
    proxy."""
    import re

    with open(os.path.join(REPO, "web", "nginx.conf")) as fh:
        conf = fh.read()

    # (kind, pattern, has_proxy_pass) in FILE ORDER
    locations = []
    for m in re.finditer(
        r"location\s+(~|=)?\s*([^\s{]+)\s*\{(.*?)\n    \}", conf, re.S
    ):
        modifier, pattern, body = m.group(1), m.group(2), m.group(3)
        locations.append(
            {
                "exact": modifier == "=",
                "regex": modifier == "~",
                "pattern": pattern.rstrip("} ").strip(),
                "proxy": "proxy_pass" in body,
                "start": m.start(),
            }
        )

    spa_urls = [
        "/",
        "/create",
        "/studio",
        "/privacy",
        "/read/text/habc123def456",
        "/live/L79263f881e087c2d41943a585f3ee343",
        "/call",
        "/call/L79263f881e087c2d41943a585f3ee343",
        "/chat",
        "/chat/C79263f881e087c2d41943a585f3ee343",
    ]
    # API URLs that MUST reach the proxy — the reverse check (a page
    # regex swallowing /live/stats was live-reported: stats showed "—")
    api_urls = [
        "/live/stats",
        "/health",
        "/post/text",
        "/stream_any/text/habc123def456",
        "/meta/text/habc123def456",
        "/live/L79263f881e087c2d41943a585f3ee343/meta",
        "/live/L79263f881e087c2d41943a585f3ee343/seg",
        "/live/C79263f881e087c2d41943a585f3ee343/say",
        "/live/L79263f881e087c2d41943a585f3ee343/accept",
        "/live/L79263f881e087c2d41943a585f3ee343/ringing",
    ]
    problems = []
    missing = []
    for url in spa_urls:
        winner = None
        for loc in locations:  # file order = nginx evaluation order
            if loc["exact"]:
                if url == loc["pattern"].lstrip("="):
                    winner = loc
                    break
            elif loc["regex"]:
                try:
                    if re.search(loc["pattern"], url):
                        winner = loc
                        break
                except re.error:
                    pass
            else:  # prefix
                if url.startswith(loc["pattern"]):
                    winner = loc
                    break
        if winner is None:
            continue  # falls to nginx defaults (SPA) — acceptable
        if winner["proxy"]:
            problems.append(url)
    assert not problems, (
        f"SPA page URL(s) routed to the API proxy (Flask 404s): {problems} — "
        "each needs a dedicated location BEFORE the API regex, or the API "
        "regex must not match it (nginx: first regex match in file order wins)"
    )

    # The REVERSE check: every API URL must reach the proxy. nginx
    # evaluates EXACT matches first, then regexes in file order, then
    # prefixes — the simulator must model that, or a page regex silently
    # swallows an API route (live-reported: /live/stats -> "—" dashes).
    for url in api_urls:
        winner = None
        exact = [l for l in locations if l["exact"]]
        for loc in exact:  # nginx: exact matches beat everything
            if url == loc["pattern"].lstrip("="):
                winner = loc
                break
        if winner is None:
            for loc in locations:  # file order
                if loc["exact"]:
                    continue
                if loc["regex"]:
                    try:
                        if re.search(loc["pattern"], url):
                            winner = loc
                            break
                    except re.error:
                        pass
                else:  # prefix
                    if url.startswith(loc["pattern"]):
                        winner = loc
                        break
        if winner is None or not winner["proxy"]:
            missing.append(url)
    assert not missing, (
        f"API URL(s) NOT routed to the proxy: {missing} — a page location "
        "or regex is swallowing them (exact-match locations fix collisions; "
        "see the /live/stats incident)"
    )


def test_themes_night_and_puppa_are_actually_different():
    """Live-reported: PUPPA NIGHT rendered identical to light Puppa —
    the night block was never inserted (a silent str.replace no-op),
    while :root (light tokens) was aliased to puppa-night. A cascade
    simulation proves the default skin is DARK and distinct from the
    light choice — and guards against any future selector aliasing
    that flattens two themes into one."""
    import re

    with open(os.path.join(REPO, "web", "src", "themes.css")) as fh:
        css = fh.read()

    def resolve(theme=None):
        # strip comments first — they carry colons and prose that
        # would poison naive decl parsing
        css_nc = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        own = f'[data-theme="{theme}"]' if theme else None
        values = {}
        # file order IS the cascade: on equal specificity the LATER
        # block wins, so apply every matching block in order and let
        # later declarations overwrite earlier ones.
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css_nc):
            sels = [s.strip() for s in m.group(1).split(",")]
            if ":root" in sels or (own and own in sels):
                for decl in m.group(2).split(";"):
                    if re.match(r"\s*--[\w-]+\s*:", decl):
                        k, v = decl.split(":", 1)
                        values[k.strip()] = v.strip()
        return values

    default, night = resolve(), resolve("puppa-night")
    puppa, ember, warm = resolve("radio-puppa"), resolve("ember"), resolve("warm")
    assert default.get("--paper") == "#14100d", "the DEFAULT must be night (dark)"
    assert night.get("--paper") == "#14100d", "night must be dark-shell"
    assert puppa.get("--paper") == "#f7efdc", "light puppa stays paper"
    assert ember.get("--paper") == "#0e0c0a", (
        "EMBER must override the default — if this is #14100d, the :root "
        "block sits AFTER the theme blocks and squashes every choice "
        "(live-reported: theme switcher dead). :root goes FIRST."
    )
    assert warm.get("--paper") == "#faf6ef", "WARM must override the default too"
    assert night.get("--paper") != puppa.get("--paper"), (
        "PUPPA NIGHT and PUPPA collapsed into the same skin — check the "
        "selector aliasing and block order in themes.css"
    )
    assert night.get("--display-font") == puppa.get("--display-font"), (
        "both puppas keep the cassette soul (Silkscreen) — night is a "
        "COLOR change, not a different personality"
    )


def test_compose_mounts_both_schemas_for_fresh_volumes():
    with open(os.path.join(REPO, "docker-compose.yml")) as fh:
        compose = fh.read()
    assert (
        "schema-live.sql:/docker-entrypoint-initdb.d/schema-live.sql:ro"
        in compose
    ), "fresh Postgres volumes must create live_sessions/live_messages too"
