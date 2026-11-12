// Radio Puppa Live — source-side streaming client (creator browser).
// getUserMedia -> MediaRecorder -> 3s chunks -> /live/<h>/seg?token=…
import { reduced } from "./pages/HomePage";

export const CHUNK_MS = 3000;

// Tier A (70-external-ingest-design.md): input-device picker +
// voice/music tape type. Voice = today's behavior (processing ON,
// 32kbps). Music = processing OFF, 128kbps (the browser's voice-grade
// DSP mangles music). 128kbps ~ 48KB per 3s chunk — under the 64KB
// SEG_CAP ceiling.
export const MUSIC_BITRATE = 128000;
export const VOICE_BITRATE = 32000;

export async function listInputDevices() {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  const all = await navigator.mediaDevices.enumerateDevices();
  return all
    .filter((d) => d.kind === "audioinput")
    .map((d) => ({ deviceId: d.deviceId, label: d.label || "input device" }));
}

export async function createLiveSession(maxhours, cap, kind = "live") {
  const r = await fetch("/live", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ maxhours, cap, kind }),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "go-live failed");
  return r.json(); // { listener_url, source_url, session_hash, token, kind }
}

export async function endLiveSession(h, token) {
  const r = await fetch(`/live/${h}/end?token=${encodeURIComponent(token)}`, { method: "POST" });
  return r.ok;
}

export async function saveAsShout(h, token, maxhits, maxtime) {
  const r = await fetch(`/live/${h}/save?token=${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ maxhits, maxtime }),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || "save failed");
  return body.url; // /read/audio/<hash>
}

export class LiveSource {
  // Tier A: deviceId + music mode. deviceId = null -> OS default.
  // music = false -> voice tape (processing ON, 32kbps).
  constructor(hash, token, { deviceId = null, music = false } = {}) {
    this.hash = hash;
    this.token = token;
    this.deviceId = deviceId;
    this.music = music;
    this.recorder = null;
    this.stream = null;
    this.seq = 0;
    this.deviceGone = false;  // stale-device fallback (hot-unplug)
  }

  async start(onSeq) {
    const constraints = { audio: this.music
      ? { deviceId: this.deviceId ? { exact: this.deviceId } : undefined,
          echoCancellation: false, autoGainControl: false, noiseSuppression: false }
      : { deviceId: this.deviceId ? { exact: this.deviceId } : undefined } };
    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      if (this.deviceId && (e.name === "OverconstrainedError" ||
                            e.name === "NotFoundError")) {
        // chosen device vanished (unplugged/permission changed) — fall
        // back to the default input, honestly flagged to the UI
        this.deviceGone = true;
        this.deviceId = null;
        delete constraints.audio.deviceId;
        this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      } else {
        throw e;
      }
    }
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";
    this.recorder = new MediaRecorder(this.stream, {
      mimeType: mime,
      audioBitsPerSecond: this.music ? MUSIC_BITRATE : VOICE_BITRATE,
    });
    this.recorder.ondataavailable = async (e) => {
      if (!e.data || e.data.size === 0) return;
      const fd = new FormData();
      fd.append("data", e.data, "c.webm");
      const r = await fetch(
        `/live/${this.hash}/seg?token=${encodeURIComponent(this.token)}`,
        { method: "POST", body: fd },
      );
      if (r.ok) {
        this.seq += 1;
        onSeq?.(this.seq);
      }
    };
    this.recorder.start(CHUNK_MS);
  }

  stop() {
    try { this.recorder?.stop(); } catch {}
    this.stream?.getTracks().forEach((t) => t.stop());
  }
}

// Listener side: poll segments and keep an MSE buffer fed.
// ring: "live" (radio default) | "A" | "B" (SEC CALL — poll the OTHER's)
export class LivePlayer {
  constructor(hash, audioEl, seat, ring = "live", pollMs = 2000) {
    this.hash = hash;
    this.el = audioEl;
    this.seat = seat || "";   // renewed by poll participation (seats expire)
    this.ring = ring;
    this.pollMs = pollMs;
    this.seq = 0;
    this.mediaSource = null;
    this.sourceBuffer = null;
    this.queue = [];
    this.timer = null;
    this.running = false;
  }

  async start() {
    // gate minor #5: honest degradation — can this browser tune in at all?
    const MIME = "audio/webm; codecs=opus";
    if (typeof MediaSource === "undefined" || !MediaSource.isTypeSupported(MIME)) {
      this.unsupported = true;
      this.onUnsupported?.();
      return;
    }
    this.running = true;
    this.mediaSource = new MediaSource();
    this.el.src = URL.createObjectURL(this.mediaSource);
    this.mediaSource.addEventListener("sourceopen", () => {
      this.sourceBuffer = this.mediaSource.addSourceBuffer(MIME);
      this.sourceBuffer.addEventListener("updateend", () => this._drain());
    });
    this.timer = setInterval(() => this._poll(), this.pollMs);
    await this._poll();
  }

  async _poll() {
    if (!this.running) return;
    try {
      const u = new URL(`/live/${this.hash}/poll`, location.origin);
      u.searchParams.set("after", this.seq);
      if (this.ring !== "live") u.searchParams.set("ring", this.ring);
      if (this.seat) u.searchParams.set("seat", this.seat);  // seat renewal
      const r = await fetch(u);
      if (r.status === 404) {
        this.stop();
        this.onEnded?.();
        return;
      }
      if (!r.ok) return;
      const j = await r.json();
      for (const b64 of j.segments) {
        this.queue.push(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));
      }
      this.seq = j.seq;
      this._drain();
    } catch { /* transient — next tick retries */ }
  }

  _drain() {
    if (!this.sourceBuffer || this.sourceBuffer.updating || this.queue.length === 0) return;
    const chunk = this.queue.shift();
    try {
      this.sourceBuffer.appendBuffer(chunk);
    } catch { /* transient — next updateend retries */ }
  }

  stop() {
    this.running = false;
    clearInterval(this.timer);
  }
}
