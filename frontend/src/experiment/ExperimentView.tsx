import { Chat } from "../messaging/Chat";
import { Results } from "../results/Results";
import { IdentityPill } from "../ui/PlayerChip";
import { RoundOneTotals } from "../voting/Totals";
import { VotePanel } from "../voting/VotePanel";
import { Countdown } from "./Countdown";
import { recallPhaseLength } from "./phaseClock";
import type { State } from "./reducer";
import { StepPills } from "./StepPills";

type Props = {
  state: State & { session: NonNullable<State["session"]> };
  onSend(text: string): void;
  onVote(target: string): void;
};

export function ExperimentView({ state, onSend, onVote }: Props) {
  const { session, clockOffset, notice } = state;
  const ownLabel = session.ownLabel ?? "";
  const length = session.phaseLength ?? recallPhaseLength(session.phaseSeq);
  const timer = (size?: "sm") =>
    session.deadline !== null && (
      <Countdown
        key={session.phaseSeq}
        deadline={session.deadline}
        offset={clockOffset}
        length={length}
        size={size}
      />
    );
  const roundMeta = (
    <div className="round-meta">
      <span className="round-tag">
        Round {session.round} of 2{session.phase === "voting" ? " · Vote" : ""}
      </span>
      <IdentityPill label={ownLabel} />
      {session.phase === "voting" && timer("sm")}
    </div>
  );

  return (
    <>
      <StepPills phaseSeq={session.phaseSeq} />
      {/* Keyed by phase so each new phase enters with option H's stage animation. */}
      <div className="stage stage-enter" key={session.phaseSeq}>
        {session.phase === "discussion" && (
          <>
            {roundMeta}
            {timer()}
            {session.vote1Totals && <RoundOneTotals totals={session.vote1Totals} />}
          </>
        )}
        {session.phase === "voting" && (
          <>
            <VotePanel
              header={roundMeta}
              options={session.voteOptions}
              ownLabel={ownLabel}
              ownVote={session.ownVote}
              ballotsCast={session.ballotsCast}
              notice={notice}
              onVote={onVote}
            />
            {session.vote1Totals && <RoundOneTotals totals={session.vote1Totals} />}
          </>
        )}
        {session.phase === "results" && (
          <Results ownLabel={ownLabel} results={session.results} vote1Totals={session.vote1Totals} />
        )}
        <Chat
          messages={session.messages}
          ownLabel={session.ownLabel}
          open={session.phase === "discussion"}
          notice={session.phase === "voting" ? null : notice}
          onSend={onSend}
        />
      </div>
    </>
  );
}
