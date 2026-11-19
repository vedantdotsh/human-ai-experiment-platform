class Rejected(Exception):
    """An action that was refused. The reason is sent to the sender only and the
    attempt is never written to the event log."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
