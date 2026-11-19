import { useCallback, useEffect, useState } from "react";
import { join, leave } from "./api";

type State =
  | { kind: "joining" }
  | { kind: "waiting" }
  | { kind: "left" }
  | { kind: "error"; message: string };

export function WaitingRoom() {
  const [state, setState] = useState<State>({ kind: "joining" });

  const claim = useCallback(() => {
    setState({ kind: "joining" });
    return join().then(
      () => setState({ kind: "waiting" }),
      (err: Error) => setState({ kind: "error", message: err.message }),
    );
  }, []);

  useEffect(() => {
    void claim();
  }, [claim]);

  const release = () =>
    leave().then(
      () => setState({ kind: "left" }),
      (err: Error) => setState({ kind: "error", message: err.message }),
    );

  switch (state.kind) {
    case "joining":
      return <p>Joining…</p>;
    case "waiting":
      return (
        <>
          <p>Waiting for other participants</p>
          <button onClick={release}>Leave</button>
        </>
      );
    case "left":
      return (
        <>
          <p>You left the waiting room.</p>
          <button onClick={() => void claim()}>Join again</button>
        </>
      );
    case "error":
      return (
        <>
          <p>Not ready: {state.message}</p>
          <button onClick={() => void claim()}>Retry</button>
        </>
      );
  }
}
