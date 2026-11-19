const STEPS = ["Waiting", "Round 1", "Vote", "Round 2", "Vote", "Results"];

/** Progress through the run; the active step is the server's phase sequence. */
export function StepPills({ phaseSeq }: { phaseSeq: number }) {
  return (
    <nav className="step-nav" aria-label="Progress">
      <div className="step-pills">
        {STEPS.map((label, i) => (
          <span
            key={i}
            className={`step-pill${i < phaseSeq ? " is-done" : i === phaseSeq ? " is-active" : ""}`}
            aria-current={i === phaseSeq ? "step" : undefined}
          >
            {label}
          </span>
        ))}
      </div>
    </nav>
  );
}
