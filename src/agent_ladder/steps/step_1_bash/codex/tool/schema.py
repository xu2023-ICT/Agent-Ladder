"""Codex shell_command schema."""

NAME = "shell_command"
DEFAULT_TIMEOUT_SECONDS = 60
MAX_OUTPUT_CHARS = 10_000

DESCRIPTION = (
    "Runs a shell command and returns its output. This is the only tool "
    "available -- use it for everything: listing files, reading files, "
    "searching, editing (e.g. via sed or python -c), and running tests. "
    "Always set the `workdir` param instead of `cd`-ing inside the command: "
    "each call is a fresh, non-interactive login shell, so nothing persists "
    "between calls (no cwd, no env vars, no shell history) -- chain related "
    "commands in one call with `&&`/`;`/`|` instead of relying on state left "
    "over from a previous call."
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
                    "description": "The shell script to execute in the user's default shell.",
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory to run the command in; defaults to the process cwd.",
                },
                "timeout": {
                    "type": "number",
                    "description": f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT_SECONDS}.",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
}
