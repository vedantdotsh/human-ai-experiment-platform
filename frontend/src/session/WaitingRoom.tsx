import { StatusCard } from "../ui/StatusCard";

type Props = {
  status: "joining" | "joined" | "left" | "ended" | "error";
  error: string | null;
  onLeave(): void;
  onJoin(): void;
};

// The waiting room shows only the breathing shape, one generic line and Leave:
// nothing about who or how many are here.
export function WaitingRoom({ status, error, onLeave, onJoin }: Props) {
  switch (status) {
    case "joining":
      return <p className="joining-note stage-enter">Joining…</p>;
    case "joined":
      return (
        <section className="waiting-stage stage-enter">
          <div className="blob-stage" aria-hidden="true">
            <div className="blob-halo" />
            <div className="blob-core" />
          </div>
          <h1 className="waiting-title">Waiting for other participants</h1>
          <button type="button" className="btn btn-secondary" onClick={onLeave}>
            Leave
          </button>
        </section>
      );
    case "left":
      return (
        <StatusCard icon="left" title="You left the waiting room">
          <button type="button" className="btn btn-primary" onClick={onJoin}>
            Join again
          </button>
        </StatusCard>
      );
    case "ended":
      return (
        <StatusCard icon="info" title="This run is no longer available" hint="This session has ended">
          <button type="button" className="btn btn-primary" onClick={onJoin}>
            Join a new run
          </button>
        </StatusCard>
      );
    case "error":
      return (
        <StatusCard icon="info" title="Not ready" hint={error ?? undefined}>
          <button type="button" className="btn btn-primary" onClick={onJoin}>
            Retry
          </button>
        </StatusCard>
      );
  }
}
