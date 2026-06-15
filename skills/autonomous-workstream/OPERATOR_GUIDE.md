# Autonomous Workstream — Operator Guide

A complete, project-agnostic guide to running Claude Code autonomously
on a multi-step workstream. Read SKILL.md first for the quick model;
this guide is the depth.

---

## 1. What this is, in plain language

Normally you launch a Claude Code session, watch it, answer its
questions, and close it when done. That's fine for one task. It does
not scale to a workstream with a dozen sub-tasks spread over days.

The autonomous pattern lets you launch **one** session — the
**Terminal** — and tell it "complete this whole workstream." The
Terminal then launches its own Claude sessions (one per sub-task,
called **headless phase sessions**), checks their work, and only comes
back to you at meaningful checkpoints (phase boundaries) or when it
hits something it genuinely shouldn't decide alone.

Each sub-task still gets a fresh session with clean context and its own
journal entry — so you keep the quality of session-led development —
but you stop paying the per-task launch + babysit cost.

---

## 2. The three layers

```
┌─────────────────────────────────────────────────────────────┐
│ ARCHITECT CHAT                                                │
│ Strategic decisions, scope docs, ADRs. Writes the Terminal   │
│ prompt. In supervised mode, answers architectural questions. │
│ This is a normal interactive chat with you.                  │
└───────────────────────────┬─────────────────────────────────┘
                            │  operator pastes the prompt
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ TERMINAL  (one per workstream/phase)                         │
│ Operator-launched interactive Claude. Verifies prereqs,      │
│ creates the phase feature branch, spawns headless phase       │
│ sessions one at a time, verifies each, updates the journal,   │
│ reports at phase boundaries. Lives hours-to-days.            │
└───────────────────────────┬─────────────────────────────────┘
                            │  spawn_phase_session.ps1 (background)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ HEADLESS PHASE SESSION  (one per sub-task)                   │
│ `claude -p --allow-dangerously-skip-permissions`. Fully      │
│ autonomous. Does ONE bounded deliverable. Commits to a       │
│ feature branch. CANNOT push to main/dev. Writes its own      │
│ session journal. Returns a status to the Terminal.          │
└───────────────────────────┬─────────────────────────────────┘
                            │  Agent tool
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ WORKERS  (scoped subagents)                                  │
│ The actual implementation: code, tests, docs. Bounded by     │
│ the four-field contract (objective / output / tools /        │
│ boundaries).                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. The pieces (what's installed in a project)

| Piece | Path | Role |
| --- | --- | --- |
| Headless wrapper | `scripts/spawn_headless_session.ps1` | Low-level. Sets `CLAUDE_HEADLESS=1`, pipes prompt via stdin, enforces a timeout with process-tree kill, writes audit log. |
| Phase wrapper | `scripts/spawn_phase_session.ps1` | High-level. Builds a phase-shaped prompt (with the Q&A protocol baked in) and calls the headless wrapper. |
| Answer helper | `scripts/answer_question.ps1` | Operator/Terminal writes answers to phase-session questions. |
| Hook installer | `scripts/install_safety_hooks.ps1` | One-time. Writes the pre-push hook into `.git/hooks/`. |
| Pre-push hook | `.git/hooks/pre-push` | Blocks `CLAUDE_HEADLESS=1` pushes to main/dev. |
| Audit log | `data/automation/headless_log/*.jsonl` | One file per spawn; spawn + completion events. |
| Q&A inbox/outbox | `data/automation/inbox/`, `data/automation/outbox/` | File-based question/answer channel. |

`data/automation/` should be gitignored (the audit log + Q&A files are
runtime artifacts, not source).

To install in a new repo, see `assets/SETUP.md`.

---

## 4. Safety model — what can and cannot happen

| Capability | Headless session (skip-permissions) |
| --- | --- |
| Read any file | yes |
| Edit any file | yes (a frozen-state verifier, if present, catches overreach) |
| Run any shell command | yes — including destructive ones; this is the real risk |
| Spawn its own subagents | yes |
| Commit to a `feature/*` branch | yes |
| Push to `feature/*` on origin | yes |
| Commit to main/dev locally | technically yes, but cannot push them |
| Push to main/dev | NO — local pre-push hook rejects; origin branch protection (if set) is the non-bypassable backstop |
| Force-push / delete branches on origin | NO if origin branch protection is configured |

**The genuine residual risks** (mitigated by scoping + review, not
eliminated): a destructive shell command (`rm -rf`), unbounded external
API spend, and prompt injection from a file the session reads. Keep
autonomous work bounded and well-scoped; review commits before
promoting to main/dev.

**The single most important safety control you cannot get locally** is
origin-side branch protection. The local hook is bypassable (a
misbehaving session could `rm` it or `git push --no-verify`). If your
git host enforces branch protection on free private repos, turn it on.
If it requires a paid tier (some do), decide consciously: pay, make the
repo public, or accept that the local hook + operator monitoring is
your only layer (only acceptable when you actively watch the runs).

---

## 5. Autonomy modes

### Supervised (default for new patterns / high-stakes / operator awake)

Phase sessions surface forks via the file inbox. The Terminal
categorizes:
- **tactical** (naming, ordering, small design): Terminal/operator
  answers directly via `answer_question.ps1`.
- **architectural** (library choice, schema design, deviation from a
  doc, anything ADR-worthy): Terminal shows the question; operator
  pastes it into architect chat; architect decides; operator writes
  the answer.

Slower, every fork in the loop.

### Best-judgment (operator away / well-understood work)

Phase sessions make their own calls and document them; they do NOT
write questions for normal decisions. This mode is only safe if the
Terminal prompt contains:

1. **Pre-baked decisions** — every architectural choice you'd otherwise
   be asked, decided up front in the prompt (which library, which
   pattern, which endpoint, error strategy, etc.). The reference run
   used a "D1…D10" block.
2. **Hard-stop conditions** — the short list of situations where
   guessing is irresponsible. The session commits clean work, writes a
   "BLOCKED — needs operator" report, and stops. Typical hard-stops:
   - credentials missing or rejected
   - would need to hit a live/production (non-sandbox) endpoint
   - would touch protected/frozen files
   - would push to main/dev
   - scope ballooning beyond the phase
   - would spend real money or touch a shared external service that
     other processes depend on

**Shared-external-state rule**: if the work touches any external
resource other processes rely on (a shared sandbox account, a shared
database), do NOT let an unattended run mutate it. Build + test against
mocks/fixtures autonomously, and defer the one step that touches the
shared resource to a supervised session. (Reference run: the broker
adapter was fully built + mock-tested overnight; the live-account test
was deferred so it wouldn't leave residue that broke a scheduled job
the next morning.)

---

## 6. Anatomy of a Terminal prompt

A good Terminal prompt has these sections, in order:

1. **Identity + mode** — "This is the X Terminal. Supervised, or fully
   autonomous (operator asleep)." State it plainly up front.
2. **Architecture reference** — point at SKILL.md / the project's
   autonomous-session doc so the Terminal knows the pattern.
3. **Autonomy-mode rules** — if best-judgment: the pre-baked decisions +
   hard-stop list. If supervised: the escalation routing.
4. **Prerequisites** — the launch checklist, as commands the Terminal
   runs and verifies before spawning anything. Include the corrected
   pre-push test vector (`refs/heads/main abc refs/heads/main def`).
5. **Goal + branch** — what "done" means; which feature branch
   (`feature/<workstream>-phase-<N>`, off the prior phase's branch or
   main).
6. **Sub-session sequence** — each sub-task as a `spawn_phase_session.ps1`
   call with Scope + PhaseSpecificGuidance. Order them; one at a time;
   verify each before the next.
7. **Event handling** — start the inbox Monitor; how to handle Q_NEW
   and completion notifications.
8. **Hard constraints** — never push main/dev; don't touch frozen
   files; one sub-session at a time (shared-tree); stop on hard-stop.
9. **Phase completion** — verify deliverables; update journal/handoff/
   workstreams; report; do NOT auto-advance across phase boundaries.
10. **Deferred/supervised steps** — anything explicitly held for a
    human-watched session, with exact instructions.

Keep each sub-session's Scope to one coherent deliverable (2-4 hours of
work). Bake any external-tool PATH injection into a gitignored launcher
under `data/automation/`, never by editing `scripts/`.

---

## 7. The file-based Q&A protocol

When a phase session needs an answer it writes
`data/automation/inbox/Q_<session_id>_<seq>.json`:

```json
{
  "session_id": "...", "sequence_num": 1, "timestamp_utc": "...",
  "category": "tactical | architectural",
  "question": "...", "context": "...",
  "options": ["A: ...", "B: ..."],
  "recommended": "A — because ...",
  "blocking_subtask": "...",
  "phase_session_will_wait_until": "<now+30min>"
}
```

It then polls `data/automation/outbox/A_<session_id>_<seq>.json` every
30s for up to 30 minutes. On timeout it returns
`BLOCKED_AWAITING_ANSWER` with the unanswered Q path, having committed
whatever clean work preceded the block.

The Terminal watches the inbox with a persistent Monitor (each new Q
file → a notification). In best-judgment mode the Terminal answers
stray Qs itself (`-SignedBy "terminal-autonomous"`). In supervised mode
it routes per category.

---

## 7.5 Lessons memory (compounding knowledge across runs)

Each phase session gets a deliberately *fresh* context — great for quality, but
it means learnings don't carry over on their own. The lessons memory fixes that:

- **Raw log** — `data/automation/lessons_log.jsonl` (gitignored). Every session
  appends what it learned at completion: `autows lessons add --category
  <gotcha|pitfall|decision|pattern> --text "..."`.
- **Curated file** — `docs/journal/LESSONS.md` (committed). The durable, deduped
  knowledge, reviewed like code.
- **Read at bootstrap** — sessions run `autows lessons show` so they don't repeat
  known mistakes (the phase prompt already instructs this).

**Your job at phase boundaries:** curate. Skim the raw log (`autows lessons
show`), promote the durable, repo-specific lessons into `docs/journal/LESSONS.md`,
drop the noise, and commit. This keeps the file from growing unbounded and is the
pattern's analog of autoresearch "plateau/stuck detection." The kinds of things
worth promoting are exactly the entries in TROUBLESHOOTING.md — off-PATH tools,
flaky suites, hidden module couplings — captured automatically, per project.

**Safety:** the curated file is read by future autonomous sessions, so treat it as
part of the trust boundary (SECURITY.md) — review promotions, never seed lessons
from untrusted input.

---

## 7.6 Self-improvement (operator-gated)

`autows improve` closes the loop: it reads recent run outcomes (from the audit
log) + accumulated lessons and spawns a session that proposes improvements to the
agent's own prompt templates/heuristics. It is deliberately constrained:

- Edits land on a `feature/self-improve-<timestamp>` branch only; the pre-push
  hook keeps them off main/dev. **You review and merge** — nothing self-applies.
- The improver may change *behaviour* (prompts, heuristics, non-frozen files) but
  not *safety*: the frozen core is checksummed, the session is told never to touch
  it, and `autows verify-core` must stay green (the spawn path refuses on drift).

Run it occasionally (e.g. after a batch of phases), then review the branch like
any PR: does each change name a real problem from the outcomes/lessons and a
metric it should move? Merge the good ones; discard the rest. Do NOT widen the
improvable surface to the frozen core, and never `autows verify-core --update` to
"fix" a self-improvement diff — that would defeat the guard.

---

## 8. Handling a morning report

When a Terminal finishes (or hard-stops), it leaves a report. Check, in
order:

1. **Status** — COMPLETE, BLOCKED (hard-stop), or ERROR.
2. **Verifier / frozen-state guard** — must be green on the protected
   branch. If not, investigate before anything else.
3. **Branch state** — which feature branch, at which SHA, how many
   commits. Nothing should have reached main/dev.
4. **Gate results** — build/test/lint per sub-session.
5. **Deferred steps** — anything held for a supervised session; do
   those next, watched.
6. **Audit log** — `data/automation/headless_log/` if you want the full
   spawn/completion trail.
7. **Then**: review the diff, decide push / merge / discard.

If it hard-stopped, the report names which hard-stop (H1…Hn) and what
it needs. Resolve that, then either re-spawn the blocked sub-session
with the answer threaded in, or continue manually.

---

## 9. Cost + pacing

- `claude -p` invocations are real model usage. Each phase session is a
  full session's worth. Budget accordingly.
- Recommended initial cadence: 1-2 autonomous phase sessions per day,
  reviewed the next morning, until the pattern is proven in your repo.
  Then scale up.
- Premature scaling compounds errors faster than you can catch them.

---

## 10. Glossary

- **Terminal** — the operator-launched interactive session that
  orchestrates a workstream by spawning phase sessions.
- **Phase session** — an autonomous headless `claude -p` session doing
  one bounded sub-task.
- **Worker** — a subagent spawned inside a phase session via the Agent
  tool.
- **CLAUDE_HEADLESS** — env var set by the spawn wrapper; the pre-push
  hook keys off it to block protected-branch pushes.
- **Hard-stop** — a condition where an unattended session must stop
  rather than guess.
- **Pre-baked decision** — an architectural choice resolved in the
  Terminal prompt so sub-sessions don't need to ask.
- **Shared-external-state rule** — don't let unattended runs mutate
  external resources other processes depend on; mock it, defer the live
  step to a supervised session.
