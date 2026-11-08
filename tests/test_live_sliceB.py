"""RED — live slice B: save-as-shout, heartbeat death, chat-on-stream."""

import io
import time

import pytest




def _push(live_api, h, token, data=b"\x1aE\xdf\xa3" + b"\x00" * 60):
    return live_api.post(
        f"/live/{h}/seg",
        query_string={"token": token},
        data={"data": (io.BytesIO(data), "c.webm")},
        content_type="multipart/form-data",
    )


def test_save_after_end_the_ui_order(live_api, session):
    """StudioPage order: END the session, THEN the SAVE button appears.
    The backend used to 404 the save because _get_live_session excludes
    ended rows — and END also deleted the Redis ring, so the audio was
    gone even if the 404 were fixed (live-reported on the production
    deploy). Save must work on a manually-ended, unexpired session,
    exactly once; the ring survives END (TTL-bounded) for that."""
    h, token = session["h"], session["token"]
    assert _push(live_api, h, token).status_code == 200

    end = live_api.post(f"/live/{h}/end", query_string={"token": token})
    assert end.status_code == 200
    # listeners still see uniform burned
    assert live_api.get(f"/live/{h}/meta").status_code == 404

    save = live_api.post(
        f"/live/{h}/save",
        query_string={"token": token},
        json={"maxhits": 3, "maxtime": 60},
    )
    assert save.status_code == 200, save.get_data(as_text=True)
    assert save.get_json()["url"].startswith("/read/audio/")

    # second save: the ring is consumed -> uniform 404
    again = live_api.post(
        f"/live/{h}/save",
        query_string={"token": token},
        json={"maxhits": 3, "maxtime": 60},
    )
    assert again.status_code == 404


def test_save_as_shout_creates_normal_shout(live_api, session):
    h, token = session["h"], session["token"]
    _push(live_api, h, token, b"\x1aE\xdf\xa3AUDIOCHUNK1" + b"\x00" * 40)
    _push(live_api, h, token, b"\x1aE\xdf\xa3AUDIOCHUNK2" + b"\x00" * 40)
    # contract (UI order): END first, then SAVE
    live_api.post(f"/live/{h}/end", query_string={"token": token})

    r = live_api.post(
        f"/live/{h}/save",
        query_string={"token": token},
        json={"maxhits": 3, "maxtime": 60},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["url"].startswith("/read/audio/")  # human link (gate round fix)
    saved = body["url"].rsplit("/", 1)[1]

    # the saved shout is a NORMAL shout: claimable, fuse-governed
    import urllib.parse

    raw = "/stream_any/audio/" + saved
    first = live_api.get(raw)
    assert first.status_code == 200
    assert b"AUDIOCHUNK1" in first.data and b"AUDIOCHUNK2" in first.data
    assert first.mimetype == "audio/webm"  # sniffed honestly (MediaRecorder output)

    # session is ENDED after save: uniform burned
    m = live_api.get(f"/live/{h}/meta")
    assert m.status_code == 404


def test_save_requires_token(live_api, session):
    h, token = session["h"], session["token"]
    # before END: save 404s uniformly (the session is not saveable yet)
    r0 = live_api.post(f"/live/{h}/save", json={})
    assert r0.status_code == 404
    # after END: token is enforced (401 without it)
    live_api.post(f"/live/{h}/end", query_string={"token": token})
    r = live_api.post(f"/live/{h}/save", json={})
    assert r.status_code == 401


def test_heartbeat_death_ends_session(live_api, live_db, session):
    import redis as redis_lib

    from live import CREATE_GRACE_S, HEARTBEAT_S

    h, token = session["h"], session["token"]
    r = redis_lib.from_url("redis://localhost:6379/15")

    # hb TTL semantics (gate major #2): bounded grace, 30s per push
    assert 0 < r.ttl(f"live-hb:{h}") <= CREATE_GRACE_S
    assert _push(live_api, h, token).status_code == 200
    assert 0 < r.ttl(f"live-hb:{h}") <= HEARTBEAT_S

    from live import reap_dead_live

    # heartbeat alive -> not reaped
    ended, deleted = reap_dead_live(live_db)
    assert ended == 0

    # TTL lapse — NO manual delete: shorten and let it EXPIRE
    r.expire(f"live-hb:{h}", 1)
    time.sleep(1.2)
    ended, deleted = reap_dead_live(live_db)
    assert ended >= 1
    m = live_api.get(f"/live/{h}/meta")
    assert m.status_code == 404  # uniform burned


def test_chat_say_and_tail(live_api, session):
    h = session["h"]
    r1 = live_api.post(
        f"/live/{h}/say",
        json={"nickname": "Listener-4417", "body": "ciao puppa!"},
    )
    assert r1.status_code == 200
    assert r1.get_json()["id"] >= 1

    r2 = live_api.post(
        f"/live/{h}/say",
        json={"nickname": "Listener-0001", "body": "on air!"},
    )
    tail = live_api.get(f"/live/{h}/chat?after=0")
    assert tail.status_code == 200
    msgs = tail.get_json()["messages"]
    assert len(msgs) == 2
    assert msgs[0]["nickname"] == "Listener-4417"
    assert msgs[0]["body"] == "ciao puppa!"

    # incremental tail
    tail2 = live_api.get(f"/live/{h}/chat?after={msgs[0]['id']}")
    assert len(tail2.get_json()["messages"]) == 1


def test_chat_caps_body_and_rejects_ended(live_api, session):
    h = session["h"]
    too_long = live_api.post(
        f"/live/{h}/say", json={"nickname": "X", "body": "x" * 501}
    )
    assert too_long.status_code == 400

    live_api.post(f"/live/{h}/end", query_string={"token": session["token"]})
    after_end = live_api.post(
        f"/live/{h}/say", json={"nickname": "X", "body": "hi"}
    )
    assert after_end.status_code == 404
    assert set(after_end.get_json().keys()) == {"error"}
