import { useEffect, useState } from "react";
import { Chat } from "../messaging/Chat";
import { Results } from "../results/Results";
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
};

export function ExperimentView({ state, onSend }: Props) {
  const { session, clockOffset, notice } = state;
  const title = session.phase === "discussion" ? "Discussion" : "Voting";
  return (
    <>
      <p>
        You are <strong>{session.ownLabel}</strong>.
      </p>
      {session.phase === "results" ? (
        <Results />
      ) : (
        <p>
          Round {session.round} · {title}
          {session.deadline !== null && (
            <>
              {" "}
              · <Countdown deadline={session.deadline} offset={clockOffset} />
            </>
          )}
        </p>
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
