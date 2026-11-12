import test from "node:test";
import assert from "node:assert/strict";

import {
  pickRecordMime,
  sniffContainer,
  playbackMime,
} from "./mobilemedia.js";

// pickRecordMime needs MediaRecorder — simulate the browser env
test("pickRecordMime: webm browsers get opus first", () => {
  globalThis.MediaRecorder = {
    isTypeSupported: (m) => m.startsWith("audio/webm"),
  };
  assert.equal(pickRecordMime(), "audio/webm;codecs=opus");
});

test("pickRecordMime: Safari iOS falls back to audio/mp4", () => {
  globalThis.MediaRecorder = {
    isTypeSupported: (m) => m === "audio/mp4",
  };
  assert.equal(pickRecordMime(), "audio/mp4");
});

test("pickRecordMime: no MediaRecorder at all -> null (honest degrade)", () => {
  globalThis.MediaRecorder = undefined;
  assert.equal(pickRecordMime(), null);
});

// container sniffing — the same magic bytes the server trusts
const EBML = new Uint8Array([0x1a, 0x45, 0xdf, 0xa3, 1, 2, 3, 4, 5, 6, 7, 8]);
const FTyp = new Uint8Array([0, 0, 0, 0x18, 0x66, 0x74, 0x79, 0x70, 1, 2, 3, 4]);

test("sniffContainer: EBGL magic -> webm", () => {
  assert.equal(sniffContainer(EBML), "webm");
});

test("sniffContainer: ftyp -> mp4 (Safari's AAC output)", () => {
  assert.equal(sniffContainer(FTyp), "mp4");
});

test("sniffContainer: unknown stays honest", () => {
  assert.equal(sniffContainer(new Uint8Array(16)), "unknown");
});

test("playbackMime maps container to SourceBuffer mime", () => {
  assert.equal(playbackMime("webm"), "audio/webm; codecs=opus");
  assert.equal(playbackMime("mp4"), "audio/mp4");
  assert.equal(playbackMime("unknown"), null);
});
