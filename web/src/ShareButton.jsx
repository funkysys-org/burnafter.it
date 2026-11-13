import React, { useState } from "react";

// Adaptive share button: native share sheet on mobile (Web Share API),
// clipboard copy on desktop. One button, always the right behavior.
export default function ShareButton({ url, title, className = "bevel" }) {
  const [done, setDone] = useState(false);
  const [label, setLabel] = useState("");

  async function share() {
    // native sheet first — mobile only, requires secure context
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title: title || "burnafter.it", url });
        setLabel("SHARED!");
        setDone(true);
        setTimeout(() => setDone(false), 2500);
        return;
      } catch (e) {
        if (e && e.name === "AbortError") return; // user dismissed the sheet
        // other failures (denied, unsupported mid-flight): fall through
      }
    }
    // desktop fallback: clipboard
    try {
      await navigator.clipboard.writeText(url);
      setLabel("COPIED!");
    } catch {
      setLabel("COPY FAILED"); // honest: URL stays visible on the page
    }
    setDone(true);
    setTimeout(() => setDone(false), 2500);
  }

  const native = typeof navigator.share === "function";
  return (
    <button className={className} onClick={share} aria-pressed={done}>
      {done ? label : native ? "SHARE THE LINK" : "COPY THE LINK"}
    </button>
  );
}
