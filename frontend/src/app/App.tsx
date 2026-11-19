import { ExperimentView } from "../experiment/ExperimentView";
import { useExperiment } from "../experiment/useExperiment";
import { WaitingRoom } from "../session/WaitingRoom";

export function App() {
  const { state, claim, leaveWaitingRoom, sendMessage, sendVote } = useExperiment();
  const { session } = state;
  // The label arrives with the start snapshot; until then keep the generic waiting text.
  const started =
    state.status === "joined" &&
    session !== null &&
    session.phase !== "waiting" &&
    session.ownLabel !== null;

  return (
    <main>
      <h1>Experiment</h1>
      {started ? (
        <ExperimentView state={{ ...state, session }} onSend={sendMessage} onVote={sendVote} />
      ) : (
        <WaitingRoom
          status={state.status}
          error={state.error}
          onLeave={() => void leaveWaitingRoom()}
          onJoin={() => void claim()}
        />
      )}
    </main>
  );
}
