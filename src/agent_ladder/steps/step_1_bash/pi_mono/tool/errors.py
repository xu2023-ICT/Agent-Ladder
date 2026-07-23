"""Error shape used by the pi-mono-style loop boundary."""


class BashError(Exception):
    """A command that timed out or exited non-zero."""

    def __init__(self, message: str, output: str):
        super().__init__(message)
        self.output = output
