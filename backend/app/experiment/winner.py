from collections.abc import Callable, Sequence

SLOTS = (1, 2, 3)


def decide_winner(
    vote1: dict[int, int],
    vote2: dict[int, int],
    choose: Callable[[Sequence[int]], int],
) -> tuple[int, str]:
    """Pick the Decision Maker. Returns (slot, how it was decided).

    Vote 2 decides; candidates tied for first are compared on vote 1; candidates
    still tied are settled by `choose`, which the caller supplies (the server passes
    a random choice, tests pass a controlled one). Abstentions are simply absent
    from the totals."""
    candidates = _leaders(SLOTS, vote2)
    if len(candidates) == 1:
        return candidates[0], "vote2"
    candidates = _leaders(candidates, vote1)
    if len(candidates) == 1:
        return candidates[0], "vote1"
    return choose(candidates), "random"


def _leaders(slots: Sequence[int], totals: dict[int, int]) -> list[int]:
    best = max(totals.get(slot, 0) for slot in slots)
    return [slot for slot in slots if totals.get(slot, 0) == best]
