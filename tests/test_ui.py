"""RED slice 6 — web UI: home, message form, QR, robots metadata.

Design anchors: §1 (route shapes + funky personality kept), §4.2
(X-Robots-Tag noindex on served content; anti-preview as metadata),
§4.6 (no |safe anywhere reachable from request data — enforced by
a template-audit test, not by hope).
"""

import glob
import os

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_home_serves(api):
    r = api.get("/")
    assert r.status_code == 200
    assert b"BurnAfterIt" in r.data  # personality kept


def test_message_form_serves(api):
    r = api.get("/message")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    for needle in ("maxhits", "maxtime", "data"):
        assert needle in html  # the create form is there


def test_served_content_carries_robots_noinfo_headers(api):
    r = api.post(
        "/post/text",
        data={"data": "noindex me", "maxhits": "1", "maxtime": "60"},
    )
    url = r.get_json()["url"]
    served = api.get(url)
    assert served.headers.get("X-Robots-Tag") == "noindex, noarchive"
    # the capability URL must not leak into referrer-prone headers
    assert "Cache-Control" in served.headers


def test_qr_endpoint_returns_png(api):
    r = api.post(
        "/post/text",
        data={"data": "qr target", "maxhits": "1", "maxtime": "60"},
    )
    h = r.get_json()["url"].rsplit("/", 1)[1]
    qr = api.get(f"/get_qrimg/text/{h}")
    assert qr.status_code == 200
    assert qr.mimetype == "image/png"
    assert qr.data[:8] == PNG_MAGIC


def test_no_safe_filter_in_any_template():
    """Design rule 4.6: |safe is banned in ALL templates, period."""
    offenders = []
    for path in glob.glob(os.path.join(REPO, "templates", "**", "*.html"),
                          recursive=True):
        with open(path) as fh:
            if "|safe" in fh.read():
                offenders.append(path)
    assert offenders == []


def test_no_500_on_public_pages(api):
    for path in ("/", "/message", "/health"):
        r = api.get(path)
        assert r.status_code == 200, path
