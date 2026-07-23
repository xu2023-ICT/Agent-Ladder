"""minicode's bash tool: schema and execution split into their own modules.

No specific real agent to mirror here, so this split is just the minimal
sensible shape -- one module for what the model is told, one for what
actually runs -- the same schema/execution separation every sibling agent
folder uses under its own `tool/`.
"""

from agent_ladder.steps.step_1_bash.minicode.tool.schema import BASH_TOOL, DEFAULT_TIMEOUT
from agent_ladder.steps.step_1_bash.minicode.tool.shell import MAX_OUTPUT_CHARS, run_bash

__all__ = ["BASH_TOOL", "DEFAULT_TIMEOUT", "MAX_OUTPUT_CHARS", "run_bash"]
