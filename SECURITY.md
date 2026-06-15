# Security & Threat Model

Read this before running anything unattended. This project orchestrates an AI coding agent
running **with permission checks disabled** (`--allow-dangerously-skip-permissions` or the
equivalent on your backend). That is the whole point — and the whole risk. The controls
below are what make autonomous operation acceptable rather than reckless.

## What an unattended session can do

A headless phase session has, by design, broad capability:

| Capability | Headless session |
| --- | --- |
| Read any file in the working tree | yes |
| Edit any file | yes |
| Run any shell command (including destructive ones) | **yes — this is the real risk** |
| Spawn its own subagents | yes |
| Commit to a `feature/*` branch | yes |
| Push `feature/*` to origin | yes |
| Commit to `main`/`dev` locally | technically yes; cannot *push* them |
| Push to `main`/`dev` | **NO** — blocked by the pre-push hook; origin protection is the backstop |
| Force-push / delete protected branches on origin | **NO** if origin branch protection is configured |

## The genuine residual risks

These are mitigated by scoping + review, not eliminated. Know them:

1. **Destructive shell commands.** A session can run `rm -rf`, drop a database, etc. Scope
   work tightly; review diffs before promoting; never point an unattended run at
   irreplaceable state.
2. **Unbounded external spend.** A session can hit paid APIs in a loop. Use sandbox keys,
   spend caps, and the hard-stop "would spend real money / hit a non-sandbox endpoint."
3. **Prompt injection from files the session reads.** A malicious string in a dependency, a
   README, an issue, or test data can hijack the agent's instructions. Treat any repo with
   untrusted content as higher-risk; prefer running on trusted code.
4. **Shared external state.** If the work touches a resource other processes rely on (a
   shared sandbox account, a shared DB), an unattended run can corrupt it. Build + test
   against mocks autonomously; defer the live step to a supervised session.

## The controls (defense in depth)

1. **Feature-branch-only policy.** Headless sessions commit and push to `feature/*` only.
2. **Pre-push hook.** A local `pre-push` hook rejects pushes to `main`/`dev` when the
   `CLAUDE_HEADLESS=1` env var is set (the spawn wrapper sets it; an operator's interactive
   terminal does not). Installed by `install_safety_hooks.ps1`.
3. **Origin-side branch protection — the only non-bypassable layer.** The local hook is
   bypassable (a misbehaving session could remove it or use `--no-verify`). Origin-side
   protection on your git host is the one control a session cannot defeat. **Turn it on.**
   If your host gates it behind a paid tier, decide consciously: pay, make the repo public,
   or accept local-hook-only protection *and actively watch every run*.
4. **The spawn wrapper is the only sanctioned entry.** It sets the headless marker, enforces
   a timeout with a process-tree kill, and writes an audit record. Anything spawned outside
   it bypasses the audit trail — treat unaccounted-for commits as a red flag.
5. **Audit log.** Every spawn + completion is logged (git state before/after, duration, exit
   code) under `data/automation/headless_log/`.
6. **Hard-stops.** In unattended mode the session stops rather than guess on a short list of
   irresponsible-to-guess conditions (missing credentials, would touch protected/frozen
   files, would spend real money, scope ballooning, would mutate shared external state).
7. **Operator review before promotion.** Autonomous work stages on feature branches; a human
   is the final gate before anything reaches `main`/`dev`.
8. **Frozen-state guard (if your project has one).** Any guard that refuses promotion on
   protected-file drift catches a session that oversteps its scope.

## The frozen safety core (important for the self-improving roadmap)

A future phase lets the agent improve **its own prompt templates and heuristics** across
runs. That capability must never be allowed to weaken its own safety rails. The design
constraint is absolute:

- The **safety core is frozen**: the pre-push hook, the `CLAUDE_HEADLESS` handling, and the
  spawn wrapper's timeout/audit logic are checksummed and **off-limits** to any
  self-improvement loop.
- Self-improvement may touch **only** prompt templates, lessons, and heuristics, on a
  feature branch, **operator-gated** — never auto-applied to the running safety config.
- The frozen-state guard fails any run in which the safety core has drifted.

If you build on this project, preserve that boundary.

## Reporting a vulnerability

Please report security issues privately to **reddy.amogh2004@gmail.com** rather than opening
a public issue. Include reproduction steps and the impact you observed. (Maintainers: update
this address to a dedicated security contact before wide distribution.)
