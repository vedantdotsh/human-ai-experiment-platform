// Neutral player identity: the same shape for every label, coloured by label only.
export function PlayerChip({ label, size }: { label: string; size?: "lg" | "xl" }) {
  const letter = label.replace("Player ", "").slice(0, 1).toUpperCase();
  const sizeClass = size ? ` is-${size}` : "";
  return (
    <span className={`player-chip is-${letter.toLowerCase()}${sizeClass}`} aria-hidden="true">
      {letter}
    </span>
  );
}

export function IdentityPill({ label }: { label: string }) {
  return (
    <span className="identity-pill">
      <PlayerChip label={label} />
      <span>You are {label}</span>
    </span>
  );
}
