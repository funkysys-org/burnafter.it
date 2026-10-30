// Auto-burn fuse policy (maintainer-locked 2026-10-25):
//   text / photo       -> fixed 8s countdown
//   audio / video      -> PLAYBACK-LINKED: burns duration + 5s after
//                        the reveal; pausing the player pauses the fuse
//   duration unreadable -> null = MANUAL-ONLY burn (the honest fallback)
export const AUTO_BURN_STATIC_S = 8;
export const AUTO_BURN_MARGIN_S = 5;

// Returns seconds (number), or null when the auto fuse is disabled.
export function autoBurnFor(type, duration) {
  if (type === "audio" || type === "video") {
    if (typeof duration !== "number" || !isFinite(duration) || duration <= 0) {
      return null; // manual-only — never guess a media duration
    }
    return Math.ceil(duration) + AUTO_BURN_MARGIN_S;
  }
  return AUTO_BURN_STATIC_S; // text/photo (and defensive: unknown types)
}

// Playback-linked remaining fuse. currentTime can exceed duration while
// the browser finishes the last frame; the margin absorbs that.
export function remainingSeconds(duration, currentTime) {
  if (typeof duration !== "number" || !isFinite(duration) || duration <= 0) {
    return null;
  }
  const left = Math.ceil(duration) + AUTO_BURN_MARGIN_S - Math.floor(currentTime);
  return left > 0 ? left : 0;
}
