"""Codex CLI backend.

`codex exec` runs a one-shot non-interactive session. The trailing `-` forces
Codex to read the prompt from stdin (which is how the process layer feeds it);
`--dangerously-bypass-approvals-and-sandbox` is Codex's equivalent of running
fully unattended (no approval prompts, no sandbox) — see SECURITY.md for why
that's gated behind the same safety rails as the Claude backend.

Codex `exec` has no nested-subagent primitive, so per SPEC section 6 the phase
session completes worker deliverables itself (supports_subagents = False).
"""
from .base import Backend


class CodexBackend(Backend):
    name = "codex"
    supports_subagents = False

    def command(self):
        return ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "-"]
