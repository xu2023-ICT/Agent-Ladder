"""Small OutputAccumulator inspired by pi-mono's streaming collector."""

import tempfile

from agent_ladder.steps.step_1_bash.pi_mono.tool.truncation import MAX_OUTPUT_BYTES, truncate_tail


class OutputAccumulator:
    def __init__(self, temp_file_prefix: str = "agent-ladder-bash"):
        self._chunks: list[str] = []
        self._temp_file_prefix = temp_file_prefix

    def append(self, text: str) -> None:
        self._chunks.append(text)

    def snapshot(self, persist_if_truncated: bool = False) -> str:
        output = "".join(self._chunks)
        truncated = truncate_tail(output)
        if output == truncated:
            return output

        if not persist_if_truncated:
            return truncated

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix=f"{self._temp_file_prefix}-", delete=False
        ) as f:
            f.write(output)
            full_output_path = f.name

        return (
            f"[... output truncated to the last {MAX_OUTPUT_BYTES} bytes. "
            f"Full output: {full_output_path} ...]\n"
            f"{truncated.split('\\n', 1)[-1]}"
        )
