import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

// GDPR consent — the honest version. This app sets NO cookies (verified:
// no session writes, no Set-Cookie on any route). The only client-side
// state is the theme in localStorage. The banner exists because GDPR
// asks for informed transparency — and our answer is short.
const KEY = "bai-consent-v1";

export default function ConsentBanner() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(KEY)) setShow(true);
    } catch { setShow(true); }
  }, []);

  function answer(ok) {
    try { localStorage.setItem(KEY, ok ? "ok" : "no"); } catch {}
    setShow(false);
  }

  if (!show) return null;

  return (
    <div style={{
      position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 50,
      background: "var(--panel-bg)", borderTop: "2px solid var(--border)",
      padding: "12px 16px", display: "flex", gap: 12,
      alignItems: "center", flexWrap: "wrap", justifyContent: "center",
    }}>
      <span style={{ fontSize: 12, color: "var(--ink)", maxWidth: 560 }}>
        🍪 We use <b>no cookies</b> — no tracking, no accounts, nothing
        recorded. The only thing saved in your browser is your theme
        choice. Read the{" "}
        <Link to="/privacy" style={{ color: "var(--blue)" }}>privacy page</Link>{" "}
        if you like short stories.
      </span>
      <button className="bevel" style={{ minHeight: 0, padding: "8px 12px", fontSize: 11 }}
              onClick={() => answer(true)}>
        GOT IT
      </button>
    </div>
  );
}
