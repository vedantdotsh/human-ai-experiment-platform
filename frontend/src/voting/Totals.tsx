import type { CSSProperties } from "react";
import type { Totals } from "../realtime/socket";
import { useCountUp, useGrown } from "../ui/motion";
import { PlayerChip } from "../ui/PlayerChip";

// Three seats vote, so three is the most any player can receive in a round.
const MAX_VOTES = 3;
const ratio = (n: number) => ({ "--ratio": (n / MAX_VOTES).toFixed(4) }) as CSSProperties;

function Count({ value, className }: { value: number; className: string }) {
  return <span className={className}>{useCountUp(value)}</span>;
}

/** Option H's round 1 column chart. Only totals, never who voted for whom. */
export function RoundOneTotals({ totals }: { totals: Totals }) {
  const grown = useGrown();
  return (
    <section className="card totals-card" aria-label="Round 1 totals">
      <div className="totals-header">
        <h2 className="totals-title">Round 1 totals</h2>
        <span className="totals-note">Totals only</span>
      </div>
      <div className="column-chart">
        {Object.entries(totals).map(([label, value]) => (
          <div className="column-item" key={label}>
            <div className="column-plot">
              <Count value={value} className="column-value" />
              <div
                className={`column-bar is-${label.slice(-1).toLowerCase()}${value === 0 ? " is-zero" : ""}${grown ? " is-grown" : ""}`}
                style={ratio(value)}
              />
            </div>
            <div className="column-label">
              <PlayerChip label={label} />
              <span>{label}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/** Option H's grouped round 1 / round 2 chart for the results screen. */
export function ResultsChart({ round1, round2 }: { round1: Totals | null; round2: Totals }) {
  const grown = useGrown();
  const bar = (value: number, round: "r1" | "r2") => (
    <div className="bar-slot">
      <Count value={value} className="bar-num" />
      <div
        className={`bar-fill is-${round}${value === 0 ? " is-zero" : ""}${grown ? " is-grown" : ""}`}
        style={ratio(value)}
      />
    </div>
  );
  return (
    <section className="card results-chart-card" aria-label="Vote totals">
      <div className="chart-legend">
        {round1 && (
          <span className="legend-item">
            <span className="legend-swatch is-r1" aria-hidden="true" />
            Round 1
          </span>
        )}
        <span className="legend-item">
          <span className="legend-swatch is-r2" aria-hidden="true" />
          Round 2
        </span>
      </div>
      <div className="grouped-chart">
        {Object.entries(round2).map(([label, value]) => (
          <div className="grouped-player" key={label}>
            <div className="grouped-bars">
              {round1 && bar(round1[label] ?? 0, "r1")}
              {bar(value, "r2")}
            </div>
            <div className="grouped-foot">
              <div className="column-label">
                <PlayerChip label={label} />
                <span>{label}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
