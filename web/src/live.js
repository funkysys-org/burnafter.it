// Radio Puppa Live — source-side streaming client (creator browser).
// getUserMedia -> MediaRecorder -> 3s chunks -> /live/<h>/seg?token=…
import { reduced } from "./pages/HomePage";

export const CHUNK_MS = 3000;

export async function createLiveSession(maxhours, cap) {
  const r = await fetch("/live", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ maxhours, cap }),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "go-live failed");
  return r.json(); // { listener_url, source_url, session_hash, token }
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
  constructor(hash, token) {
    this.hash = hash;
    this.token = token;
    this.recorder = null;
    this.stream = null;
    this.seq = 0;
  }

  async start(onSeq) {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";
    this.recorder = new MediaRecorder(this.stream, {
      mimeType: mime,
      audioBitsPerSecond: 32000,
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
export class LivePlayer {
  constructor(hash, audioEl) {
    this.hash = hash;
    this.el = audioEl;
    this.seq = 0;
    this.mediaSource = null;
    this.sourceBuffer = null;
    this.queue = [];
    this.timer = null;
    this.running = false;
  }

  async start() {
    this.running = true;
    this.mediaSource = new MediaSource();
    this.el.src = URL.createObjectURL(this.mediaSource);
    this.mediaSource.addEventListener("sourceopen", () => {
      this.sourceBuffer = this.mediaSource.addSourceBuffer("audio/webm; codecs=opus");
      this.sourceBuffer.addEventListener("updateend", () => this._drain());
    });
    this.timer = setInterval(() => this._poll(), 2000);
    await this._poll();
  }

  async _poll() {
    if (!this.running) return;
    try {
      const r = await fetch(`/live/${this.hash}/poll?after=${this.seq}`);
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
