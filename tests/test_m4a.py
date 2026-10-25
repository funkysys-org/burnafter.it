"""m4a sniffing — real-world major brands (live maintainer report).

The gate-round test only used 'M4A ' as the MAJOR brand. Real .m4a
files very often carry major brand 'isom'/'iso2'/'mp42' (or even
nothing audio-flavored at all) with M4A among the compatible brands —
those were classified video/mp4 and rejected 415 on the audio route.
"""

import io

import pytest

from app import _sniff_mime, MEDIA_SPECS


def _ftyp(major, compat=b""):
    # Real ISO box: size(4) counts the WHOLE box; body = ftyp+major+minor+compat
    body = b"ftyp" + major + b"\x00\x00\x00\x00" + compat
    size = 4 + len(body)
    return size.to_bytes(4, "big") + body + b"\x00" * 32


CASES = [
    ("M4A major", _ftyp(b"M4A "), "audio/mp4"),
    ("isom major + M4A compat", _ftyp(b"isom", b"isommp42M4A "), "audio/mp4"),
    ("iso2 major + M4A compat", _ftyp(b"iso2", b"iso2isomM4A "), "audio/mp4"),
    ("isom major, NO M4A marker", _ftyp(b"isom", b"isommp42"), "video/mp4"),
    ("malformed size 0, M4A major",
     b"\x00\x00\x00\x00" + b"ftypM4A \x00\x00\x00\x00" + b"\x00" * 32,
     "audio/mp4"),  # clamp scans at least major+minor
]


@pytest.mark.parametrize("name,payload,expected", CASES, ids=[c[0] for c in CASES])
def test_m4a_major_brands(name, payload, expected):
    assert _sniff_mime(payload) == expected


def test_m4a_files_pass_the_audio_route(api):
    """The live repro: an isom-brand m4a must upload via /post/audio."""
    payload = _ftyp(b"isom", b"isommp42M4A ")
    r = api.post(
        "/post/audio",
        data={
            "data": (io.BytesIO(payload), "recording.m4a"),
            "maxhits": "1",
            "maxtime": "60",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    served = api.get(r.get_json()["url"])
    assert served.status_code == 200
    assert served.mimetype == "audio/mp4"


def test_plain_mp4_video_still_rejected_on_audio_route(api):
    """Regression guard: isom without any M4A marker is a VIDEO — the
    audio route must keep refusing it (no loosening the allowlist)."""
    payload = _ftyp(b"isom", b"isommp42")  # no M4A anywhere
    r = api.post(
        "/post/audio",
        data={
            "data": (io.BytesIO(payload), "clip.mp4"),
            "maxhits": "1",
            "maxtime": "60",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 415
