# Autonomous Workstream

**Run an AI coding agent autonomously across a whole multi-step workstream — safely.**

One operator-launched **Terminal** session spawns **headless phase sessions** (one per
sub-task), each of which spawns **workers**. Every sub-task gets a clean, fresh agent
context — so you keep session-led quality — while you launch *one* session per workstream
instead of babysitting one per sub-task. A structural safety rail keeps unattended
sessions on feature branches and off your protected branches.

> [!WARNING]
> This tool runs an AI coding agent **with permission checks disabled**, unattended.
> That is powerful and genuinely dangerous. **Read [SECURITY.md](SECURITY.md) before your
> first autonomous run** — the safety model (feature-branch-only pushes, a pre-push hook,
> origin branch protection, an audit log, and hard-stops) is what makes this acceptable.
> Do not run unattended without origin-side branch protection on your protected branches.

---

## Why this exists

A normal agent session is great for one task: you launch it, watch it, answer its
questions, close it. That doesn't scale to a workstream with a dozen sub-tasks spread over
days. This pattern lets you say *"complete this whole workstream"* once. The Terminal then
launches its own sessions, checks each one's work, and only comes back to you at meaningful
checkpoints (phase boundaries) or when it hits something it genuinely shouldn't decide
alone.

## The mental model (three layers)

```
Architect chat    strategic; writes the Terminal prompt; answers escalations
   │
   ▼  (operator pastes prompt)
Terminal          ONE operator-launched interactive session per workstream.
   │              Spawns + verifies sub-sessions. Lives hours-to-days.
   ▼  (spawn a headless session, in background)
Headless phase    autonomous agent. Does ONE bounded sub-task. Commits to a
session           feature branch. CANNOT push to protected branches.
   │
   ▼  (subagent)
Workers           scoped subagents doing the actual implementation.
```

Read [`SPEC.md`](SPEC.md) for the tool-agnostic pattern, or the bundled skill docs for the
hands-on guide: [`SKILL.md`](skills/autonomous-workstream/SKILL.md),
[`OPERATOR_GUIDE.md`](skills/autonomous-workstream/OPERATOR_GUIDE.md),
[`TROUBLESHOOTING.md`](skills/autonomous-workstream/TROUBLESHOOTING.md).

## Status

This is an early public release. Be honest about what works today:

| Area | Today (v0.1) | On the roadmap |
| --- | --- | --- |
| Agent backend | Claude Code (`claude -p`) | Codex + a documented backend interface |
| OS / runtime | Windows / PowerShell scripts | One cross-platform CLI (Python) |
| Packaging | Claude Code plugin (this repo) | published marketplace listing |
| Learning | none (each session starts cold) | accumulating lessons + a guarded self-improving loop |

See [Roadmap](#roadmap).

## Install (Claude Code plugin)

Once this repo is public on GitHub:

```
/plugin marketplace add AmoghReddy45/autonomous-workstream
/plugin install autonomous-workstream@autonomous-workstream
/reload-plugins
```

Then invoke the skill from any project: ask Claude to "set up an autonomous workstream" or
"write a Terminal prompt for ...".

**Manual install (no plugin):** copy `skills/autonomous-workstream/` into your global
skills directory, and copy the scripts from `skills/autonomous-workstream/assets/scripts/`
into your project's `scripts/`. See
[`assets/SETUP.md`](skills/autonomous-workstream/assets/SETUP.md).

## Bootstrapping a project

~10 minutes, one-time per repo. Full steps in
[`assets/SETUP.md`](skills/autonomous-workstream/assets/SETUP.md):

1. Copy the scripts into your project's `scripts/`.
2. Gitignore `data/automation/` (runtime audit + Q&A artifacts).
3. Install the pre-push safety hook (`install_safety_hooks.ps1`).
4. **Strongly recommended:** turn on origin-side branch protection for `main`/`dev`.
5. Smoke-test with a trivial headless session.

## Repository layout

```
.claude-plugin/        plugin.json + marketplace.json (Claude Code install)
skills/
  autonomous-workstream/
    SKILL.md           quick model + launch checklist + core commands
    OPERATOR_GUIDE.md  full mental model, safety architecture, autonomy modes
    TROUBLESHOOTING.md fixes for every failure mode observed
    assets/
      SETUP.md         bootstrap a new repo
      scripts/         PowerShell scripts + embedded pre-push hook
SPEC.md                the tool-agnostic pattern (implement it on any backend)
SECURITY.md            threat model + the controls that mitigate it
LICENSE                Apache-2.0
```

## Roadmap

- **Phase 0 — Foundation** ✅ — git, license, README, security model, spec, plugin packaging.
- **Phase 1 — Cross-platform core** — consolidate the orchestration into one cross-platform
  CLI with a backend seam; keep the bash pre-push hook; deprecate the `.ps1` scripts.
- **Phase 2 — Backends** — a Codex adapter + a documented "add your own backend" interface.
- **Phase 3 — Lessons memory** — an accumulating, version-controlled `LESSONS.md` (+ raw
  append-only log) read at session bootstrap, written at completion, curated at phase
  boundaries. Inspired by autoresearch-style experiment journals.
- **Phase 4 — Self-improving loop (guarded)** — the agent proposes improvements to its own
  prompt templates/heuristics on a feature branch, operator-gated, with the **safety core
  frozen and untouchable** (see [SECURITY.md](SECURITY.md)).
- **Phase 5 — Tests / CI** — run the pre-push hook test vectors and a CLI smoke test in CI.

## License

[Apache-2.0](LICENSE). Note the strong **AS-IS / no-warranty** disclaimer — fitting for a
tool that runs an agent unattended. You are responsible for what you run.
