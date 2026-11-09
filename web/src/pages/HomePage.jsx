import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ThemeSwitch } from "../theme";

export const reduced = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

export function Masthead() {
  return (
    <header style={{ display: "flex", justifyContent: "space-between",
                     alignItems: "center", flexWrap: "wrap", gap: 8 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center",
                    flexWrap: "wrap" }}>
        <Link to="/" className="big"
              style={{ fontSize: "clamp(20px,5vw,30px)",
                       textDecoration: "none", color: "inherit" }}>
          burnafter·it
        </Link>
        <nav style={{ display: "inline-flex", gap: 6, flexWrap: "wrap" }}>
          <Link to="/create" className="bevel"
                style={{ fontSize: 10, padding: "8px 10px", minHeight: 0 }}>
            ► SHOUT
          </Link>
          <Link to="/studio" className="bevel"
                style={{ fontSize: 10, padding: "8px 10px", minHeight: 0 }}>
            ● GO LIVE
          </Link>
        </nav>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center",
                    flexWrap: "wrap" }}>
        <ThemeSwitch />
        <span className="chip live">
          <span className="lamp blink" /> ON AIR SINCE 2006
        </span>
      </div>
    </header>
  );
}

function Step({ n, title, children }) {
  return (
    <div className="panel" style={{ flex: "1 1 240px" }}>
      <div className="sec-label">STEP {n}</div>
      <h2 style={{ fontFamily: "'Silkscreen', monospace", fontSize: 15,
                   margin: "6px 0" }}>{title}</h2>
      <p className="dim small">{children}</p>
    </div>
  );
}

function StatBox({ value, label, note }) {
  return (
    <div className="panel" style={{ flex: "1 1 150px", textAlign: "center",
                                    padding: "14px 10px" }}>
      <div className="lcd" style={{ display: "inline-block" }}>
        <span className="counter">{value}</span>
      </div>
      <div className="sec-label" style={{ marginTop: 8 }}>{label}</div>
      {note && <div className="dim" style={{ fontSize: 10 }}>{note}</div>}
    </div>
  );
}

function StatsStrip() {
  const [liveNow, setLiveNow] = useState(null);
  const [chatNow, setChatNow] = useState(null);
  useEffect(() => {
    fetch("/live/stats")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((j) => { setLiveNow(j.live_now); setChatNow(j.chat_now); })
      .catch(() => {});
  }, []);
  return (
    <section>
      <div className="sec-label">ON THE WIRE</div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 10 }}>
        <StatBox value={liveNow ?? "—"} label="ON AIR NOW" note="real, live" />
        <StatBox value={chatNow ?? "—"} label="CHAT ROOMS OPEN" note="real, live" />
        <StatBox value="∞" label="SHOUTS BURNED" note="unknowable by design" />
        <StatBox value="0" label="MESSAGES STORED FOREVER" note="we keep nothing" />
      </div>
      <p className="dim small" style={{ marginTop: 8 }}>
        two of these are live counters; two are the honest truth —
        we can't count burned shouts BECAUSE they're gone, and we store
        nothing forever because nothing exists to store. capito?
      </p>
    </section>
  );
}

export default function HomePage() {
  const [roomUrl, setRoomUrl] = useState("");
  const [roomErr, setRoomErr] = useState("");

  async function makeRoom() {
    setRoomErr("");
    try {
      const r = await fetch("/live", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "chat", maxhours: 4, cap: null }),
      });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "room failed");
      const j = await r.json();
      setRoomUrl(location.origin + j.listener_url);
    } catch (e) {
      setRoomErr(e.message);
    }
  }

  return (
    <main>
      <Masthead />
      <section style={{ textAlign: "center", padding: "40px 0" }}>
        <h1>
          SHOUT IT ONCE.<br />
          <span style={{ color: "var(--headline-accent)" }}>THEN IT BURNS.</span>
        </h1>
        <p className="dim" style={{ margin: "14px 0 22px" }}>
          no accounts · no tracking · links die on purpose — capito?
        </p>
        <Link to="/create" className="bevel primary" style={{ fontSize: 16 }}>
          ► SHARE EPHEMERAL CONTENT
        </Link>{" "}
        <Link to="/studio" className="bevel" style={{ fontSize: 16 }}>
          ● GO LIVE
        </Link>{" "}
        <button className="bevel" style={{ fontSize: 16 }} onClick={makeRoom}>
          💬 CHAT ROOM
        </button>
        {roomUrl && (
          <div className="panel" style={{ marginTop: 18, textAlign: "center" }}>
            <div className="sec-label">ROOM LINK — SHARE IT</div>
            <div className="lcd" style={{ display: "inline-block", maxWidth: "100%",
                     overflowWrap: "anywhere", textAlign: "left", margin: "10px 0" }}>
              {roomUrl}
            </div>
            <p className="dim small">
              anonymous room · burns in 4h · everyone with the link is in
            </p>
          </div>
        )}
        {roomErr && <p style={{ color: "var(--red)", marginTop: 10 }}>⚠ {roomErr}</p>}
      </section>

      <StatsStrip />

      <section>
        <div className="sec-label">HOW IT WORKS</div>
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap",
                      marginTop: 10 }}>
          <Step n="1" title="SHOUT IT">
            Text, photo, audio or video. Pick the fuse: N views or T
            minutes — whichever runs out first burns the tape.
          </Step>
          <Step n="2" title="SHARE THE LINK">
            You get one secret URL and its QR. No resend, no backup:
            the link you get is the only key.
          </Step>
          <Step n="3" title="IT BURNS">
            The play IS the burn — no takebacks. When the fuse runs
            out, all that's left is ash and a "Burned!".
          </Step>
        </div>
      </section>

      <section>
        <div className="panel" style={{ transform: "rotate(-.6deg)" }}>
          <div className="sec-label">THE FINE PRINT · HONESTLY</div>
          <p style={{ marginTop: 8 }}>
            THINGS WE CANNOT DO FOR YOU: recover a lost link, un-burn a
            shout, resend it, read it ourselves, or know it ever existed.
            There is no database of your stuff — there's barely a
            database at all. Ephemeral means ephemeral, capito?
          </p>
          <p className="dim small" style={{ marginTop: 8 }}>
            limits: text ≤ 10 KB · photo ≤ 5 MB · audio ≤ 25 MB ·
            video ≤ 50 MB · views 1–100 · lifetime 1 min – 24 h ·
            default fuse 4 h
          </p>
        </div>
      </section>

      <footer className="dim small" style={{ padding: "20px 0",
                 borderTop: "2px solid var(--ink)" }}>
        burnafter.it — revived 2026 · a 2006 hobby radio app that grew
        up · puppa-powered
      </footer>
    </main>
  );
}
