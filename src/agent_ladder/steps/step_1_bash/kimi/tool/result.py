"""Tiny stand-in for kimi-cli's ToolResultBuilder."""

MAX_OUTPUT_CHARS = 20_000


class ToolResultBuilder:
    def __init__(self):
        self._chunks: list[str] = []

    def write(self, text: str) -> None:
        self._chunks.append(text)

    def output(self) -> str:
        text = "".join(self._chunks)
        if len(text) <= MAX_OUTPUT_CHARS:
            return text
        hidden = len(text) - MAX_OUTPUT_CHARS
        return f"{text[:MAX_OUTPUT_CHARS]}\n[...truncated, {hidden} more chars]"
