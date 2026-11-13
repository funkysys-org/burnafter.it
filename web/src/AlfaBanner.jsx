import React from "react";

// Alfa-testing banner for the experimental surfaces (Radio/Go Live,
// Phone/Call). Honest copy: things may hiccup, but burns are REAL —
// don't test with content you'd mourn.
export default function AlfaBanner() {
  return (
    <div className="alfa-banner" role="note" aria-label="alfa version in testing">
      ⚠ ALFA VERSION — IN TESTING · EXPECT HICCUPS · BURNS ARE REAL
    </div>
  );
}
