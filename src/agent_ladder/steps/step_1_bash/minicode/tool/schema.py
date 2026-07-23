"""The `bash` tool's schema: name, description, parameter shape."""

DEFAULT_TIMEOUT = 60  # seconds

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Run a bash command and return its output. This is the only tool "
            "available -- use it for everything: listing and reading files, "
            "searching, editing (e.g. with sed or a heredoc), running tests, "
            "checking git status, and so on. stdout and stderr are merged into "
            "a single string; if the command exits non-zero, the exit code is "
            "appended after the output. Each call runs in a brand new shell -- "
            "the working directory, environment variables, and shell history "
            "are NOT preserved between calls -- so chain related commands in "
            "one call with `&&`, `;`, or `|` instead of relying on state from "
            "a previous call."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
                },
            },
            "required": ["command"],
        },
    },
}
