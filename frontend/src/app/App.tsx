import { useEffect, useState } from "react";

type Health = { status: string; database: string };
type State =
  | { kind: "loading" }
  | { kind: "ready"; health: Health }
  | { kind: "error"; message: string };

export function App() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    fetch("/api/health")
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setState({ kind: "ready", health: (await res.json()) as Health });
      })
      .catch((err: Error) => setState({ kind: "error", message: err.message }));
  }, []);

  return (
    <main>
      <h1>Experiment</h1>
      {state.kind === "loading" && <p>Checking readiness…</p>}
      {state.kind === "error" && <p>Not ready: {state.message}</p>}
      {state.kind === "ready" && (
        <ul>
          <li>API: {state.health.status === "ok" ? "ready" : state.health.status}</li>
          <li>Database: {state.health.database === "ok" ? "ready" : state.health.database}</li>
        </ul>
      )}
    </main>
  );
}
