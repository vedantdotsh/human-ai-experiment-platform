import type { Totals } from "../realtime/socket";

// The three candidates are always the three neutral labels.
const CANDIDATES = ["Player A", "Player B", "Player C"];

type Props = {
  ownVote: string | null;
  ballotsCast: number | null;
  onVote(target: string): void;
};

export function VotePanel({ ownVote, ballotsCast, onVote }: Props) {
  return (
    <section>
      <h2>Vote</h2>
      <p>Choose one player. You may vote for yourself. Your ballot is final.</p>
      {CANDIDATES.map((label) => (
        <button key={label} disabled={ownVote !== null} onClick={() => onVote(label)}>
          {label}
        </button>
      ))}
      {ownVote !== null && <p>Your vote: {ownVote} (final)</p>}
      <p>Ballots cast: {ballotsCast ?? 0}</p>
    </section>
  );
}

export function TotalsList({ title, totals }: { title: string; totals: Totals }) {
  return (
    <section>
      <h2>{title}</h2>
      <ul>
        {Object.entries(totals).map(([label, count]) => (
          <li key={label}>
            {label}: {count}
          </li>
        ))}
      </ul>
    </section>
  );
}
