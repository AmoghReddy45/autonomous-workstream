# Backends

A backend is the one tool-specific part of the pattern (SPEC §5): **"spawn one
headless agent."** Everything else — the timeout/process-tree-kill watchdog, the
audit log, the branch policy, the pre-push hook, the Q&A protocol — is shared and
lives outside this folder.

## Built-in backends

| name | command | subagents? |
| --- | --- | --- |
| `claude` | `claude -p --allow-dangerously-skip-permissions` (prompt on stdin) | yes |
| `codex` | `codex exec --dangerously-bypass-approvals-and-sandbox -` (prompt on stdin) | no |

Select one with `--backend` on `autows spawn` / `autows phase`.

## Adding a backend

1. Create `autows/backends/<name>.py`:

   ```python
   from .base import Backend

   class MyBackend(Backend):
       name = "mybackend"
       supports_subagents = False  # True only if it can spawn nested agents

       def command(self):
           # argv to run the agent NON-interactively with approvals/sandbox
           # disabled, reading the prompt from stdin. Return a list (no shell).
           return ["myagent", "run", "--yes", "--stdin"]
   ```

2. Register it in `__init__.py`:

   ```python
   from .mybackend import MyBackend
   _BACKENDS = {..., MyBackend.name: MyBackend}
   ```

3. That's it — `--backend mybackend` now works everywhere.

## Contract (what `command()` must guarantee)

- **Prompt on stdin, untruncated.** The process layer feeds the prompt via a temp
  file on stdin. If your tool needs a positional prompt arg, prefer its
  "read from stdin" form (e.g. Codex's trailing `-`); passing a multi-line prompt
  as a list element is also safe (no shell is involved), but stdin is preferred.
- **Non-interactive, unattended.** No approval prompts, no sandbox that would
  block file edits or commits. This is exactly the capability SECURITY.md's rails
  exist to contain — the env markers (`AUTOWS_HEADLESS` / `CLAUDE_HEADLESS`) set by
  `Backend.env()` are what let the pre-push hook block protected-branch pushes.
- **Set `supports_subagents` honestly.** If the tool can't spawn nested agents, the
  phase prompt automatically tells the session to do worker deliverables itself
  (SPEC §6). Quality may be lower than a backend with real subagents — say so.
