import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import qrcode from "qrcode-generator";
import { reduced, Masthead } from "./HomePage";
import ShareButton from "../ShareButton";
import { LiveSource, createLiveSession } from "../live";
import { LivePlayer } from "../live";

// SEC CALL — honest-poll v1 (~2-3s latency, walkie-talkie flavor).
// The link IS the ring: caller creates + shares, callee accepts.
// One tape: either hang-up burns it for both. No recording (v1).
export default function CallPage() {
  const { hash } = useParams();           // present = CALLEE (opened the link)
  const [phase, setPhase] = useState(
    hash ? "incoming" : "idle"
  ); // idle|ringing|incall|incoming|burned|ended
  const [err, setErr] = useState("");
  const [callUrl, setCallUrl] = useState("");
  const sessRef = useRef(null);           // { session_hash, token, role }
  const callerSrcRef = useRef(null);
  const calleeSrcRef = useRef(null);
  const otherAudioRef = useRef(null);
  const ringingTimerRef = useRef(null);

  const qrSrc = useMemo(() => {
    if (!callUrl) return "";
    const qr = qrcode(0, "M");
    qr.addData(callUrl);
    qr.make();
    return qr.createDataURL(4, 4);
  }, [callUrl]);

  async function startTalking(role, token, h) {
    // push MY voice to MY ring; play the OTHER's ring.
    // NO local playback by design: you never hear yourself (no echo
    // path at all) — the 'you' strip is a mic indicator, muted.
    const src = new LiveSource(h, token, { music: false }); // VOICE processing
    const source = role === "caller" ? callerSrcRef : calleeSrcRef;
    source.current = src;
    await src.start(() => {});
    const player = new LivePlayer(
      h, otherAudioRef.current,
      null, role === "caller" ? "B" : "A",  // poll the OTHER's ring
    );
    player.start();
  }


  async function createCall() {
    setErr("");
    try {
      const s = await createLiveSession(2, null, "call");
      sessRef.current = { ...s, role: "caller" };
      setCallUrl(location.origin + s.listener_url);
      setPhase("ringing");
      // poll for the callee's accept
      const h = s.session_hash;
      const poll = setInterval(async () => {
        try {
          const r = await fetch(`/live/${h}/ringing`);
          if (r.status === 404) { clearInterval(poll); setPhase("burned"); return; }
          if (!r.ok) return;
          const j = await r.json();
          if (j.accepted) {
            clearInterval(poll);
            setPhase("incall");
            await startTalking("caller", s.token, h);
          }
        } catch {}
      }, 2000);
      ringingTimerRef.current = poll;
    } catch (e) {
      setErr(e.message);
    }
  }

  async function accept() {
    const h = hash;
    try {
      const r = await fetch(`/live/${h}/accept`, { method: "POST" });
      if (r.status === 404) { setPhase("burned"); return; }
      if (!r.ok) throw new Error("accept failed");
      const j = await r.json();
      sessRef.current = { session_hash: h, token: j.token, role: "callee" };
      setPhase("incall");
      await startTalking("callee", j.token, h);
    } catch (e) {
      setErr(e.message);
    }
  }

  async function hangUp() {
    const s = sessRef.current;
    callerSrcRef.current?.stop();
    calleeSrcRef.current?.stop();
    if (s) {
      await fetch(`/live/${s.session_hash}/end?token=${encodeURIComponent(s.token)}`,
                  { method: "POST" }).catch(() => {});
    }
    setPhase("ended");
  }

  useEffect(() => () => {
    clearInterval(ringingTimerRef.current);
    callerSrcRef.current?.stop();
    calleeSrcRef.current?.stop();
  }, []);

  if (phase === "burned") {
    return (
      <main style={{ textAlign: "center", padding: "60px 0" }}>
        <div style={{ fontSize: 64 }}>🔥</div>
        <h1 className="big" style={{ color: "var(--red)" }}>BURNED!</h1>
        <p style={{ margin: "10px 0" }}>the call is over — the tape is gone</p>
        <Link to="/" className="bevel">BACK HOME</Link>
      </main>
    );
  }

  if (phase === "ended") {
    return (
      <main style={{ textAlign: "center", padding: "60px 0" }}>
        <div style={{ fontSize: 64 }}>📞</div>
        <h1 style={{ fontFamily: "var(--display-font)" }}>CALL ENDED</h1>
        <p className="dim" style={{ margin: "10px 0" }}>
          both sides burned — nothing was recorded, by design
        </p>
        <Link to="/" className="bevel">BACK HOME</Link>
      </main>
    );
  }

  if (phase === "incoming") {
    return (
      <main>
        <Masthead />
        <section style={{ textAlign: "center", padding: "40px 0" }}>
          <div style={{ fontSize: 64 }}>📞</div>
          <h1 style={{ fontFamily: "var(--display-font)" }}>
            INCOMING TAPE
          </h1>
          <p className="dim" style={{ margin: "12px 0" }}>
            someone who had this link wants to talk. anonymous call —
            nothing recorded, ~2-3s of radio-flavored latency.
          </p>
          <button className="bevel primary" style={{ fontSize: 15 }} onClick={accept}>
            ► ACCEPT THE CALL
          </button>
          <p className="dim small" style={{ marginTop: 10 }}>
            one tape: if either side hangs up, it burns for both
          </p>
          {err && <p style={{ color: "var(--red)" }}>⚠ {err}</p>}
        </section>
      </main>
    );
  }

  if (phase === "ringing") {
    return (
      <main>
        <Masthead />
        <section style={{ textAlign: "center", padding: "30px 0" }}>
          <span className="chip live"><span className="lamp blink" /> RINGING…</span>
          <p className="dim" style={{ margin: "14px 0" }}>
            share the call link — the call starts when they accept
          </p>
        </section>
        <section className="panel" style={{ textAlign: "center" }}>
          <div className="lcd" style={{ display: "inline-block", maxWidth: "100%",
                   overflowWrap: "anywhere", textAlign: "left", margin: "10px 0" }}>
            {callUrl}
          </div>
          <div style={{ margin: "12px 0" }}>
            <ShareButton url={callUrl} title="SEC CALL — the link is the ring" />
          </div>
          {qrSrc && (
            <div style={{ margin: "12px 0" }}>
              <img src={qrSrc} alt="QR code of the call link"
                   width={220} height={220} />
              <p className="dim small">the link is the ring — scan to answer</p>
            </div>
          )}
        </section>
        <section style={{ textAlign: "center" }}>
          <button className="bevel" onClick={() => { clearInterval(ringingTimerRef.current); setPhase("ended"); }}>
            ■ CANCEL
          </button>
        </section>
      </main>
    );
  }

  if (phase === "incall") {
    return (
      <main>
        <Masthead />
        <section style={{ textAlign: "center", padding: "20px 0" }}>
          <span className="chip live"><span className="lamp blink" /> ON THE TAPE</span>{" "}
          <span className="chip neutral">ANONYMOUS · NOTHING RECORDED</span>
        </section>
        <section className="panel" style={{ textAlign: "center" }}>
          <p className="dim small">them ▼</p>
          <audio ref={otherAudioRef} controls autoPlay style={{ width: "100%" }} />
          <p className="dim small" style={{ margin: "8px 0" }}>
            you ▼ <span className="chip ok" style={{ marginLeft: 6 }}>
              <span className="lamp blink" /> MIC LIVE · MUTED LOCALLY
            </span>
          </p>
          <div className="lcd" style={{ display: "inline-block", fontSize: 14 }}>
            YOUR VOICE GOES TO THE TAPE — NOT TO YOUR SPEAKERS
          </div>
        </section>
        <section style={{ textAlign: "center" }}>
          <button className="bevel primary" onClick={hangUp}>
            ■ HANG UP (BURNS FOR BOTH)
          </button>
        </section>
      </main>
    );
  }

  // idle: the CALL creation view (caller starts here)
  return (
    <main>
      <Masthead />
      <section style={{ textAlign: "center", padding: "30px 0" }}>
        <div className="sec-label">SEC · SECURE EPHEMERAL CALL</div>
        <h1 style={{ fontSize: "clamp(24px,6vw,40px)" }}>PHONE</h1>
        <p className="dim">anonymous call — the link is the ring</p>
      </section>
      <section className="panel" style={{ textAlign: "center" }}>
        <button className="bevel primary" style={{ fontSize: 16 }} onClick={createCall}>
          📞 START A CALL
        </button>
        <p className="dim small" style={{ marginTop: 10 }}>
          got a call link? just open it — that's answering
        </p>
        {err && <p style={{ color: "var(--red)", marginTop: 8 }}>⚠ {err}</p>}
      </section>
    </main>
  );
}
