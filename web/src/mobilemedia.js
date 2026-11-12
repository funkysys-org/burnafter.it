// Mobile-media utilities (planned fix A+B):
//  A. HEIC/HEIF photos -> JPEG via canvas re-encode (iOS camera default;
//     server allowlist stays JPEG/PNG — no HEIC ever stored)
//  B. MediaRecorder mime negotiation for GO LIVE (Safari iOS has no
//     webm; falls back to audio/mp4/AAC)

// ── B: broadcast mime negotiation ─────────────────────────────────────────
const RECORD_MIMES = [
  "audio/webm;codecs=opus",   // Chrome/Firefox/Android — the ideal
  "audio/mp4",                // Safari iOS 14.3+ — AAC in an mp4 box
  "audio/webm",               // last resort, container only
];

export function pickRecordMime() {
  if (typeof MediaRecorder === "undefined") return null;
  for (const m of RECORD_MIMES) {
    try {
      if (MediaRecorder.isTypeSupported(m)) return m;
    } catch { /* some browsers throw on unknown types */ }
  }
  return null;
}

// Container sniffing from the FIRST bytes of the first segment — the
// player needs to know what the source is actually sending (the ring
// carries whatever the recorder produced).
export function sniffContainer(bytes) {
  const b = new Uint8Array(bytes);
  if (b.length < 12) return "unknown";
  // EBML magic 0x1A45DFA3 — webm
  if (b[0] === 0x1a && b[1] === 0x45 && b[2] === 0xdf && b[3] === 0xa3) {
    return "webm";
  }
  // ISO-BMFF: size(4) + 'ftyp'
  if (
    b[4] === 0x66 && b[5] === 0x74 &&
    b[6] === 0x79 && b[7] === 0x70
  ) {
    return "mp4";
  }
  return "unknown";
}

// The SourceBuffer mime for a detected container + codec preference.
export function playbackMime(container) {
  if (container === "webm") return "audio/webm; codecs=opus";
  if (container === "mp4") return "audio/mp4"; // AAC-in-mp4 (Safari emits, all play)
  return null;
}

// ── A: HEIC/HEIF -> JPEG re-encode via canvas ────────────────────────────
// Returns a File the upload path can treat as a first-class JPEG.
// Browsers that can't decode HEIC (most desktop ones) reject in
// createImageBitmap/img.onerror -> we throw honestly.
export async function convertToJpeg(file, quality = 0.9) {
  const bitmap = await createBitmap(file);
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  canvas.getContext("2d").drawImage(bitmap, 0, 0);
  if (bitmap.close) bitmap.close();
  const blob = await new Promise((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", quality));
  if (!blob) throw new Error("JPEG conversion failed in this browser");
  const name = (file.name || "photo").replace(/\.[^.]+$/, "") + ".jpg";
  return new File([blob], name, { type: "image/jpeg" });
}

async function createBitmap(file) {
  if (typeof createImageBitmap === "function") {
    return createImageBitmap(file); // may still reject on non-decoders
  }
  // older path: <img> decode
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    return img;
  } finally {
    URL.revokeObjectURL(url);
  }
}
