import type { CSSProperties, ReactNode } from "react";
import { PlayerChip } from "../ui/PlayerChip";

const SEATS = 3;

type Props = {
  /** The players this viewer may vote for, exactly as the server sent them. */
  options: string[];
  ownLabel: string;
  ownVote: string | null;
  ballotsCast: number | null;
  notice: string | null;
  header: ReactNode;
  onVote(target: string): void;
};

export function VotePanel({ options, ownLabel, ownVote, ballotsCast, notice, header, onVote }: Props) {
  const cast = ballotsCast ?? 0;
  const voted = ownVote !== null;
  return (
    <section className="vote-stage">
      {header}
      <h1 className="vote-question">Who should be the decision maker?</h1>
      <p className="vote-self-note">
        {options.includes(ownLabel) ? "You may vote for yourself" : "Cannot vote for yourself"}
      </p>

      <div className="vote-tiles" style={{ "--options": options.length } as CSSProperties}>
        {options.map((label) => {
          const chosen = ownVote === label;
          return (
            <button
              key={label}
              type="button"
              className={`vote-tile${chosen ? " is-chosen" : voted ? " is-unchosen" : ""}`}
              disabled={voted}
              aria-pressed={chosen}
              onClick={() => onVote(label)}
            >
              <PlayerChip label={label} size="lg" />
              <span className="vote-tile-name">{label}</span>
              <span className="vote-check-badge" aria-hidden="true">
                <svg className="vote-check-svg" viewBox="0 0 18 18">
                  <path className="vote-check-path" d="M3.5 9.5L7.2 13.2L14.5 5.2" />
                </svg>
              </span>
            </button>
          );
        })}
      </div>

      {voted && (
        <div className="vote-status-block">
          <span className="vote-yours">Your vote: {ownVote} · final</span>
          {cast < SEATS && <p className="vote-waiting-note">Waiting for other ballots</p>}
        </div>
      )}
      {notice && <p className="notice" role="alert">{notice}</p>}

      <div className="ballots-panel" aria-live="polite">
        <div className="ballot-dots">
          {Array.from({ length: SEATS }, (_, i) => (
            <span key={i} className={`ballot-dot${i < cast ? " is-filled" : ""}`} aria-hidden="true" />
          ))}
        </div>
        <span className="ballots-label">
          Ballots cast {cast} of {SEATS}
        </span>
      </div>
    </section>
  );
}
