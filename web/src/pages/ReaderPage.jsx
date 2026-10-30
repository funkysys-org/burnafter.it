import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { reduced } from "./HomePage";
import {
  autoBurnFor,
  remainingSeconds,
} from "../autoburn";

function fmtLeft(iso) {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "00:00";
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

function BurnedScreen({ meta }) {
  return (
    <main style={{ textAlign: "center", padding: "60px 0" }}>
      <div style={{ fontSize: 64 }}>🔥</div>
      <h1 className="big" style={{ color: "var(--red)" }}>BURNED!</h1>
      <p style={{ margin: "10px 0" }}>shout expired or already seen!</p>
      <p className="dim" style={{ marginBottom: 6 }}>
        {meta
          ? "…ask the sender to shout again — fresh link, fresh fuse."
          : "No counter, no undo — just ash."}
      </p>
      <Link to="/create" className="bevel primary">CREATE YOUR OWN SHOUT ►</Link>
    </main>
  );
}

export default function ReaderPage() {
  const { type, hash } = useParams();
  const [phase, setPhase] = useState("gate"); // gate|confirming|reveal|burning|burned|fetcherr
  const [meta, setMeta] = useState(null);
  const [contentUrl, setContentUrl] = useState("");
  const [textContent, setTextContent] = useState("");
  const [left, setLeft] = useState("");
  const [auto, setAuto] = useState(8);          // countdown shown in the LCD
  const [fuse, setFuse] = useState(null);        // null = manual-only
  const burnedRef = useRef(false);
  const mediaRef = useRef(null);                 // <audio>/<video> element

  // feature-detect the non-consuming metadata endpoint (spec §6)
  useEffect(() => {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 800);
    fetch(`/meta/${type}/${hash}`, { signal: ctl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((j) => { setMeta(j); setLeft(fmtLeft(j.expires_at)); })
      .catch(() => setMeta(null));
    return () => { clearTimeout(t); ctl.abort(); };
  }, [type, hash]);

  // TTL ticker (meta mode only)
  useEffect(() => {
    if (!meta || phase !== "reveal") return;
    const iv = setInterval(() => setLeft(fmtLeft(meta.expires_at)), 1000);
    return () => clearInterval(iv);
  }, [meta, phase]);

  async function openIt() {
    setPhase("confirming");
    try {
      const r = await fetch(`/stream_any/${type}/${hash}`);
      if (r.status === 404) {
        setPhase("burned");
        return;
      }
      if (!r.ok) throw new Error("bad status " + r.status);
      // the fetch WAS the claim — the content is in this response body
      const blob = await r.blob();
      if (type === "text") setTextContent(await blob.text());
      else setContentUrl(URL.createObjectURL(blob));
      setPhase("reveal");
    } catch {
      setPhase("fetcherr");
    }
  }

  function burn() {
    if (burnedRef.current) return;
    burnedRef.current = true;
    setPhase("burning");
    setTimeout(() => {
      if (contentUrl) URL.revokeObjectURL(contentUrl);
      setPhase("burned");
    }, reduced() ? 50 : 1500);
  }

  // auto-burn fuse (maintainer-locked policy):
  //   text/photo -> fixed 8s wall-clock countdown
  //   audio/video -> PLAYBACK-LINKED: duration + 5s; pausing the player
  //                 pauses the fuse; unreadable duration -> manual-only
  useEffect(() => {
    if (phase !== "reveal" || reduced()) return;
    if (type === "audio" || type === "video") {
      setFuse("media");          // fuse value set on metadata load
      setAuto(null);             // hidden until duration is known
      return;                    // ticking handled by onTimeUpdate
    }
    const f = autoBurnFor(type, null);
    setFuse("static");
    setAuto(f);
    const iv = setInterval(() => setAuto((n) => {
      if (n <= 1) { clearInterval(iv); burn(); return 0; }
      return n - 1;
    }), 1000);
    return () => clearInterval(iv);
  }, [phase]); // eslint-disable-line react-hooks/exhaustive-deps

  function onMediaMeta(e) {
    const d = e.target.duration;
    const f = autoBurnFor(type, isFinite(d) ? d : null);
    if (f === null) { setFuse(null); setAuto(null); return; } // manual-only
    setAuto(remainingSeconds(isFinite(d) ? d : 0, 0) ?? f);
  }

  function onMediaTime(e) {
    const el = e.target;
    if (!isFinite(el.duration) || el.duration <= 0) return;
    const r = remainingSeconds(el.duration, el.currentTime);
    setAuto(r);
    if (r === 0) burn();
  }

  if (phase === "burned") return <BurnedScreen meta={meta} />;

  if (phase === "fetcherr") {
    return (
      <main style={{ textAlign: "center", padding: "60px 0" }}>
        <div style={{ fontSize: 64 }}>⚠</div>
        <h1 style={{ fontFamily: "'Silkscreen', monospace" }}>
          STATIC ON THE DIAL
        </h1>
        <p className="dim" style={{ margin: "12px 0", maxWidth: 460 }}>
          we couldn't reach the server. If the request landed, this play
          may have counted; trying again might burn another view.
          Your call.
        </p>
        <button className="bevel" onClick={() => setPhase("gate")}>TRY AGAIN</button>{" "}
        <Link to="/" className="bevel">BACK TO STUDIO</Link>
      </main>
    );
  }

  if (phase === "gate" || phase === "confirming") {
    return (
      <main style={{ textAlign: "center", padding: "60px 0" }}>
        <div style={{ fontSize: 64 }}>📻</div>
        <h1 style={{ fontFamily: "'Silkscreen', monospace" }}>
          THIS MESSAGE WILL SELF-DESTRUCT
        </h1>
        <p className="dim" style={{ margin: "12px 0" }}>
          {meta
            ? `Opening burns 1 of ${meta.views_left} views · tape expires in ${left}.`
            : "Opening this link might be the last play. No counter, no clock — the link is all there is."}
        </p>
        <button className="bevel primary" style={{ fontSize: 15 }}
                disabled={phase === "confirming"} onClick={openIt}>
          {phase === "confirming" ? "PLAYING…" :
           meta ? "► OPEN & PLAY (BURNS 1 VIEW)" : "► OPEN IT — BURN IT"}
        </button>
        <p className="dim small" style={{ marginTop: 10 }}>
          the play IS the burn — no takebacks
        </p>
      </main>
    );
  }

  // reveal / burning
  const burning = phase === "burning";
  return (
    <main style={{ textAlign: "center" }}>
      {meta && (
        <div style={{ display: "flex", gap: 8, justifyContent: "center",
                      margin: "14px 0", flexWrap: "wrap" }}>
          <span className="chip live"><span className="lamp blink" /> ON AIR — PLAYING</span>
          <span className="chip ok">{meta.views_left - 1} OF {meta.max_hits} PLAYS LEFT</span>
          <span className="chip neutral">BURNS IN {left}</span>
        </div>
      )}
      <div className="panel" style={{
        filter: burning
          ? "contrast(2) brightness(.12) saturate(0)" : undefined,
        opacity: burning ? 0.2 : 1,
        transition: reduced() ? "none" : "filter 1.5s steps(6), opacity 1.5s steps(6)",
        padding: "22px", maxWidth: 720, margin: "0 auto" }}>
        <div className="sec-label">FROM: SOMEONE WHO WANTED THIS SEEN ONCE</div>
        <div style={{ margin: "16px 0" }}>
          {type === "text" ? (
            <span className="lcd" style={{ fontSize: 24, padding: "12px 14px",
                    display: "inline-block", maxWidth: "100%", whiteSpace: "pre-wrap",
                    textAlign: "left", overflowWrap: "anywhere" }}>
              {textContent}
            </span>
          ) : type === "photo" ? (
            <img src={contentUrl} alt="the shout" style={{ maxWidth: "100%" }} />
          ) : type === "audio" ? (
            <audio ref={mediaRef} controls src={contentUrl}
                   style={{ width: "100%" }}
                   onLoadedMetadata={onMediaMeta}
                   onTimeUpdate={onMediaTime} />
          ) : (
            <video ref={mediaRef} controls src={contentUrl}
                   style={{ maxWidth: "100%" }}
                   onLoadedMetadata={onMediaMeta}
                   onTimeUpdate={onMediaTime} />
          )}
        </div>
        <p className="dim small">
          THIS IS THE ONLY PLAY. Close the tab and it lives only in your head.
        </p>
      </div>
      {!burning && (
        <div style={{ margin: "18px 0", display: "flex", gap: 10,
                      justifyContent: "center", alignItems: "center", flexWrap: "wrap" }}>
          <button className="bevel" onClick={burn}>🔥 BURN IT NOW</button>
          {!reduced() && fuse !== null && auto !== null && (
            <span className="lcd" style={{ fontSize: 14 }}>
              {fuse === "media"
                ? `AUTO-BURN WITH PLAYBACK · ${auto}s LEFT`
                : `AUTO-BURN IN ${auto}s`}
            </span>
          )}
          {!reduced() && fuse === null && (
            <span className="lcd" style={{ fontSize: 14 }}>
              MANUAL BURN ONLY — NO TIMER ON THIS TAPE
            </span>
          )}
        </div>
      )}
    </main>
  );
}
