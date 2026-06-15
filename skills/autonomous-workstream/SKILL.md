---
name: autonomous-workstream
description: Launch, manage, or troubleshoot an autonomous workstream — an operator-launched "Terminal" Claude that spawns headless phase sessions to complete a whole multi-step workstream hands-off, with feature-branch-only safety and a file-based Q&A protocol. Works in any git project. Invoke when setting up autonomous Claude execution, writing a Terminal prompt, bootstrapping the infrastructure in a new repo, interpreting a morning report, or diagnosing a stuck/hung autonomous run.
---

# Autonomous Workstream

A portable pattern for running Claude Code autonomously on a multi-step
workstream: one operator-launched **Terminal** session spawns **headless
phase sessions**, each of which spawns **workers**, all while structural
safety prevents headless sessions from touching protected branches.

This skill is project-agnostic. The reference implementation was built
in a quant-trading repo, but nothing here is language- or domain-bound.

- `OPERATOR_GUIDE.md` — full mental model, safety architecture, autonomy
  modes, anatomy of a Terminal prompt, morning-report handling.
- `TROUBLESHOOTING.md` — concrete fixes for every failure mode seen.
- `assets/SETUP.md` — how to bootstrap the infrastructure in a NEW repo.
- `assets/scripts/` — portable PowerShell scripts + git hook to copy in.

## The mental model (three layers)

```
Architect chat        strategic; writes the Terminal prompt; answers
   │                  architectural escalations (supervised mode only)
   ▼ (operator pastes prompt)
Terminal              ONE operator-launched interactive Claude per
   │                  workstream/phase. Spawns + verifies sub-sessions.
   ▼ (spawn_phase_session.ps1, run_in_background)
Headless phase        autonomous `claude -p --allow-dangerously-skip-
session               permissions`. Does one bounded sub-task. Commits
   │                  to a feature branch. Cannot push to main/dev.
   ▼ (Agent tool)
Workers               scoped subagents doing the actual implementation.
```

Why this shape: each sub-task still gets a clean session (own context,
own journal entry) — preserving session-led quality — while the operator
launches ONE session per workstream instead of one per sub-task.

## Safety model (the load-bearing parts)

1. **Branch policy**: headless sessions commit + push to `feature/*`
   ONLY. A local `pre-push` hook rejects pushes to `main`/`dev` when the
   `CLAUDE_HEADLESS=1` env var is set (the spawn wrapper sets it;
   operator interactive terminals don't). If your git host supports it,
   add origin-side branch protection as a second, non-bypassable layer.
2. **Wrapper is the only sanctioned entry**: `spawn_headless_session.ps1`
   sets the env var, enforces a timeout with process-tree kill, and
   writes an audit log. Anything not spawned through it bypasses the
   audit trail.
3. **Frozen-state verifier (if the project has one)**: any guard that
   refuses promotion on protected-file drift is equally load-bearing
   for headless sessions — they break it visibly if they overstep.
4. **Audit log**: every invocation logs spawn + completion (git state
   before/after, duration, exit code) under `data/automation/headless_log/`.
5. **Operator review before merge to main/dev**: autonomous work stages
   on feature branches; the operator is the final gate.

## When to invoke this skill

- Bootstrapping the pattern in a new repo → see `assets/SETUP.md`
- Writing a Terminal prompt for a specific workstream/phase
- A Terminal finished and left a morning report to interpret
- An autonomous run is stuck, hung, or behaving oddly → `TROUBLESHOOTING.md`

## Decision: which autonomy mode?

| Mode | When | Q&A behavior |
| --- | --- | --- |
| **Supervised** | First runs of a new pattern; high-stakes; operator awake | Phase sessions surface questions via the file inbox; operator answers (tactical) or routes architectural ones to architect chat |
| **Best-judgment** | Operator away; well-understood work; decisions pre-bakeable | Phase sessions decide + document; Terminal answers stray questions itself using pre-baked decisions; only HARD-STOP conditions halt the run |

Best-judgment mode REQUIRES, in the Terminal prompt: (a) the
architectural decisions pre-baked so sub-sessions don't need to ask, and
(b) hard-stop conditions — the few cases where guessing is irresponsible
(missing credentials, would spend real money, would touch protected/
frozen files, scope ballooning, would touch shared external state). See
OPERATOR_GUIDE.md §"Autonomy modes".

## Launch checklist (verify before any autonomous run)

```
[ ] pre-push hook installed (.git/hooks/pre-push exists)
[ ] hook blocks headless→protected:
      echo "refs/heads/main abc refs/heads/main def" | CLAUDE_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"
      → must print EXIT=1
[ ] claude CLI on PATH (claude --version)
[ ] any external tool the phase needs is on PATH
[ ] project's pre-flight / verifier (if any) is green
[ ] NO other coordinator session running in this working tree
      (shared-tree collisions — see TROUBLESHOOTING.md)
[ ] if best-judgment/unattended: hard-stops defined + shared-external-
      state risk considered
```

## Core commands

Spawn a phase session (the Terminal runs this, in background):
```powershell
.\scripts\spawn_phase_session.ps1 `
    -Workstream "<name>" -Phase <N> -SessionInPhase <K> `
    -Scope "<1-3 sentence bounded scope>" `
    -PhaseSpecificGuidance "<doc refs, prior commits, pre-baked decisions>" `
    -WorkerType "<subagent type or general-purpose>" `
    -GateCommands "<the project's build/test/lint gates>"
```

Inject an off-PATH tool for the headless child (do NOT edit scripts/):
```powershell
# data/automation/_launch_<label>.ps1  (gitignored)
$env:SOMETOOL = "C:\path\to\tool.exe"; $env:PATH = "C:\path\to\bin;" + $env:PATH
& .\scripts\spawn_phase_session.ps1 -Workstream "..." -Phase 1 -SessionInPhase 1 -Scope "..." -PhaseSpecificGuidance "..."
```

Answer a phase session's question (supervised mode):
```powershell
.\scripts\answer_question.ps1 -QFile "data\automation\inbox\Q_<id>_001.json" -Answer "..." -Rationale "..." -SignedBy "operator"
.\scripts\answer_question.ps1 -QFile "data\automation\inbox\Q_<id>_001.json" -ShowOnly   # surface architectural Q
```

Watch the inbox (the Terminal starts this as a persistent Monitor):
```bash
seen="/tmp/inbox_seen_$$.txt"; touch "$seen"; while true; do for q in data/automation/inbox/Q_*.json; do [ -f "$q" ] || continue; if ! grep -qFx "$q" "$seen"; then echo "Q_NEW: $q"; echo "$q" >> "$seen"; fi; done; sleep 30; done
```
