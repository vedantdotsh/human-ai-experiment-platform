import type { Results as ResultsData, Totals } from "../realtime/socket";
import { TotalsList } from "../voting/VotePanel";

type Props = { results: ResultsData | null; vote1Totals: Totals | null };

export function Results({ results, vote1Totals }: Props) {
  return (
    <section>
      <p>The experiment has ended.</p>
      {results && (
        <>
          <h2>Decision Maker: {results.winner}</h2>
          <TotalsList title="Final vote totals" totals={results.totals} />
        </>
      )}
      {vote1Totals && <TotalsList title="Round 1 vote totals" totals={vote1Totals} />}
    </section>
  );
}
