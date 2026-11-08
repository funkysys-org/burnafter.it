import React, { useEffect, useRef, useState } from "react";

// Shared live-session chat (listener page AND host studio page).
// Polls /live/<h>/chat; posts /say. Uses refs for the active flag —
// the closure-freeze lesson (the tick that died on its first fire).
export default function LiveChat({ hash, nick, active }) {
  const [msgs, setMsgs] = useState([]);
  const [draft, setDraft] = useState("");
  const lastIdRef = useRef(0);
  const activeRef = useRef(active);
  useEffect(() => { activeRef.current = active; }, [active]);

  useEffect(() => {
    if (!active) return;
    const tick = setInterval(async () => {
      if (!activeRef.current) { clearInterval(tick); return; }
      try {
        const r = await fetch(`/live/${hash}/chat?after=${lastIdRef.current}`);
        if (r.status === 404) { clearInterval(tick); return; } // tape over
        if (!r.ok) return;
        const j = await r.json();
        if (j.messages.length) {
          lastIdRef.current = j.messages[j.messages.length - 1].id;
          setMsgs((prev) => [...prev, ...j.messages].slice(-50));
        }
      } catch { /* transient — next tick retries */ }
    }, 2500);
    return () => clearInterval(tick);
  }, [active, hash]);

  async function say(e) {
    e.preventDefault();
    if (!draft.trim()) return;
    const body = draft.trim();
    setDraft("");
    await fetch(`/live/${hash}/say`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname: nick, body }),
    });
  }

  return (
    <section className="panel">
      <div className="sec-label">CHAT · {nick}</div>
      <div style={{ maxHeight: 240, overflowY: "auto", margin: "10px 0" }}>
        {msgs.map((m) => (
          <p key={m.id} style={{ overflowWrap: "anywhere" }}>
            <b>{m.nickname}</b>{" "}
            <span className="dim small">· {m.said_at.slice(11, 19)}Z</span><br />
            {m.body}
          </p>
        ))}
        {msgs.length === 0 && (
          <p className="dim small">no messages yet — say hi…</p>
        )}
      </div>
      <form onSubmit={say} style={{ display: "flex", gap: 8 }}>
        <input type="text" value={draft} maxLength={500}
               onChange={(e) => setDraft(e.target.value)}
               placeholder="say it to the room (≤ 500 chars)" />
        <button className="bevel" type="submit" disabled={!draft.trim()}>
          SAY
        </button>
      </form>
      <p className="dim small" style={{ marginTop: 6 }}>
        anonymous · nicknames cap at 32 chars · messages die with the session
      </p>
    </section>
  );
}
