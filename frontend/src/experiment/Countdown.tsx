import { useEffect, useRef, useState } from "react";

const RADIUS = 68;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function format(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

type Props = {
  /** Server deadline (ms since epoch) and server-minus-browser clock offset. */
  deadline: number;
  offset: number;
  /** Full phase length in ms, when known. */
  length: number | null;
  size?: "sm";
};

/** Option H's ring countdown, driven only by the server's deadline. */
export function Countdown({ deadline, offset, length, size }: Props) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(id);
  }, []);
  const remainingMs = Math.max(0, deadline - (now + offset));
  const fallback = useRef(remainingMs);
  const total = length ?? fallback.current;
  const ratio = total > 0 ? Math.min(1, remainingMs / total) : 0;
  const seconds = Math.ceil(remainingMs / 1000);
  const amber = seconds > 0 && seconds <= 10;

  return (
    <div
      className={`countdown-hero${size ? ` is-${size}` : ""}${amber ? " is-amber" : ""}`}
      role="timer"
      aria-live="off"
      aria-label={`${format(seconds)} left`}
    >
      <svg className="countdown-svg" viewBox="0 0 160 160" aria-hidden="true">
        <circle className="countdown-track" cx="80" cy="80" r={RADIUS} />
        <circle
          className="countdown-progress"
          cx="80"
          cy="80"
          r={RADIUS}
          strokeDasharray={CIRCUMFERENCE.toFixed(2)}
          strokeDashoffset={(CIRCUMFERENCE * (1 - ratio)).toFixed(2)}
        />
      </svg>
      <div className="countdown-readout">
        <span className="countdown-digits">{format(seconds)}</span>
        <span className="countdown-label">Time left</span>
      </div>
    </div>
  );
}
