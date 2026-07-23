"""Claude Code style Bash tool schema."""

NAME = "bash"
DEFAULT_TIMEOUT = 120
MAX_OUTPUT_CHARS = 30_000

DESCRIPTION = (
    "Run a shell command and get back its output. This is the only tool "
    "available: use it for everything -- listing and reading files, "
    "searching, editing with sed/heredocs, running tests, and so on. Each "
    "call starts a fresh, non-interactive shell process -- environment "
    "variables, aliases, and shell functions do NOT persist between calls -- "
    "but the working directory does (a `cd` in one call affects the next)."
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
                    "description": "The shell command to run.",
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
