import React from "react";
import { Link } from "react-router-dom";
import { Masthead } from "./HomePage";

// The privacy page — every claim here is verifiable in the repo:
// no session writes (grep session[ in app.py/live.py: zero), no
// Set-Cookie on any route (probed), the only client state is the
// theme in localStorage. Ephemeral means ephemeral — capito?
export default function PrivacyPage() {
  return (
    <main>
      <Masthead />
      <section>
        <div className="sec-label">THE FINE PRINT · PRIVACY</div>
        <h1 style={{ fontSize: "clamp(24px,6vw,40px)" }}>PRIVACY, IN ONE PAGE</h1>
        <p className="dim">last updated: november 2026 · burnafter.it</p>
      </section>

      <section className="panel">
        <h2>THE SHORT VERSION</h2>
        <p style={{ marginTop: 8 }}>
          We store <b>no personal data</b>, we set <b>no cookies</b>, and we
          track <b>no one</b>. Content is reachable only by its secret link,
          and when its fuse runs out, it is <b>deleted</b> — from storage,
          not just from view.
        </p>
      </section>

      <section className="panel">
        <h2>WHAT WE ACTUALLY KEEP (AND FOR HOW LONG)</h2>
        <div style={{ marginTop: 8 }}>
          <p><b>Shouts (text/photo/audio/video):</b> the content plus its
          fuse (views/time). Deleted by the cleanup job once burned or
          expired — storage, not just access.</p>
          <p><b>Live sessions:</b> the audio ring lives in memory (Redis)
          with a time-to-live equal to the session fuse; when the session
          ends or expires, it is gone. Chat messages and session rows are
          deleted by the cleanup job — messages die with the session.</p>
          <p><b>Chat rooms:</b> same as live sessions — the room dies, the
          messages die with it.</p>
          <p><b>What we DON'T keep:</b> accounts (there are none),
          email addresses, IP logs, analytics, profiles, or any
          identifier tying content to a person.</p>
        </div>
      </section>

      <section className="panel">
        <h2>COOKIES (OR THE LACK OF THEM)</h2>
        <p style={{ marginTop: 8 }}>
          This site sets <b>no cookies</b> — no session cookies, no
          analytics cookies, no third-party cookies. The only thing saved
          in your browser is your <b>theme choice</b> (Puppa / Ember / Warm)
          in localStorage, which never leaves your device. The consent
          banner remembers your "got it" the same way — in your browser,
          nowhere else.
        </p>
      </section>

      <section className="panel">
        <h2>YOUR GDPR RIGHTS (SHORT, BECAUSE THE ANSWER IS SHORT)</h2>
        <div style={{ marginTop: 8 }}>
          <p><b>Access / erasure / portability:</b> for anything you
          created, the secret link IS the access. Losing the link is the
          erasure. There is nothing to export because nothing identifies
          you.</p>
          <p><b>Right to object / restrict:</b> there is no processing of
          personal data to object to.</p>
          <p><b>Complaints:</b> you can contact the site operator at the
          address published on the domain registration. This being a
          hobby project with no data, we expect short conversations.</p>
        </div>
      </section>

      <section className="panel" style={{ transform: "rotate(-.6deg)" }}>
        <h2>THE HONEST FOOTNOTE</h2>
        <p style={{ marginTop: 8 }}>
          Ephemeral means ephemeral. There is no database of your stuff —
          there's barely a database at all. If a regulator asks what we
          know about you: "the fuse burned it, capito?"
        </p>
      </section>

      <section style={{ textAlign: "center" }}>
        <Link to="/" className="bevel">◄ BACK HOME</Link>
      </section>
    </main>
  );
}
