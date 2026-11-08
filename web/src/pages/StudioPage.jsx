import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Masthead } from "./HomePage";
import { ThemeSwitch } from "../theme";
import {
  LiveSource,
  createLiveSession,
  endLiveSession,
  saveAsShout,
} from "../live";

export default function StudioPage() {
  const [hours, setHours] = useState(1);
  const [cap, setCap] = useState("");          // "" = unlimited
  const [phase, setPhase] = useState("idle"); // idle|live|ended|saved
  const [listenerUrl, setListenerUrl] = useState("");
  const [seq, setSeq] = useState(0);
  const [savedUrl, setSavedUrl] = useState("");
  const [err, setErr] = useState("");
  const srcRef = useRef(null);
  const sessRef = useRef(null);
  const [copied, setCopied] = useState(false);

  async function goLive() {
    setErr("");
    try {
      const s = await createLiveSession(hours, cap === "" ? null : parseInt(cap, 10));
      sessRef.current = s;
      const source = new LiveSource(s.session_hash, s.token);
      srcRef.current = source;
      await source.start(setSeq);
      setListenerUrl(location.origin + s.listener_url);
      setPhase("live");
    } catch (e) {
      setErr(e.message);
    }
  }

  async function endLive() {
    srcRef.current?.stop();
    const s = sessRef.current;
    if (s) await endLiveSession(s.session_hash, s.token);
    setPhase("ended");
  }

  async function save() {
    const s = sessRef.current;
    try {
      const url = await saveAsShout(s.session_hash, s.token, 5, 1440);
      setSavedUrl(url);
      setPhase("saved");
    } catch (e) {
      setErr(e.message);
    }
  }

  async function copy() {
    try { await navigator.clipboard.writeText(listenerUrl); }
    catch {
      const ta = document.createElement("textarea");
      ta.value = listenerUrl; document.body.appendChild(ta);
      ta.select(); document.execCommand("copy"); ta.remove();
    }
    setCopied(true); setTimeout(() => setCopied(false), 1600);
  }

  if (phase === "live" || phase === "ended" || phase === "saved") {
    return (
      <main>
        <Masthead />
        <section style={{ textAlign: "center" }}>
          {phase === "live" && (
            <>
              <span className="chip live"><span className="lamp blink" /> ON AIR</span>
              <h1 style={{ fontFamily: "var(--display-font)", margin: "12px 0" }}>
                YOU ARE LIVE
              </h1>
              <p className="lcd" style={{ display: "inline-block" }}>
                CHUNKS SENT: <span className="counter">{seq}</span>
              </p>
            </>
          )}
          {phase === "ended" && (
            <h1 style={{ fontFamily: "var(--display-font)" }}>TAPE STOPPED</h1>
          )}
          {phase === "saved" && (
            <>
              <h1 style={{ fontFamily: "var(--display-font)" }}>SAVED AS SHOUT</h1>
              <p className="dim">the session became a normal audio shout (5 views / 24h fuse)</p>
              <div className="lcd" style={{ display: "inline-block", maxWidth: "100%",
                        overflowWrap: "anywhere", margin: "10px 0" }}>
                {location.origin + savedUrl}
              </div>
            </>
          )}
        </section>

        {phase !== "saved" && (
          <section className="panel" style={{ textAlign: "center" }}>
            <div className="sec-label">LISTENER LINK — SHARE IT</div>
            <div className="lcd" style={{ display: "inline-block", maxWidth: "100%",
                     overflowWrap: "anywhere", textAlign: "left", margin: "10px 0" }}>
              {listenerUrl}
            </div>
            <div>
              <button className="bevel" onClick={copy} aria-pressed={copied}>
                {copied ? "COPIED!" : "COPY THE LINK"}
              </button>
            </div>
            <p className="dim small" style={{ marginTop: 8 }}>
              anyone with this link joins anonymously — nothing is recorded unless you save
            </p>
          </section>
        )}

        <section style={{ textAlign: "center" }}>
          {phase === "live" && (
            <button className="bevel primary" onClick={endLive}>■ END THE SESSION</button>
          )}
          {phase === "live" && (
            <p className="dim small" style={{ marginTop: 10 }}>
              auto-end 30s after you stop pushing — keep this tab open while live
            </p>
          )}
          {phase === "ended" && (
            <>
              <p className="dim" style={{ marginBottom: 10 }}>
                save the buffered audio as a normal shout, or let it burn forever?
                (minor glitches possible near chunk boundaries)
              </p>
              <button className="bevel primary" onClick={save}>💾 SAVE AS SHOUT</button>{" "}
              <Link to="/" className="bevel">LET IT BURN ►</Link>
            </>
          )}
          {phase === "saved" && <Link to="/" className="bevel">BACK TO STUDIO</Link>}
        </section>
      </main>
    );
  }

  return (
    <main>
      <Masthead />
      <section>
        <div className="sec-label">NEW LIVE SESSION</div>
        <h1 style={{ fontSize: "clamp(24px,6vw,40px)" }}>GO LIVE · RADIO PUPPA</h1>
        <p className="dim">anonymous live audio from your browser — listeners join with a link</p>
      </section>

      <section className="panel" style={{ display: "flex", gap: 22, flexWrap: "wrap" }}>
        <div>
          <div className="sec-label">TAPE LENGTH (HOURS)</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
            <button className="bevel" style={{ padding: "10px 14px" }}
                    onClick={() => setHours(Math.max(1, hours - 1))}>−</button>
            <span className="lcd"><span className="counter">{hours}</span> H</span>
            <button className="bevel" style={{ padding: "10px 14px" }}
                    onClick={() => setHours(Math.min(24, hours + 1))}>+</button>
          </div>
          <p className="dim small" style={{ marginTop: 6 }}>max 24h · auto-end 30s after you stop</p>
        </div>
        <div>
          <div className="sec-label">LISTENER CAP (BLANK = UNLIMITED)</div>
          <input type="text" inputMode="numeric" value={cap} style={{ width: 120, marginTop: 6 }}
                 onChange={(e) => setCap(e.target.value.replace(/[^0-9]/g, "").slice(0, 5))}
                 placeholder="∞" />
          <p className="dim small" style={{ marginTop: 6 }}>the radio's max_hits</p>
        </div>
      </section>

      <section style={{ textAlign: "center" }}>
        <button className="bevel primary" style={{ fontSize: 16 }} onClick={goLive}>
          ● GO LIVE
        </button>
        <p className="dim small" style={{ marginTop: 8 }}>
          the browser will ask for your microphone — your voice streams to listeners only
        </p>
        {err && <p style={{ color: "var(--red)" }}>⚠ {err}</p>}
      </section>
    </main>
  );
}
