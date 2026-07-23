"""opencode-style tool definition schema."""

DEFAULT_TIMEOUT = 120
NAME = "bash"

DESCRIPTION = (
    "Run a shell command and get back its combined stdout+stderr. This is the only "
    "tool available -- use it for everything: listing files (ls), reading files "
    "(cat), searching (grep), editing (sed), running tests, and any other terminal "
    "operation. Each call starts a fresh, non-interactive shell: nothing persists "
    "between calls (no cwd, no environment variables, no shell history), so chain "
    "related commands in one call with `&&`/`;`/`|` rather than relying on state "
    "left over from a previous call."
)

SCHEMA = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Full shell command string to run, e.g. `ls -la` or `pytest tests/ -x`.",
                },
                "timeout": {
                    "type": "number",
                    "description": f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
                },
            },
            "required": ["command"],
        },
    },
}
