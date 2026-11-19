from app.session.config import Config

LABELS = {1: "Player A", 2: "Player B", 3: "Player C"}
SLOT_BY_LABEL = {label: slot for slot, label in LABELS.items()}

# phase_seq 0 is the waiting room; the run then steps through these in order,
# so phase_seq N is PHASES[N - 1].
PHASES: list[tuple[str, int | None]] = [
    ("discussion", 1),
    ("voting", 1),
    ("discussion", 2),
    ("voting", 2),
    ("results", None),
]


def phase_at(phase_seq: int) -> tuple[str, int | None]:
    return PHASES[phase_seq - 1]


def duration_seconds(phase: str, config: Config) -> int | None:
    if phase == "discussion":
        return config.chat_seconds
    if phase == "voting":
        return config.vote_seconds
    return None
