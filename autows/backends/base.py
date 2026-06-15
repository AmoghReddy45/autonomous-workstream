"""Backend interface (SPEC section 5).

The ONLY backend-specific operation is "spawn one headless agent". Everything
else in the pattern (timeout/process-tree kill, audit log, branch policy, hooks,
Q&A protocol) is backend-neutral and implemented once, here and in the CLI.

To add a backend, subclass Backend and implement command(); register it in
backends/__init__.py.
"""
import os
from dataclasses import dataclass

from .. import process


@dataclass
class SpawnResult:
    stdout: str
    exit_code: int
    timed_out: bool


class Backend:
    name = "base"

    def command(self):
        """argv to launch the agent non-interactively, reading the prompt from stdin."""
        raise NotImplementedError

    def env(self) -> dict:
        """Environment for the child, with the headless markers set.

        Setting the markers here is what lets the pre-push hook (SPEC S1)
        distinguish autonomous sessions from operator terminals.
        """
        e = os.environ.copy()
        e["AUTOWS_HEADLESS"] = "1"
        e["CLAUDE_HEADLESS"] = "1"  # back-compat with legacy hooks
        return e

    def spawn_headless(self, prompt: str, timeout_seconds: int) -> SpawnResult:
        out, code, timed = process.run_with_timeout(
            self.command(), prompt, timeout_seconds, env=self.env()
        )
        return SpawnResult(stdout=out, exit_code=code, timed_out=timed)
