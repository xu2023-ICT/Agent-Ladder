"""Reduced version of opencode's tool/truncate.ts service."""

MAX_OUTPUT_CHARS = 20_000


def output(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    hidden = len(text) - MAX_OUTPUT_CHARS
    return f"{text[:MAX_OUTPUT_CHARS]}\n...[truncated, {hidden} more chars]"
