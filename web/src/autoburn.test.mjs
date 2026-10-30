import test from "node:test";
import assert from "node:assert/strict";

import {
  AUTO_BURN_STATIC_S,
  AUTO_BURN_MARGIN_S,
  autoBurnFor,
  remainingSeconds,
} from "./autoburn.js";

test("static types: text/photo burn on the fixed 8s fuse", () => {
  assert.equal(autoBurnFor("text", null), AUTO_BURN_STATIC_S);
  assert.equal(autoBurnFor("photo", null), AUTO_BURN_STATIC_S);
  assert.equal(AUTO_BURN_STATIC_S, 8);
});

test("media with readable duration: duration + 5s grace", () => {
  assert.equal(autoBurnFor("audio", 12.4), Math.ceil(12.4) + AUTO_BURN_MARGIN_S);
  assert.equal(autoBurnFor("video", 60), 65);
  assert.equal(AUTO_BURN_MARGIN_S, 5);
});

test("media with unreadable duration: null = manual-only (honest fallback)", () => {
  assert.equal(autoBurnFor("audio", Infinity), null);
  assert.equal(autoBurnFor("audio", NaN), null);
  assert.equal(autoBurnFor("video", 0), null);
  assert.equal(autoBurnFor("audio", undefined), null);
});

test("remainingSeconds is playback-linked", () => {
  assert.equal(remainingSeconds(60, 30), 35);   // mid-playback
  assert.equal(remainingSeconds(60, 60), 5);    // just ended -> margin left
  assert.equal(remainingSeconds(60, 63), 2);   // inside the margin
  assert.equal(remainingSeconds(60, 65), 0);   // fuse out -> burn
  assert.equal(remainingSeconds(NaN, 10), null);
  assert.equal(remainingSeconds(Infinity, 10), null);
});

test("unknown type falls back to the static fuse (defensive)", () => {
  assert.equal(autoBurnFor("exe", 999), AUTO_BURN_STATIC_S);
});
