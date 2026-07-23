"""pi-mono bash tool definition."""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Execute a bash command in the current working directory. Returns "
            "stdout and stderr combined. Output longer than a few KB is "
            "truncated to the tail (full output saved to a temp file, path "
            "included). Optionally provide a timeout in seconds. This is the "
            "only tool available -- use it for everything: listing files (ls), "
            "reading files (cat), searching (grep), editing (sed, heredocs), "
            "and running tests. Each call starts a fresh shell: nothing "
            "(working directory, environment variables, background jobs) "
            "persists between calls, so chain related commands with && / ; / |."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Bash command to execute"},
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional, no default timeout)",
                },
            },
            "required": ["command"],
        },
    },
}
