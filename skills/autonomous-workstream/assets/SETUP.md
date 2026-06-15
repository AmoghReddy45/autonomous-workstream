# Bootstrapping the Autonomous Workstream pattern in a new repo

One-time setup to make a git project ready for autonomous workstream
runs. ~10 minutes.

> **Cross-platform path (recommended):** instead of the PowerShell scripts
> below, install the `autows` CLI (`pipx install git+https://github.com/AmoghReddy45/autonomous-workstream`)
> and use `autows install-hooks`, `autows phase ...`, `autows answer ...`,
> `autows spawn ...`. It works on macOS/Linux/Windows with zero dependencies and
> the safety model is identical. The steps below are the Windows-native /
> no-Python path. See the repo README, "Using the CLI".

## 0. Prerequisites

- Claude Code CLI on PATH (`claude --version`).
- A git repo with a `main` (and optionally `dev`) branch.
- PowerShell (the scripts are PowerShell; the hook is bash, run by Git
  for Windows / git's hook runner on any platform).

## 1. Copy the scripts in

Copy the four scripts from this skill's `assets/scripts/` into your
project's `scripts/` directory:

```
scripts/spawn_headless_session.ps1
scripts/spawn_phase_session.ps1
scripts/answer_question.ps1
scripts/install_safety_hooks.ps1
```

## 2. Gitignore the runtime artifacts

Ensure `data/` (or at least `data/automation/`) is gitignored — it
holds the audit log + Q&A files, which are runtime artifacts:

```
# .gitignore
data/automation/
```

## 3. Install the pre-push safety hook

```powershell
.\scripts\install_safety_hooks.ps1
```

This writes `.git/hooks/pre-push`, which blocks pushes to `main`/`dev`
when `CLAUDE_HEADLESS=1` is set. Verify:

```bash
echo "refs/heads/main abc refs/heads/main def" | CLAUDE_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"   # expect 1
echo "refs/heads/feature/x abc refs/heads/feature/x def" | CLAUDE_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"   # expect 0
echo "refs/heads/main abc refs/heads/main def" | bash .git/hooks/pre-push; echo "EXIT=$?"   # operator push: expect 0
```

## 4. (Strongly recommended) Origin-side branch protection

The local hook is bypassable. Add origin branch protection on `main`
and `dev` so a misbehaving session can't reach them even if it removes
the hook:

- GitHub: Settings → Branches → add protection (require PR; block force
  pushes + deletions). Note: on some plans this requires a paid tier
  for private repos. If unavailable, you're relying on the local hook +
  operator monitoring only — acceptable only when you actively watch
  runs.

## 5. (Optional) Customize protected branches

If your project protects branches other than `main`/`dev`, edit the
`$protected_branches` array in `.git/hooks/pre-push` after installing.

## 6. Tell Claude about the pattern

Add a pointer in your project's `CLAUDE.md` so any session knows the
pattern is available, e.g.:

```
## Autonomous execution
This repo supports the Autonomous Workstream pattern (global skill
`autonomous-workstream`). Headless phase sessions commit to feature/*
only; the pre-push hook blocks protected-branch pushes. See
scripts/spawn_phase_session.ps1.
```

## 7. Smoke test

Spawn a trivial phase session to confirm the wiring:

```powershell
.\scripts\spawn_headless_session.ps1 -Prompt "Respond with exactly: SETUP_OK" -SessionLabel "smoke-test" -TimeoutSeconds 120
```

Expect `SETUP_OK` on stdout and a new file under
`data/automation/headless_log/`.

You're ready. Use the `autonomous-workstream` skill to write a Terminal
prompt for your first real workstream.

## Project-specific knobs

The scripts are generic. Per project, you'll typically specify at spawn
time:

- `-WorkerType` — the subagent type your phase sessions should spawn
  (e.g. a project-specific implementer agent, or `general-purpose`).
- `-GateCommands` — your project's build/test/lint gates (e.g.
  `cargo build && cargo test && cargo clippy -- -D warnings`, or
  `npm run build && npm test && npm run lint`, or
  `pytest -q && ruff check`).
- `-BranchPrefix` — default `feature`.

These keep the scripts language-agnostic while each run stays
project-correct.
