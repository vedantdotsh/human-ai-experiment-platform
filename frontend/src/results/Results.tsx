import type { Results as ResultsData, Totals } from "../realtime/socket";
import { useCountUp } from "../ui/motion";
import { IdentityPill, PlayerChip } from "../ui/PlayerChip";
import { ResultsChart } from "../voting/Totals";

type Props = { ownLabel: string; results: ResultsData | null; vote1Totals: Totals | null };

export function Results({ ownLabel, results, vote1Totals }: Props) {
  return (
    <section className="results-stage">
      <div className="results-head">
        <h1 className="results-title">Results</h1>
        <IdentityPill label={ownLabel} />
      </div>
      {results ? (
        <>
          <Podium winner={results.winner} votes={results.totals[results.winner] ?? 0} />
          <ResultsChart round1={vote1Totals} round2={results.totals} />
        </>
      ) : (
        <p className="joining-note">The experiment has ended.</p>
      )}
    </section>
  );
}

function Podium({ winner, votes }: { winner: string; votes: number }) {
  const shown = useCountUp(votes);
  return (
    <div className="podium-wrap">
      <div className="podium-glow" aria-hidden="true" />
      <div className="podium-card">
        <span className="podium-label">Decision maker</span>
        <div className="podium-winner">
          <PlayerChip label={winner} size="xl" />
          <span className="podium-winner-name">{winner}</span>
        </div>
        <p className="podium-how">The experiment has ended.</p>
        <div className="podium-steps" aria-hidden="true">
          <div className="podium-tier is-side" />
          <div className="podium-tier is-center">
            <span className="podium-tier-total">{shown}</span>
            <span className="podium-tier-caption">Round 2 votes</span>
          </div>
          <div className="podium-tier is-side" />
        </div>
      </div>
    </div>
  );
}
