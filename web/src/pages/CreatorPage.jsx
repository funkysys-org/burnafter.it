import React, { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import qrcode from "qrcode-generator";
import { reduced } from "./HomePage";

const TYPES = [
  { id: "text", label: "TEXT", limit: "≤ 10 KB" },
  { id: "photo", label: "PHOTO", limit: "≤ 5 MB" },
  { id: "audio", label: "AUDIO", limit: "≤ 25 MB" },
  { id: "video", label: "VIDEO", limit: "≤ 50 MB" },
];

const VIEWS_PRESETS = [1, 5, 10, 100];
const TIME_PRESETS = [15, 240, 1440];

export function fmtTTL(min) {
  if (min < 60) return `${min} min`;
  if (min % 60 === 0) {
    const h = min / 60;
    return `${h} hour${h > 1 ? "s" : ""}`;
  }
  return `${Math.floor(min / 60)}h ${String(min % 60).padStart(2, "0")}m`;
}

function VUMeter({ active, done }) {
  const [bars, setBars] = React.useState(() => Array(16).fill(4));
  React.useEffect(() => {
    if (!active) return;
    const iv = setInterval(() => {
      setBars((prev) =>
        prev.map((h, i) =>
          done ? 30 : Math.min(30, h + (8 + (i % 4) * 10 + Math.random() * 14 - h) * 0.6)
        )
      );
    }, reduced() ? 350 : 70);
    return () => clearInterval(iv);
  }, [active, done]);
  return (
    <div aria-hidden style={{ display: "flex", gap: 2, alignItems: "flex-end",
                              height: 32 }}>
      {bars.map((h, i) => (
        <div key={i} style={{
          width: 6, height: h,
          background: h > 26 ? "var(--red)" : h > 18 ? "var(--orange)" : "var(--ink)",
        }} />
      ))}
    </div>
  );
}

export default function CreatorPage() {
  const [type, setType] = useState("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [views, setViews] = useState(1);
  const [minutes, setMinutes] = useState(240);
  const [phase, setPhase] = useState("idle"); // idle|uploading|result
  const [pct, setPct] = useState(0);
  const [resultUrl, setResultUrl] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);
  const inputRef = useRef(null);

  const over = type === "text" && new Blob([text]).size > 10 * 1024;
  const canSend = phase === "idle" && !over &&
    (type === "text" ? text.trim().length > 0 : file !== null);

  const qrSrc = useMemo(() => {
    if (!resultUrl) return "";
    const qr = qrcode(0, "M");
    qr.addData(resultUrl);
    qr.make();
    return qr.createDataURL(4, 4);
  }, [resultUrl]);

  async function send() {
    setPhase("uploading");
    setPct(0);
    setError("");
    try {
      const fd = new FormData();
      fd.append("maxhits", String(views));
      fd.append("maxtime", String(minutes));
      if (type === "text") fd.append("data", text);
      else fd.append("data", file);
      // XHR for upload progress
      const url = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `/post/${type}`);
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) setPct(Math.round((e.loaded / e.total) * 100));
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            // The API returns the RAW /stream_any URL. For HUMANS the
            // branded gated reader is the destination — rewrite it
            // (gate major #1: shared/copied/QR links must open the
            // gate, not silently burn a view). Raw clients use the
            // API URL directly; it keeps working untouched.
            const raw = JSON.parse(xhr.responseText).url;
            resolve(raw.replace(/^\/stream_any\//, "/read/"));
          } else {
            let msg = "could not store the shout";
            try { msg = JSON.parse(xhr.responseText).error || msg; } catch {}
            reject(new Error(msg));
          }
        };
        xhr.onerror = () => reject(new Error("network error"));
        xhr.send(fd);
      });
      setResultUrl(location.origin + url);
      setPhase("result");
    } catch (e) {
      setError(e.message);
      setPhase("idle");
    }
  }

  function reset() {
    setPhase("idle"); setText(""); setFile(null); setResultUrl("");
    setCopied(false); setPct(0);
  }

  async function copyUrl() {
    try { await navigator.clipboard.writeText(resultUrl); }
    catch {
      const ta = document.createElement("textarea");
      ta.value = resultUrl; document.body.appendChild(ta);
      ta.select(); document.execCommand("copy"); ta.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }

  if (phase === "result") {
    return (
      <main>
        <section style={{ textAlign: "center" }}>
          <div className="sec-label">TRANSMISSION COMPLETE</div>
          <h1 style={{ margin: "8px 0" }}>
            SHOUT IS LIVE — <span style={{ color: "var(--headline-accent)" }}>
            AND ALREADY BURNING</span>
          </h1>
          <p className="dim">
            fuse: {views} view{views > 1 ? "s" : ""} or {fmtTTL(minutes)} —
            whichever runs out first burns the tape. no undo.
          </p>
        </section>
        <section className="panel" style={{ textAlign: "center" }}>
          <div className="lcd" style={{ display: "inline-block", maxWidth: "100%",
                    overflowWrap: "anywhere", textAlign: "left", margin: "10px 0" }}>
            {resultUrl}
          </div>
          <div>
            <button className="bevel" onClick={copyUrl} aria-pressed={copied}>
              {copied ? "COPIED!" : "COPY THE LINK"}
            </button>
          </div>
          <div style={{ margin: "18px 0" }}>
            <img src={qrSrc} alt="QR code of the secret link"
                 width={220} height={220} />
            <p className="dim small">scan it, save it, wave it goodbye</p>
          </div>
          <div className="chip hot" style={{ margin: "12px 0", whiteSpace: "normal" }}>
            ⚠ THIS LINK IS THE ONLY COPY. NO RESEND. NO BACKUP. NO "I LOST
            IT" RECOVERY DESK. SAVE IT NOW OR WAVE IT GOODBYE.
          </div>
          <div>
            <button className="bevel" onClick={reset}>► SHOUT ANOTHER</button>{" "}
            <Link className="bevel" to="/">BACK HOME</Link>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main>
      <section>
        <div className="sec-label">NEW SHOUT</div>
        <h1 style={{ fontSize: "clamp(24px,6vw,40px)" }}>STUDIO · CREATE</h1>
      </section>

      <section>
        <div className="sec-label">1 · PICK THE TYPE</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          {TYPES.map((t) => (
            <button key={t.id} className="bevel"
                    aria-pressed={type === t.id}
                    onClick={() => { setType(t.id); setFile(null); }}
                    style={{ minWidth: 86, justifyContent: "center" }}>
              {t.label}<br />
              <span style={{ fontSize: 9, fontFamily: "Verdana" }}>{t.limit}</span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <div className="sec-label">2 · THE CONTENT</div>
        {type === "text" ? (
          <div style={{ marginTop: 8 }}>
            <textarea ref={inputRef} value={text} maxLength={20000}
              onChange={(e) => setText(e.target.value)}
              placeholder="say it once… (≤ 10 KB)" />
            <div className="lcd" style={{ display: "inline-block", marginTop: 6,
                     background: over ? "var(--lcd-over)" : undefined }}>
              {new Blob([text]).size} / 10240 BYTES
            </div>
          </div>
        ) : (
          <div className="panel" style={{ marginTop: 8 }}>
            {file ? (
              <p>📼 {file.name} — {(file.size / 1048576).toFixed(1)} MB{" "}
                 <button className="bevel" style={{ minHeight: 0, padding: "4px 10px",
                       fontSize: 10 }}
                       onClick={() => setFile(null)}>EJECT</button></p>
            ) : (
              <button className="bevel" style={{ width: "100%", minHeight: 120 }}
                      onClick={() => fileRef.current?.click()}>
                ▣ DROP OR CLICK — {type.toUpperCase()} FILE
              </button>
            )}
            <input ref={fileRef} type="file" hidden
                   accept={type === "photo" ? "image/*" :
                           type === "audio" ? "audio/*" : "video/*"}
                   onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
        )}
      </section>

      <section>
        <div className="sec-label">3 · THE FUSE</div>
        <div className="panel" style={{ marginTop: 8,
                 display: "flex", gap: 22, flexWrap: "wrap" }}>
          <div>
            <div className="sec-label">BURN AFTER (VIEWS)</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
              <button className="bevel" style={{ padding: "10px 14px" }}
                      aria-label="fewer views"
                      onClick={() => setViews(Math.max(1, views - 1))}>−</button>
              <span className="lcd"><span className="counter">{views}</span></span>
              <button className="bevel" style={{ padding: "10px 14px" }}
                      aria-label="more views"
                      onClick={() => setViews(Math.min(100, views + 1))}>+</button>
            </div>
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              {VIEWS_PRESETS.map((v) => (
                <button key={v} className="bevel"
                        aria-pressed={views === v}
                        style={{ background: views === v ? "var(--green)" : undefined,
                                 color: views === v ? "var(--panel)" : undefined,
                                 minHeight: 44, padding: "8px 12px", fontSize: 11 }}
                        onClick={() => setViews(v)}>{v}</button>
              ))}
            </div>
          </div>
          <div>
            <div className="sec-label">OR AFTER (TIME)</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
              <button className="bevel" style={{ padding: "10px 14px" }}
                      aria-label="less time"
                      onClick={() => setMinutes(Math.max(1,
                        minutes - (minutes <= 60 ? 5 : minutes <= 240 ? 15 : 60)))}>−</button>
              <span className="lcd">{fmtTTL(minutes)}</span>
              <button className="bevel" style={{ padding: "10px 14px" }}
                      aria-label="more time"
                      onClick={() => setMinutes(Math.min(1440,
                        minutes + (minutes < 60 ? 5 : minutes < 240 ? 15 : 60)))}>+</button>
            </div>
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              {TIME_PRESETS.map((m) => (
                <button key={m} className="bevel" aria-pressed={minutes === m}
                        style={{ minHeight: 44, padding: "8px 12px", fontSize: 11 }}
                        onClick={() => setMinutes(m)}>{fmtTTL(m)}</button>
              ))}
            </div>
          </div>
        </div>
        <p className="dim small" style={{ marginTop: 6 }}>
          views OR time — whichever runs out first burns the tape. no undo.
        </p>
      </section>

      <section className="panel" style={{
               display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
        <VUMeter active={phase === "uploading"} done={false} />
        <button className="bevel primary" style={{ fontSize: 16 }} disabled={!canSend}
                onClick={send}>
          {phase === "uploading" ? `UPLOADING ${pct}%…` :
           type === "text" ? "► SHOUT IT" : "► UPLOAD & SHOUT"}
        </button>
        <span className="lcd" style={{ fontSize: 14 }}>
          {phase === "uploading" ? `SEND ${pct}%` : "STANDBY"}
        </span>
        {error && <p style={{ color: "var(--red)", flexBasis: "100%" }}>⚠ {error}</p>}
      </section>
    </main>
  );
}
