"""Minimal cwd state for the Claude Code style Bash tool."""

from dataclasses import dataclass


@dataclass
class BashState:
    cwd: str
