import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import qrcode from "qrcode-generator";
import { Masthead } from "./HomePage";
import AlfaBanner from "../AlfaBanner";
import { ThemeSwitch } from "../theme";
import LiveChat from "../LiveChat";
import {
  LiveSource,
  createLiveSession,
  endLiveSession,
  saveAsShout,
  listInputDevices,
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
  // Tier A: input device + tape type (persisted; labels need a granted
  // mic once — the browser rule, noted in the UI not hidden)
  const [devices, setDevices] = useState([]);
  const [deviceId, setDeviceId] = useState(() => {
    try { return localStorage.getItem("bai-input") || ""; } catch { return ""; }
  });
  const [music, setMusic] = useState(() => {
    try { return localStorage.getItem("bai-music") === "1"; } catch { return false; }
  });
  const [deviceGone, setDeviceGone] = useState(false);

  const listenerQr = useMemo(() => {
    if (!listenerUrl) return "";
    const qr = qrcode(0, "M");
    qr.addData(listenerUrl);
    qr.make();
    return qr.createDataURL(4, 4);
  }, [listenerUrl]);

  const savedQr = useMemo(() => {
    if (!savedUrl) return "";
    const qr = qrcode(0, "M");
    qr.addData(location.origin + savedUrl);
    qr.make();
    return qr.createDataURL(4, 4);
  }, [savedUrl]);

  useEffect(() => {
    listInputDevices().then(setDevices).catch(() => {});
    if (navigator.mediaDevices?.addEventListener) {
      const refresh = () => listInputDevices().then(setDevices).catch(() => {});
      navigator.mediaDevices.addEventListener("devicechange", refresh);
      return () => navigator.mediaDevices.removeEventListener("devicechange", refresh);
    }
  }, []);

  useEffect(() => {
    try { localStorage.setItem("bai-input", deviceId); } catch {}
  }, [deviceId]);
  useEffect(() => {
    try { localStorage.setItem("bai-music", music ? "1" : "0"); } catch {}
  }, [music]);

  async function goLive() {
    setErr("");
    setDeviceGone(false);
    try {
      const s = await createLiveSession(hours, cap === "" ? null : parseInt(cap, 10));
      sessRef.current = s;
      const source = new LiveSource(s.session_hash, s.token, {
        deviceId: deviceId || null,
        music,
      });
      srcRef.current = source;
      await source.start(setSeq);
      if (source.deviceGone) setDeviceGone(true);
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


  if (phase === "live" || phase === "ended" || phase === "saved") {
    return (
      <main>
        <Masthead />
        <AlfaBanner />
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
              {deviceGone && (
                <p className="dim small" style={{ color: "var(--red)" }}>
                  ⚠ chosen input device was unavailable — fell back to the
                  default microphone. Re-pick before the next session.
                </p>
              )}
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
              {savedQr && (
                <div style={{ margin: "10px 0" }}>
                  <img src={savedQr} alt="QR code of the saved shout"
                       width={220} height={220} />
                  <p className="dim small">the session survived — scan to listen</p>
                </div>
              )}
            </>
          )}
        </section>

        {phase === "live" && (
          <LiveChat hash={sessRef.current.session_hash} nick="HOST" active={phase === "live"} />
        )}

        {phase !== "saved" && (
          <section className="panel" style={{ textAlign: "center" }}>
            <div className="sec-label">LISTENER LINK — SHARE IT</div>
            <div className="lcd" style={{ display: "inline-block", maxWidth: "100%",
                     overflowWrap: "anywhere", textAlign: "left", margin: "10px 0" }}>
              {listenerUrl}
            </div>
            <div>
              <ShareButton url={listenerUrl} title="Radio Puppa — live session" />
            </div>
            {listenerQr && (
              <div style={{ margin: "14px 0" }}>
                <img src={listenerQr} alt="QR code of the listener link"
                     width={220} height={220} />
                <p className="dim small">scan it, share it — the room takes everyone</p>
              </div>
            )}
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
        <AlfaBanner />
      <section>
        <div className="sec-label">NEW LIVE SESSION</div>
        <h1 style={{ fontSize: "clamp(24px,6vw,40px)" }}>GO LIVE · RADIO PUPPA</h1>
        <p className="dim">anonymous live audio from your browser — listeners join with a link</p>
      </section>

      <section className="panel" style={{ display: "flex", gap: 22, flexWrap: "wrap" }}>
        <div>
          <div className="sec-label">INPUT DEVICE</div>
          <select value={deviceId}
                  onChange={(e) => setDeviceId(e.target.value)}
                  style={{ marginTop: 6, minWidth: 220, fontSize: 12,
                           padding: "8px 6px",
                           background: "var(--lcd-bg)", color: "var(--lcd-ink)",
                           border: "2px solid var(--border)",
                           borderRadius: "var(--r-ctl)" }}>
            <option value="">» default microphone</option>
            {devices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>{d.label}</option>
            ))}
          </select>
          <p className="dim small" style={{ marginTop: 6 }}>
            usb mixers, interfaces and virtual cables appear here
            (labels show after the first mic grant — browser rule)
          </p>
        </div>
        <div>
          <div className="sec-label">TAPE TYPE</div>
          <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
            <button className="bevel" aria-pressed={!music}
                    style={{ minHeight: 44, padding: "8px 12px", fontSize: 11,
                             background: !music ? "var(--green)" : undefined,
                             color: !music ? "var(--panel)" : undefined }}
                    onClick={() => setMusic(false)}>🎙 VOICE</button>
            <button className="bevel" aria-pressed={music}
                    style={{ minHeight: 44, padding: "8px 12px", fontSize: 11,
                             background: music ? "var(--green)" : undefined,
                             color: music ? "var(--panel)" : undefined }}
                    onClick={() => setMusic(true)}>🎵 MUSIC</button>
          </div>
          <p className="dim small" style={{ marginTop: 6 }}>
            voice: processing on, 32kbps · music: raw input, 128kbps
            (the voice DSP mangles music)
          </p>
        </div>
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
