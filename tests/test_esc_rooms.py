"""ESC chat rooms (kind='chat') — the original project's chat, revived.

Contract: a room is a live_sessions row of kind='chat' — no source
token (the link is the ONLY credential, as in the 2006 original),
anonymous say/chat on the SAME routes as live sessions, fuse-bounded,
uniform burned, storage-honest (reap deletes, messages cascade).
"""

import pytest


def _create_room(c, **kw):
    return c.post("/live", json={"kind": "chat", "maxhours": 4, **kw})


def test_room_create_returns_chat_link_no_token(live_api):
    r = _create_room(live_api)
    assert r.status_code == 200
    j = r.get_json()
    assert j["kind"] == "chat"
    assert j["listener_url"].startswith("/chat/C")
    assert j["token"] is None           # rooms have no source token
    assert "source_url" not in j


def test_room_hash_prefix_distinguishes_kinds(live_api):
    room = _create_room(live_api).get_json()
    live = live_api.post("/live", json={"maxhours": 1, "cap": None}).get_json()
    assert room["session_hash"].startswith("C")
    assert live["session_hash"].startswith("L")


def test_room_say_and_tail_on_shared_routes(live_api):
    j = _create_room(live_api).get_json()
    h = j["session_hash"]
    r1 = live_api.post(f"/live/{h}/say",
                       json={"nickname": "A", "body": "ciao stanza!"})
    assert r1.status_code == 200
    r2 = live_api.post(f"/live/{h}/say",
                       json={"nickname": "B", "body": "anonimo qui"})
    assert r2.status_code == 200
    tail = live_api.get(f"/live/{h}/chat?after=0")
    msgs = tail.get_json()["messages"]
    assert [m["body"] for m in msgs] == ["ciao stanza!", "anonimo qui"]


def test_room_meta_is_chat_kind(live_api):
    j = _create_room(live_api).get_json()
    m = live_api.get(f"/live/{j['session_hash']}/meta").get_json()
    assert m["kind"] == "chat"
    assert m["on_air"] is True
    assert "expires_at" in m


def test_live_routes_reject_chat_hashes_and_vice_versa(live_api):
    """Kind separation: a room hash hitting LIVE routes is a uniform
    404 — a room is not a live session (the 404 leaks nothing about
    kind; same discipline as every burned surface)."""
    import io

    room = _create_room(live_api).get_json()
    seg = live_api.post(
        f"/live/{room['session_hash']}/seg",
        data={"data": (io.BytesIO(b"webm-ish"), "c.webm")},
        content_type="multipart/form-data",
    )
    assert seg.status_code == 404
    assert set(seg.get_json().keys()) == {"error"}


def test_stats_endpoint_counts_kinds(live_api):
    live_api.post("/live", json={"maxhours": 1, "cap": None})
    _create_room(live_api)
    _create_room(live_api)
    live_api.post("/live", json={"kind": "call", "maxhours": 2, "cap": None})
    s = live_api.get("/live/stats")
    assert s.status_code == 200
    j = s.get_json()
    assert j["live_now"] >= 1
    assert j["chat_now"] >= 2
    assert j["call_now"] >= 1


def test_expired_room_burns_uniformly(live_api, live_db):
    import datetime

    j = _create_room(live_api).get_json()
    h = j["session_hash"]
    live_db.execute(
        "UPDATE live_sessions SET expires_at = %s WHERE hash = %s",
        (live_db.execute("SELECT now() AT TIME ZONE 'utc'").fetchone()[0]
         - datetime.timedelta(seconds=1), h),
    )
    live_db.commit()
    for call in (
        lambda: live_api.get(f"/live/{h}/meta"),
        lambda: live_api.get(f"/live/{h}/chat?after=0"),
        lambda: live_api.post(f"/live/{h}/say", json={"nickname": "X", "body": "hi"}),
    ):
        rr = call()
        assert rr.status_code == 404
        assert set(rr.get_json().keys()) == {"error"}
