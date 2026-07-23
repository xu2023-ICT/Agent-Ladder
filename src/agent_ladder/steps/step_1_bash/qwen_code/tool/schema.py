"""qwen-code style declarative shell tool schema."""

DEFAULT_TIMEOUT_SECONDS = 120
MAX_TIMEOUT_SECONDS = 600

NAME = "run_shell_command"

DESCRIPTION = (
    "Execute a shell command and return its output. This is the only tool "
    "available, so use it for everything a terminal can do -- listing and "
    "reading files (ls/cat), searching (grep), editing (sed), running "
    "tests, git, etc. -- not just for things that look like build/test "
    "commands. Output is stdout and stderr merged into a single string, "
    "followed by the exit code. Each call runs in a brand-new shell: "
    "nothing from a previous call carries over (no cwd, no environment "
    "variables, no shell history), so chain related steps in one call with "
    "`&&`/`;`/`|` rather than assuming state left over from an earlier "
    "call. If several commands are independent of each other, prefer "
    "issuing them as separate tool calls in the same turn instead of "
    "chaining them; only chain when a later command actually depends on an "
    "earlier one succeeding."
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
                    "description": "Exact shell command to execute, e.g. `pytest tests/ -x`.",
                },
                "timeout": {
                    "type": "number",
                    "description": (
                        f"Timeout in seconds (default {DEFAULT_TIMEOUT_SECONDS}, "
                        f"max {MAX_TIMEOUT_SECONDS})."
                    ),
                },
            },
            "required": ["command"],
        },
    },
}
