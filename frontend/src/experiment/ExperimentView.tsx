import { useEffect, useState } from "react";
import { Chat } from "../messaging/Chat";
import { Results } from "../results/Results";
import { TotalsList, VotePanel } from "../voting/VotePanel";
import type { State } from "./reducer";

function Countdown({ deadline, offset }: { deadline: number; offset: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);
  return <span>{Math.max(0, Math.ceil((deadline - (now + offset)) / 1000))}s</span>;
}

type Props = {
  state: State & { session: NonNullable<State["session"]> };
  onSend(text: string): void;
  onVote(target: string): void;
};

export function ExperimentView({ state, onSend, onVote }: Props) {
  const { session, clockOffset, notice } = state;
  const finished = session.phase === "results";
  return (
    <>
      <p>
        You are <strong>{session.ownLabel}</strong>.
      </p>
      {finished ? (
        <Results results={session.results} vote1Totals={session.vote1Totals} />
      ) : (
        <>
          <p>
            Round {session.round} · {session.phase === "discussion" ? "Discussion" : "Voting"}
            {session.deadline !== null && (
              <>
                {" "}
                · <Countdown deadline={session.deadline} offset={clockOffset} />
              </>
            )}
          </p>
          {session.phase === "voting" && (
            <VotePanel
              ownVote={session.ownVote}
              ballotsCast={session.ballotsCast}
              onVote={onVote}
            />
          )}
          {session.vote1Totals && (
            <TotalsList title="Round 1 vote totals" totals={session.vote1Totals} />
          )}
        </>
      )}
      <Chat
        messages={session.messages}
        ownLabel={session.ownLabel}
        open={session.phase === "discussion"}
        notice={notice}
        onSend={onSend}
      />
    </>
  );
}
