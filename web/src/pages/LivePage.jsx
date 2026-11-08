import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { reduced, Masthead } from "./HomePage";
import { LivePlayer } from "../live";

function fmtFuse(iso) {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "00:00";
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export default function LivePage() {
  const { hash } = useParams();
  const [phase, setPhase] = useState("gate"); // gate|onair|burned|full|error
  const [meta, setMeta] = useState(null);
  const [fuse, setFuse] = useState("");
  const [nick] = useState(() => "Listener-" + String(Math.floor(1000 + Math.random() * 9000)));
  const [msgs, setMsgs] = useState([]);
  const [draft, setDraft] = useState("");
  const audioRef = useRef(null);
  const playerRef = useRef(null);
  const lastIdRef = useRef(0);

  useEffect(() => {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 800);
    fetch(`/live/${hash}/meta`, { signal: ctl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("burned"))))
      .then((j) => { setMeta(j); setFuse(fmtFuse(j.expires_at)); })
      .catch(() => setMeta(null));
    return () => { clearTimeout(t); ctl.abort(); };
  }, [hash]);

  useEffect(() => {
    if (!meta || phase !== "onair") return;
    const iv = setInterval(() => setFuse(fmtFuse(meta.expires_at)), 1000);
    return () => clearInterval(iv);
  }, [meta, phase]);

  async function join() {
    const jr = await fetch(`/live/${hash}/join`);
    if (jr.status === 409) { setPhase("full"); return; }
    if (jr.status === 404) { setPhase("burned"); return; }
    const seat = (await jr.json()).seat || "";
    setPhase("onair");
    setTimeout(async () => {
      const p = new LivePlayer(hash, audioRef.current, seat);
      p.onEnded = () => setPhase("burned");
      p.onUnsupported = () => setPhase("unsupported");  // honest degrade
      playerRef.current = p;
      p.start();
      const tick = setInterval(async () => {
        if (phase !== "onair") { clearInterval(tick); return; }
        try {
          const r = await fetch(`/live/${hash}/chat?after=${lastIdRef.current}`);
          if (r.status === 404) { clearInterval(tick); setPhase("burned"); return; }
          if (!r.ok) return;
          const j = await r.json();
          if (j.messages.length) {
            lastIdRef.current = j.messages[j.messages.length - 1].id;
            setMsgs((prev) => [...prev, ...j.messages].slice(-50));
          }
        } catch {}
      }, 2500);
    }, 100);
  }

  async function say(e) {
    e.preventDefault();
    if (!draft.trim()) return;
    const body = draft.trim();
    setDraft("");
    const r = await fetch(`/live/${hash}/say`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname: nick, body }),
    });
    if (r.status === 404) setPhase("burned");
  }

  if (phase === "burned") {
    return (
      <main style={{ textAlign: "center", padding: "60px 0" }}>
        <div style={{ fontSize: 64 }}>🔥</div>
        <h1 className="big" style={{ color: "var(--red)" }}>BURNED!</h1>
        <p style={{ margin: "10px 0" }}>this tape is over — the session is gone</p>
        <Link to="/" className="bevel">BACK TO STUDIO</Link>
      </main>
    );
  }

  if (phase === "full") {
    return (
      <main style={{ textAlign: "center", padding: "60px 0" }}>
        <div style={{ fontSize: 64 }}>📻</div>
        <h1 style={{ fontFamily: "var(--display-font)" }}>ALL SEATS TAKEN</h1>
        <p className="dim" style={{ margin: "12px 0" }}>
          the session is full — the tape has no seats left
        </p>
        <Link to="/" className="bevel">BACK TO STUDIO</Link>
      </main>
    );
  }

  if (phase === "unsupported") {
    return (
      <main style={{ textAlign: "center", padding: "60px 0" }}>
        <div style={{ fontSize: 64 }}>⚠</div>
        <h1 style={{ fontFamily: "var(--display-font)" }}>CAN'T TUNE IN</h1>
        <p className="dim" style={{ margin: "12px 0", maxWidth: 460 }}>
          this browser can't play the live stream — the chat below still
          works on a device that supports it. Sorry, puppa.
        </p>
        <Link to="/" className="bevel">BACK TO STUDIO</Link>
      </main>
    );
  }

  if (phase === "gate") {
    return (
      <main>
        <Masthead />
        <section style={{ textAlign: "center", padding: "40px 0" }}>
          <div style={{ fontSize: 64 }}>📻</div>
          <h1 style={{ fontFamily: "var(--display-font)" }}>ON AIR</h1>
          <p className="dim" style={{ margin: "12px 0" }}>
            {meta
              ? `Anonymous live session — nothing recorded. ${meta.cap ? `Seats: ${meta.listeners}/${meta.cap}` : "Unlimited seats"}.`
              : "Anonymous live session — join to listen. Nothing recorded."}
          </p>
          <button className="bevel primary" style={{ fontSize: 15 }} onClick={join}>
            ► JOIN THE SESSION (ANONYMOUS)
          </button>
          <p className="dim small" style={{ marginTop: 10 }}>
            no accounts · no tracking · when it ends, it burns
          </p>
        </section>
      </main>
    );
  }

  // onair
  return (
    <main>
      <Masthead />
      <section style={{ textAlign: "center" }}>
        <span className="chip live"><span className="lamp blink" /> ON AIR — LIVE</span>{" "}
        {meta && <span className="chip neutral">TAPE BURNS IN {fuse}</span>}{" "}
        {meta && <span className="chip ok">
          {meta.listeners}{meta.cap ? `/${meta.cap}` : ""} LISTENING
        </span>}
      </section>
      <section className="panel" style={{ textAlign: "center" }}>
        <audio ref={audioRef} controls autoPlay style={{ width: "100%" }} />
        <p className="dim small" style={{ marginTop: 8 }}>
          live edge is a few seconds behind — that's the radio way
        </p>
      </section>
      <section className="panel">
        <div className="sec-label">CHAT · {nick}</div>
        <div style={{ maxHeight: 240, overflowY: "auto", margin: "10px 0" }}>
          {msgs.map((m) => (
            <p key={m.id} style={{ overflowWrap: "anywhere" }}>
              <b>{m.nickname}</b> <span className="dim small">· {m.said_at.slice(11, 19)}Z</span><br />
              {m.body}
            </p>
          ))}
          {msgs.length === 0 && <p className="dim small">no messages yet — say hi…</p>}
        </div>
        <form onSubmit={say} style={{ display: "flex", gap: 8 }}>
          <input type="text" value={draft} maxLength={500}
                 onChange={(e) => setDraft(e.target.value)}
                 placeholder="say it to the room (≤ 500 chars)" />
          <button className="bevel" type="submit" disabled={!draft.trim()}>SAY</button>
        </form>
        <p className="dim small" style={{ marginTop: 6 }}>
          anonymous · nicknames cap at 32 chars · messages die with the session
        </p>
      </section>
    </main>
  );
}
