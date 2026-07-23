"""kimi-cli Shell parameter declaration, minimized for step 1."""

DEFAULT_TIMEOUT = 60
MAX_FOREGROUND_TIMEOUT = 5 * 60

NAME = "Shell"

DESCRIPTION = (
    "Execute a bash command and return its output. This is the only tool "
    "available -- use it to explore the filesystem, read and edit files, run "
    "scripts and tests, check git status, and anything else a terminal can "
    "do. stdout and stderr are combined into a single string; if the command "
    "fails, the exit code is appended after the output. Each call runs in a "
    "fresh shell -- shell variables, cwd changes, and history are NOT "
    "preserved between calls -- so chain related commands with `&&`, `;`, "
    "`|`, or a `for`/`while` loop in one call instead of relying on state "
    "from a previous call. Avoid interactive or possibly-never-returning "
    "commands, and set `timeout` for anything that might run long."
)

SCHEMA = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute."},
                "timeout": {
                    "type": "integer",
                    "description": (
                        f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}, "
                        f"capped at {MAX_FOREGROUND_TIMEOUT}."
                    ),
                },
            },
            "required": ["command"],
        },
    },
}
