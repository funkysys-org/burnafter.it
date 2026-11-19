import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import qrcode from "qrcode-generator";
import { Masthead } from "./HomePage";
import ShareButton from "../ShareButton";

export default function ChatPage() {
  const [roomUrl, setRoomUrl] = useState("");
  const [roomErr, setRoomErr] = useState("");
  const [busy, setBusy] = useState(false);
  // SCATOLA A OROLOGERIA for the room (radio/call excluded by design)
  const [timelock, setTimelock] = useState(false);
  const [openAt, setOpenAt] = useState("");

  const qrSrc = useMemo(() => {
    if (!roomUrl) return "";
    const qr = qrcode(0, "M");
    qr.addData(roomUrl);
    qr.make();
    return qr.createDataURL(4, 4);
  }, [roomUrl]);

  async function makeRoom() {
    setRoomErr("");
    setBusy(true);
    try {
      const r = await fetch("/live", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "chat", maxhours: 4, cap: null,
          ...(timelock && openAt ? { open_at: new Date(openAt).toISOString() } : {}),
        }),
      });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "room failed");
      const j = await r.json();
      setRoomUrl(location.origin + j.listener_url);
    } catch (e) {
      setRoomErr(e.message);
    } finally {
      setBusy(false);
    }
  }


  return (
    <main>
      <Masthead />
      <section style={{ textAlign: "center", padding: "30px 0" }}>
        <div className="sec-label">ESC · EPHEMERAL SECURE CHAT</div>
        <h1 style={{ fontSize: "clamp(24px,6vw,40px)" }}>CHAT ROOM</h1>
        <p className="dim">anonymous room — everyone with the link is in</p>
      </section>

      <section className="panel" style={{ textAlign: "center" }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap",
                     justifyContent: "center", alignItems: "center" }}>
          <button className="bevel" aria-pressed={timelock}
                  style={{ minHeight: 44, padding: "8px 14px", fontSize: 12,
                           background: timelock ? "var(--blue)" : undefined,
                           color: timelock ? "var(--panel)" : undefined }}
                  onClick={() => setTimelock(!timelock)}>
            {timelock ? "🔐 SEALED ROOM — ON" : "📦 SEALED ROOM — OFF"}
          </button>
          {timelock && (
            <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
              <input type="datetime-local" value={openAt}
                     onChange={(e) => setOpenAt(e.target.value)}
                     style={{ minHeight: 44 }} />
              <button className="bevel" style={{ minHeight: 44, padding: "8px 12px", fontSize: 11 }}
                      onClick={() => setOpenAt(new Date(Date.now() + 3600e3).toJSON().slice(0, 16))}>+1h</button>
              <button className="bevel" style={{ minHeight: 44, padding: "8px 12px", fontSize: 11 }}
                      onClick={() => setOpenAt(new Date(Date.now() + 24 * 3600e3).toJSON().slice(0, 16))}>+24h</button>
              <button className="bevel" style={{ minHeight: 44, padding: "8px 12px", fontSize: 11 }}
                      onClick={() => setOpenAt(new Date(Date.now() + 7 * 24 * 3600e3).toJSON().slice(0, 16))}>+7d</button>
            </span>
          )}
        </div>
        {timelock && (
          <p className="dim small" style={{ marginTop: 8 }}>
            the room opens at that moment — until then the link shows the
            countdown and refuses every message. the fuse starts at opening.
          </p>
        )}
        {roomUrl ? (
          <>
            <div className="sec-label">ROOM LINK — SHARE IT</div>
            <div className="lcd" style={{ display: "inline-block", maxWidth: "100%",
                     overflowWrap: "anywhere", textAlign: "left", margin: "10px 0" }}>
              {roomUrl}
            </div>
            <div>
              <ShareButton url={roomUrl} title="ESC — ephemeral chat room" />{" "}
              <a className="bevel" href={roomUrl}>► ENTER THE ROOM</a>
            </div>
            {qrSrc && (
              <div style={{ margin: "14px 0" }}>
                <img src={qrSrc} alt="QR code of the room link"
                     width={220} height={220} />
                <p className="dim small">scan it, share it, wave it goodbye</p>
              </div>
            )}
            <p className="dim small" style={{ marginTop: 8 }}>
              burns in 4h · no accounts · nothing recorded · messages die with the room
            </p>
          </>
        ) : (
          <>
            <button className="bevel primary" style={{ fontSize: 16 }}
                    onClick={makeRoom} disabled={busy}>
              {busy ? "MAKING THE ROOM…" : "💬 CREATE A CHAT ROOM"}
            </button>
            <p className="dim small" style={{ marginTop: 10 }}>
              got a room link? just open it — that's the whole login
            </p>
          </>
        )}
        {roomErr && <p style={{ color: "var(--red)", marginTop: 8 }}>⚠ {roomErr}</p>}
      </section>

      <section style={{ textAlign: "center" }}>
        <Link to="/" className="bevel">◄ BACK HOME</Link>
      </section>
    </main>
  );
}
