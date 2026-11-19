// The countdown ring needs the full length of the current phase. A phase.changed
// message carries both the server time and the deadline, so the length is known
// exactly when a phase starts; it is kept per tab so a refresh mid-phase still
// draws the ring correctly. Nothing here is sent anywhere.
const key = (phaseSeq: number) => `phaseLength:${phaseSeq}`;

export function rememberPhaseLength(phaseSeq: number, ms: number): void {
  try {
    sessionStorage.setItem(key(phaseSeq), String(ms));
  } catch {
    // storage unavailable: the ring falls back to the time left when first drawn
  }
}

export function recallPhaseLength(phaseSeq: number): number | null {
  try {
    const value = Number(sessionStorage.getItem(key(phaseSeq)));
    return value > 0 ? value : null;
  } catch {
    return null;
  }
}
