"""SEC CALL — one lifecycle, one fuse, one burn; two directions.

Locked decisions (maintainer, 2026-11-09): honest-poll v1 latency;
either party's hang-up burns for both; link+QR is the ring; NO
recording in v1. Design: 80-call-design.md (folded into this suite).
"""

import io

import pytest


def _make_call(c, **kw):
    r = c.post("/live", json={"kind": "call", "maxhours": 2, **kw})
    assert r.status_code == 200, r.get_data(as_text=True)
    return r.get_json()


def _push(c, h, token, data=b"\x1aE\xdf\xa3CALL" + b"\x00" * 40):
    return c.post(
        f"/live/{h}/seg?token={token}",
        data={"data": (io.BytesIO(data), "c.webm")},
        content_type="multipart/form-data",
    )


def test_call_create_returns_link_and_caller_token(live_api):
    j = _make_call(live_api)
    assert j["kind"] == "call"
    assert j["listener_url"].startswith("/call/")
    assert j["session_hash"].startswith("L")
    assert j["token"]  # caller's push token


def test_call_full_flow_accept_dual_rings(live_api, live_db):
    import redis as redis_lib

    r = redis_lib.from_url("redis://localhost:6379/15")
    j = _make_call(live_api)
    h, caller_tok = j["session_hash"], j["token"]

    # ringing: not accepted yet
    assert live_api.get(f"/live/{h}/ringing").get_json()["accepted"] is False

    # the callee ACCEPTS -> gets their own push token
    acc = live_api.post(f"/live/{h}/accept")
    assert acc.status_code == 200
    callee_tok = acc.get_json()["token"]
    assert callee_tok != caller_tok
    assert live_api.get(f"/live/{h}/ringing").get_json()["accepted"] is True

    # caller pushes A, callee pushes B — separate rings
    assert _push(live_api, h, caller_tok, b"\x1aE\xdf\xa3FROM-CALLER").status_code == 200
    assert _push(live_api, h, callee_tok, b"\x1aE\xdf\xa3FROM-CALLEE").status_code == 200
    assert r.llen(f"live:{h}:A") == 1
    assert r.llen(f"live:{h}:B") == 1

    # each polls the OTHER's ring
    import base64

    pa = live_api.get(f"/live/{h}/poll?ring=A&after=0").get_json()
    assert base64.b64decode(pa["segments"][0]) == b"\x1aE\xdf\xa3FROM-CALLER"
    pb = live_api.get(f"/live/{h}/poll?ring=B&after=0").get_json()
    assert base64.b64decode(pb["segments"][0]) == b"\x1aE\xdf\xa3FROM-CALLEE"

    # a WRONG token never pushes
    assert _push(live_api, h, "f" * 64).status_code == 401


def test_accept_rotates_the_callee_token(live_api):
    j = _make_call(live_api)
    h = j["session_hash"]
    tok1 = live_api.post(f"/live/{h}/accept").get_json()["token"]
    tok2 = live_api.post(f"/live/{h}/accept").get_json()["token"]
    assert tok1 != tok2  # stale tab can't hijack a later accept
    # the OLD token no longer pushes
    assert _push(live_api, h, tok1).status_code == 401
    assert _push(live_api, h, tok2).status_code == 200


def test_either_hangup_burns_for_both(live_api):
    j = _make_call(live_api)
    h, caller_tok = j["session_hash"], j["token"]
    callee_tok = live_api.post(f"/live/{h}/accept").get_json()["token"]
    _push(live_api, h, caller_tok)

    # CALLEE hangs up — with THEIR token
    end = live_api.post(f"/live/{h}/end?token={callee_tok}")
    assert end.status_code == 200

    # both sides see uniform burned
    for call in (
        lambda: live_api.get(f"/live/{h}/ringing"),
        lambda: live_api.get(f"/live/{h}/poll?ring=A&after=0"),
        lambda: live_api.post(f"/live/{h}/seg?token={caller_tok}",
                              data={"data": (io.BytesIO(b"x"), "c.webm")},
                              content_type="multipart/form-data"),
    ):
        rr = call()
        assert rr.status_code == 404


def test_call_hash_on_live_routes_is_uniform_404(live_api):
    j = _make_call(live_api)
    h = j["session_hash"]
    # a call is not a live radio session: /join and /meta-live 404 flat
    assert live_api.get(f"/live/{h}/join").status_code == 404


def test_expired_call_burns_uniformly(live_api, live_db):
    import datetime

    j = _make_call(live_api)
    h = j["session_hash"]
    live_db.execute(
        "UPDATE live_sessions SET expires_at = %s WHERE hash = %s",
        (live_db.execute("SELECT now() AT TIME ZONE 'utc'").fetchone()[0]
         - datetime.timedelta(seconds=1), h),
    )
    live_db.commit()
    assert live_api.post(f"/live/{h}/accept").status_code == 404
    assert live_api.get(f"/live/{h}/ringing").status_code == 404
