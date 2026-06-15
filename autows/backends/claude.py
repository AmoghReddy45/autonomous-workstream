"""Claude Code backend — the reference implementation.

`claude -p` runs a one-shot non-interactive session; --allow-dangerously-skip-
permissions is what makes it autonomous (and is exactly why the safety rails in
SECURITY.md exist). The prompt is supplied on stdin by the process layer.
"""
from .base import Backend


class ClaudeBackend(Backend):
    name = "claude"

    def command(self):
        return ["claude", "-p", "--allow-dangerously-skip-permissions"]
