import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import qrcode from "qrcode-generator";
import { reduced, Masthead } from "./HomePage";
import LiveChat from "../LiveChat";

// the classic QR glyph — three corners + a few modules, inline SVG so
// it inherits the ink color in every theme
function QrIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"
         style={{ verticalAlign: "-1px", display: "inline-block" }}>
      <rect x="0" y="0" width="4" height="4" fill="currentColor" />
      <rect x="1" y="1" width="2" height="2" fill="var(--panel-bg)" />
      <rect x="8" y="0" width="4" height="4" fill="currentColor" />
      <rect x="9" y="1" width="2" height="2" fill="var(--panel-bg)" />
      <rect x="0" y="8" width="4" height="4" fill="currentColor" />
      <rect x="1" y="9" width="2" height="2" fill="var(--panel-bg)" />
      <rect x="6" y="6" width="2" height="2" fill="currentColor" />
      <rect x="9" y="8" width="2" height="2" fill="currentColor" />
      <rect x="6" y="0" width="1" height="1" fill="currentColor" />
      <rect x="0" y="6" width="1" height="1" fill="currentColor" />
    </svg>
  );
}

function fmtFuse(iso) {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "00:00";
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export default function ChatRoomPage() {
  const { hash } = useParams();
  const [phase, setPhase] = useState("gate"); // gate|room|burned
  const [meta, setMeta] = useState(null);
  const [fuse, setFuse] = useState("");
  const [qrOpen, setQrOpen] = useState(false);
  const [nick] = useState(() => "Listener-" + String(Math.floor(1000 + Math.random() * 9000)));

  // the REAL room URL — the link is the whole room, so it's the QR
  const roomUrl = `${location.origin}/chat/${hash}`;
  const qrSrc = useMemo(() => {
    const qr = qrcode(0, "M");
    qr.addData(roomUrl);
    qr.make();
    return qr.createDataURL(4, 4);
  }, [roomUrl]);

  useEffect(() => {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 800);
    fetch(`/live/${hash}/meta`, { signal: ctl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("gone"))))
      .then((j) => { setMeta(j); setFuse(fmtFuse(j.expires_at)); })
      .catch(() => setMeta(null));
    return () => { clearTimeout(t); ctl.abort(); };
  }, [hash]);

  useEffect(() => {
    if (!meta || phase !== "room") return;
    const iv = setInterval(() => setFuse(fmtFuse(meta.expires_at)), 1000);
    return () => clearInterval(iv);
  }, [meta, phase]);

  if (phase === "burned" || meta === null && phase === "burned") {
    return (
      <main style={{ textAlign: "center", padding: "60px 0" }}>
        <div style={{ fontSize: 64 }}>🔥</div>
        <h1 className="big" style={{ color: "var(--red)" }}>BURNED!</h1>
        <p style={{ margin: "10px 0" }}>this room is over — everything it said is gone</p>
        <Link to="/" className="bevel">BACK TO STUDIO</Link>
      </main>
    );
  }

  if (phase === "gate") {
    return (
      <main>
        <Masthead />
        <section style={{ textAlign: "center", padding: "40px 0" }}>
          <div style={{ fontSize: 64 }}>💬</div>
          <h1 style={{ fontFamily: "var(--display-font)" }}>ESC · EPHEMERAL SECURE CHAT</h1>
          <p className="dim" style={{ margin: "12px 0" }}>
            Anonymous chat room — no accounts, nothing recorded.{" "}
            {meta ? `The room burns in ${fuse}.` : "The link is the whole room."}
          </p>
          <button className="bevel primary" style={{ fontSize: 15 }}
                  onClick={() => (meta ? setPhase("room") : setPhase("burned"))}>
            ► ENTER THE ROOM (ANONYMOUS)
          </button>
          <p className="dim small" style={{ marginTop: 10 }}>
            when the fuse runs out, the room and everything said in it burn
          </p>
        </section>
      </main>
    );
  }

  return (
    <main>
      <Masthead />
      <section style={{ textAlign: "center" }}>
        <span className="chip live"><span className="lamp blink" /> ROOM OPEN</span>{" "}
        {meta && <span className="chip neutral">BURNS IN {fuse}</span>}{" "}
        <button className="chip neutral" title="show the room QR"
                aria-pressed={qrOpen} onClick={() => setQrOpen(true)}
                style={{ cursor: "pointer", fontSize: 11 }}>
          <QrIcon /> QR
        </button>
      </section>

      {qrOpen && (
        <div role="dialog" aria-label="room QR"
             onClick={() => setQrOpen(false)}
             style={{ position: "fixed", inset: 0, background: "#000000b3",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      zIndex: 50, padding: 16 }}>
          <div className="panel" onClick={(e) => e.stopPropagation()}
               style={{ maxWidth: 340, width: "100%", textAlign: "center" }}>
            <div className="sec-label">SCAN TO JOIN</div>
            {/* white pad behind the QR: modules are dark-on-transparent —
                on the NIGHT shell a bare QR would be unscannable */}
            <img src={qrSrc} alt="QR code of the room link"
                 width={220} height={220}
                 style={{ background: "#fff", padding: 8, imageRendering: "pixelated" }} />
            <div className="lcd" style={{ fontSize: 12, overflowWrap: "anywhere",
                     display: "inline-block", maxWidth: "100%", marginTop: 8 }}>
              {roomUrl}
            </div>
            <p className="dim small" style={{ marginTop: 8 }}>
              the room is the link — whoever scans it joins anonymously
            </p>
            <button className="bevel" onClick={() => setQrOpen(false)}>CLOSE</button>
          </div>
        </div>
      )}
      <LiveChat hash={hash} nick={nick} active={phase === "room"} />
      <section style={{ textAlign: "center" }}>
        <Link to="/" className="bevel">◄ LEAVE THE ROOM</Link>
      </section>
    </main>
  );
}
