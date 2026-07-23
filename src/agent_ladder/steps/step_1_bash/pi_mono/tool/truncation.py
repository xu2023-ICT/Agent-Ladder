"""Tail truncation, matching pi-mono's bash-output preference."""

MAX_OUTPUT_BYTES = 20_000


def truncate_tail(output: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    data = output.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return output

    tail = data[-max_bytes:].decode("utf-8", errors="ignore")
    return f"[... output truncated to the last {max_bytes} bytes ...]\n{tail}"
