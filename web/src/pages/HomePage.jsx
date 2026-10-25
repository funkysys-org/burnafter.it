import React from "react";
import { Link } from "react-router-dom";
import { ThemeSwitch } from "../theme";

export const reduced = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

export function Masthead() {
  return (
    <header style={{ display: "flex", justifyContent: "space-between",
                     alignItems: "center", flexWrap: "wrap", gap: 8 }}>
      <div className="big" style={{ fontSize: "clamp(20px,5vw,30px)" }}>
        burnafter·it
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

export default function HomePage() {
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
        </Link>
      </section>

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
