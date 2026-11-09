import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { reduced, Masthead } from "./HomePage";
import LiveChat from "../LiveChat";

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
  const [nick] = useState(() => "Listener-" + String(Math.floor(1000 + Math.random() * 9000)));

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
        {meta && <span className="chip neutral">BURNS IN {fuse}</span>}
      </section>
      <LiveChat hash={hash} nick={nick} active={phase === "room"} />
      <section style={{ textAlign: "center" }}>
        <Link to="/" className="bevel">◄ LEAVE THE ROOM</Link>
      </section>
    </main>
  );
}
