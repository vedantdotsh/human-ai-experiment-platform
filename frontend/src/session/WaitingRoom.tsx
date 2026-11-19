type Props = {
  status: "joining" | "joined" | "left" | "ended" | "error";
  error: string | null;
  onLeave(): void;
  onJoin(): void;
};

// The waiting room shows one generic line and nothing else about who is here.
export function WaitingRoom({ status, error, onLeave, onJoin }: Props) {
  switch (status) {
    case "joining":
      return <p>Joining…</p>;
    case "joined":
      return (
        <>
          <p>Waiting for other participants</p>
          <button onClick={onLeave}>Leave</button>
        </>
      );
    case "left":
      return (
        <>
          <p>You left the waiting room.</p>
          <button onClick={onJoin}>Join again</button>
        </>
      );
    case "ended":
      return (
        <>
          <p>This run is no longer available.</p>
          <button onClick={onJoin}>Join a new run</button>
        </>
      );
    case "error":
      return (
        <>
          <p>Not ready: {error}</p>
          <button onClick={onJoin}>Retry</button>
        </>
      );
  }
}
