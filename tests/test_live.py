"""RED — live session lifecycle (Radio Puppa Live, design §4/§5).

Locked decisions under test: two URLs (listener/source-token), ≤24h
fuse, 30s heartbeat death, optional listener cap, uniform BURNED,
save-as-shout only on explicit creator action.
"""

import pytest


def _make_app(db):
    from app import create_app

    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-0123456789abcdef0123456789abcdef",
            "DATABASE_URL": db.info.dsn,
        }
    )




def test_create_returns_two_urls_and_24h_cap(live_api, live_db):
    r = live_api.post("/live", json={"maxhours": 24, "cap": None})
    assert r.status_code == 200
    body = r.get_json()
    assert body["listener_url"].startswith("/live/")
    assert body["source_url"].startswith("/live/")
    # token is in the source URL, NOT in the listener URL
    assert "token=" in body["source_url"]
    assert "token=" not in body["listener_url"]
    assert body["listener_url"] != body["source_url"]


def test_create_rejects_over_24h(live_api):
    r = live_api.post("/live", json={"maxhours": 25, "cap": None})
    assert r.status_code == 400


def test_meta_is_on_air_with_fuse(live_api, live_db):
    r = live_api.post("/live", json={"maxhours": 24, "cap": None})
    h = r.get_json()["listener_url"].rsplit("/", 1)[1]
    m = live_api.get(f"/live/{h}/meta")
    assert m.status_code == 200
    j = m.get_json()
    assert j["on_air"] is True
    assert "expires_at" in j


def test_ended_session_is_uniform_burned(live_api, live_db):
    r = live_api.post("/live", json={"maxhours": 24, "cap": None})
    body = r.get_json()
    h = body["listener_url"].rsplit("/", 1)[1]
    token = body["source_url"].split("token=")[1]

    end = live_api.post(f"/live/{h}/end", query_string={"token": token})
    assert end.status_code == 200

    # meta, poll, say: ALL uniform 404 {"error": ...} — never leak which
    for call in (
        lambda: live_api.get(f"/live/{h}/meta"),
        lambda: live_api.get(f"/live/{h}/poll?after=0"),
        lambda: live_api.get(f"/live/nosuchhash0000000000000000000/meta"),
    ):
        rr = call()
        assert rr.status_code == 404
        assert set(rr.get_json().keys()) == {"error"}


def test_segment_push_requires_valid_token(live_api, live_db):
    import io

    r = live_api.post("/live", json={"maxhours": 24, "cap": None})
    body = r.get_json()
    h = body["listener_url"].rsplit("/", 1)[1]
    token = body["source_url"].split("token=")[1]
    seg = b"\x1aE\xdf\xa3" + b"\x00" * 60  # webm-ish bytes

    def push(tok=None):
        return live_api.post(
            f"/live/{h}/seg",
            query_string={"token": tok} if tok else None,
            data={"data": (io.BytesIO(seg), "c.webm")},
            content_type="multipart/form-data",
        )

    assert push().status_code == 401            # no token
    assert push("wrong" * 8).status_code == 401  # bad token
    ok = push(token)
    assert ok.status_code == 200
    assert "seq" in ok.get_json()


def test_listener_cap_enforced_on_join(live_api, live_db):
    r = live_api.post("/live", json={"maxhours": 24, "cap": 1})
    body = r.get_json()
    h = body["listener_url"].rsplit("/", 1)[1]

    first = live_api.get(f"/live/{h}/join")
    assert first.status_code == 200
    assert first.get_json()["seat"] is True

    second = live_api.get(f"/live/{h}/join")
    assert second.status_code == 409
    assert "full" in second.get_json()["error"].lower()
