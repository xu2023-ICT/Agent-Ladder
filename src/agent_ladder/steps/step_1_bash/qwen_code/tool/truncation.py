"""Small equivalent of qwen-code's per-tool output truncation budget."""

MAX_OUTPUT_CHARS = 30_000


def truncate_tool_output(output: str) -> str:
    if len(output) <= MAX_OUTPUT_CHARS:
        return output
    hidden = len(output) - MAX_OUTPUT_CHARS
    return f"{output[:MAX_OUTPUT_CHARS]}\n...[truncated, {hidden} more chars]"
