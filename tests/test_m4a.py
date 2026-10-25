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

# ── codec-based classification (v3): brand lists are unreliable —
# Android/encoder m4a files carry isom brands with NO M4A marker and
# the audio codec (mp4a) only inside moov, which can sit at EOF.
AUDIO_CODECS = (b"mp4a", b"alac", b"Opus", b"samr", b"ac-3", b"ec-3")
VIDEO_CODECS = (b"avc1", b"avc3", b"hev1", b"hvc1", b"mp4v", b"encv", b"av01")

def _boxed(major, compat, codecs):
    """ftyp + a minimal moov carrying the given codec 4CCs."""
    body = b"ftyp" + major + b"\x00\x00\x00\x00" + compat
    ftyp = (4 + len(body)).to_bytes(4, "big") + body
    stsd = b"\x00" * 16 + b"".join(c + b"\x00" * 24 for c in codecs)
    moov_body = b"moov" + stsd
    moov = (4 + len(moov_body)).to_bytes(4, "big") + moov_body
    return ftyp + moov + b"\x00" * 64

CODEC_CASES = [
    ("android m4a: isom brands, mp4a codec, NO M4A",
     _boxed(b"isom", b"iso2mp41", [b"mp4a"]), "audio/mp4"),
    ("alac m4a", _boxed(b"M4A ", b"", [b"alac"]), "audio/mp4"),
    ("video with sound: avc1 + mp4a -> VIDEO (video wins)",
     _boxed(b"isom", b"isom", [b"avc1", b"mp4a"]), "video/mp4"),
    ("plain video avc1", _boxed(b"isom", b"isom", [b"avc1"]), "video/mp4"),
    ("hevc video", _boxed(b"isom", b"isom", [b"hev1"]), "video/mp4"),
]


@pytest.mark.parametrize("name,payload,expected", CASES, ids=[c[0] for c in CASES])
def test_m4a_major_brands(name, payload, expected):
    assert _sniff_mime(payload) == expected


@pytest.mark.parametrize("name,payload,expected", CODEC_CASES, ids=[c[0] for c in CODEC_CASES])
def test_mp4_family_codec_classification(name, payload, expected):
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


def test_android_m4a_without_brand_passes_audio_route(api):
    """Live-report round 2: Android/encoder m4a — isom brands, NO M4A
    marker, mp4a codec only inside moov. Must upload as audio."""
    payload = _boxed(b"isom", b"iso2mp41", [b"mp4a"])
    r = api.post(
        "/post/audio",
        data={
            "data": (io.BytesIO(payload), "rec.m4a"),
            "maxhits": "1",
            "maxtime": "60",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    served = api.get(r.get_json()["url"])
    assert served.mimetype == "audio/mp4"


def test_415_is_diagnostic(api):
    """The mismatch error must say WHAT was detected — no more guessing
    from 'content does not match' alone."""
    payload = _ftyp(b"isom", b"isommp42")  # video-ish, no M4A, no codecs
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
    assert "detected:" in r.get_json()["error"]


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
