"""RED slice 3 — binary media uploads (photo/audio/video).

Design rules under test (40-v2-mono-design.md §4.3):
  * per-type caps: photo 5MB, audio 25MB, video 50MB (global 50MB)
  * server-chosen extension/mimetype from the DECLARED type
  * magic-byte allowlist, mismatch -> reject (no content-type trust)
  * client filenames never touch the filesystem or storage keys
"""

import io

JPEG_MAGIC = b"\xff\xd8\xff" + b"\x00" * 29   # FFD8FF + filler
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
WAV_MAGIC = b"RIFF\x24\x00\x00\x00WAVE" + b"\x00" * 8
MP4_MAGIC = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8
PHOTO_CAP = 5 * 1024 * 1024


def _post_file(api, posttype, data, filename="evil..%2F..%2Fpasswd.jpg",
               extra=None):
    form = {"maxhits": "1", "maxtime": "60"}
    if extra:
        form.update(extra)
    return api.post(
        f"/post/{posttype}",
        data={"data": (io.BytesIO(data), filename), **form},
        content_type="multipart/form-data",
    )


def test_photo_jpeg_roundtrip(api):
    payload = JPEG_MAGIC + b"jpegbody" * 10
    r = _post_file(api, "photo", payload)
    assert r.status_code == 200
    url = r.get_json()["url"]
    assert "/stream_any/photo/" in url

    served = api.get(url)
    assert served.status_code == 200
    assert served.data == payload
    assert served.mimetype == "image/jpeg"


def test_photo_png_accepted(api):
    r = _post_file(api, "photo", PNG_MAGIC + b"pngbody")
    assert r.status_code == 200
    served = api.get(r.get_json()["url"])
    assert served.mimetype == "image/png"


def test_photo_rejected_on_magic_mismatch(api):
    # bytes are text, declared photo -> no trust, reject
    r = _post_file(api, "photo", b"plainly not an image" * 10)
    assert r.status_code == 415


def test_photo_rejected_over_cap(api):
    big = JPEG_MAGIC + b"\x00" * (PHOTO_CAP + 1)
    r = _post_file(api, "photo", big)
    assert r.status_code == 413


def test_audio_wav_roundtrip(api):
    payload = WAV_MAGIC + b"audiodata" * 100
    r = _post_file(api, "audio", payload)
    assert r.status_code == 200
    served = api.get(r.get_json()["url"])
    assert served.status_code == 200
    assert served.data == payload
    assert served.mimetype == "audio/wav"


def test_video_mp4_roundtrip(api):
    payload = MP4_MAGIC + b"videodata" * 100
    r = _post_file(api, "video", payload)
    assert r.status_code == 200
    served = api.get(r.get_json()["url"])
    assert served.status_code == 200
    assert served.data == payload
    assert served.mimetype == "video/mp4"


def test_client_filename_never_reaches_storage(api, db):
    """Traversal-flavored filename must be ignored: server names blobs."""
    r = _post_file(api, "photo", JPEG_MAGIC + b"body",
                   filename="../../etc/passwd.png")
    assert r.status_code == 200
    h = r.get_json()["url"].rsplit("/", 1)[1]
    rows = db.execute(
        "SELECT storage_key FROM shouts WHERE hash = %s", (h,)
    ).fetchall()
    assert rows and all("../" not in sk and "/" not in sk for (sk,) in rows)


def test_unsupported_type_route_rejected(api):
    r = _post_file(api, "exe", JPEG_MAGIC + b"payload")
    assert r.status_code == 404


def test_claim_still_governs_media(api):
    """maxhits=1 media burns after first serve (single primitive)."""
    r = _post_file(api, "audio", WAV_MAGIC + b"x")
    url = r.get_json()["url"]
    assert api.get(url).status_code == 200
    assert api.get(url).status_code == 404
