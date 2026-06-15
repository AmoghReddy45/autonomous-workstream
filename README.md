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
| Agent backend | Claude Code (`claude -p`) + Codex (`codex exec`) | more backends via the documented interface |
| OS / runtime | Cross-platform `autows` CLI (Python 3.9+, zero deps); PowerShell scripts (legacy) | broaden the CI test matrix |
| Packaging | Claude Code plugin + `pip`/`pipx` install | published marketplace + PyPI |
| Learning | lessons memory (`autows lessons add/show`) — read at bootstrap, written at completion | a guarded self-improving loop |

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

## Using the CLI (cross-platform)

`autows` is a zero-dependency Python CLI (3.9+) that works on macOS, Linux, and
Windows. Install it:

```
pipx install git+https://github.com/AmoghReddy45/autonomous-workstream
# or, from a clone:  pip install -e .
```

Then, from inside your project (a git repo):

```
autows install-hooks                         # one-time: install the pre-push safety hook
autows phase --workstream rust --phase 2 --session-in-phase 1 \
    --scope "Implement crate X ..." \
    --guidance "doc refs; pre-baked decisions; best-judgment mode" \
    --gate-commands "cargo build && cargo test && cargo clippy -- -D warnings"
autows answer --qfile data/automation/inbox/Q_<id>_001.json --answer "..." --rationale "..."
autows spawn  --prompt "..." --label my-task   # low-level single session
autows lessons show                            # read accumulated lessons (sessions do this at bootstrap)
autows lessons add --category gotcha --text "protoc must be on PATH"   # record one for next time
```

The command is `autows` (not `aws`, to avoid colliding with the Amazon CLI). It's
the cross-platform replacement for the four PowerShell scripts; Windows users
without Python can still use those scripts in
`skills/autonomous-workstream/assets/scripts/`.

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
autows/                the cross-platform CLI (backend seam, process watchdog, hooks, lessons)
  backends/            claude.py + codex.py + the Backend interface (add your own)
pyproject.toml         packaging — `pipx install` gives the `autows` command
tests/                 hook test vectors + process-watchdog smoke tests
skills/
  autonomous-workstream/
    SKILL.md           quick model + launch checklist + core commands
    OPERATOR_GUIDE.md  full mental model, safety architecture, autonomy modes
    TROUBLESHOOTING.md fixes for every failure mode observed
    assets/
      SETUP.md         bootstrap a new repo
      scripts/         PowerShell scripts + embedded pre-push hook (legacy)
SPEC.md                the tool-agnostic pattern (implement it on any backend)
SECURITY.md            threat model + the controls that mitigate it
LICENSE                Apache-2.0
```

## Roadmap

- **Phase 0 — Foundation** ✅ — git, license, README, security model, spec, plugin packaging.
- **Phase 1 — Cross-platform core** ✅ — the zero-dependency `autows` Python CLI with a
  backend seam, a cross-platform process-tree-kill watchdog, and the bash pre-push hook;
  the `.ps1` scripts are now legacy.
- **Phase 2 — Backends** ✅ — a Codex adapter (`--backend codex`) + the documented
  "add your own backend" interface ([`autows/backends/README.md`](autows/backends/README.md)).
  Codex has no subagent primitive, so its phase sessions self-execute (SPEC §6).
- **Phase 3 — Lessons memory** ✅ — `autows lessons add/show`: a raw append-only log plus a
  curated, version-controlled `docs/journal/LESSONS.md`, read at session bootstrap, written at
  completion, curated at phase boundaries. Inspired by autoresearch-style experiment journals.
- **Phase 4 — Self-improving loop (guarded)** — the agent proposes improvements to its own
  prompt templates/heuristics on a feature branch, operator-gated, with the **safety core
  frozen and untouchable** (see [SECURITY.md](SECURITY.md)).
- **Phase 5 — Tests / CI** — run the pre-push hook test vectors and a CLI smoke test in CI.

## License

[Apache-2.0](LICENSE). Note the strong **AS-IS / no-warranty** disclaimer — fitting for a
tool that runs an agent unattended. You are responsible for what you run.
