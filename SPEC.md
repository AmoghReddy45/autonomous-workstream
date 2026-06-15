# Autonomous Workstream — Pattern Specification

This document defines the **Autonomous Workstream pattern** independently of any particular
AI agent or operating system. The Claude Code plugin in this repo is the *reference
implementation*; this spec is what a *conformant* implementation on another backend (Codex,
or anything else) must satisfy.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are used as in RFC 2119.

---

## 1. Roles

An implementation defines four roles. The boundaries between them are the source of the
pattern's quality and safety properties.

- **Architect** — a human-driven strategic context. Produces the *Terminal prompt* and, in
  supervised mode, answers architectural escalations. Out of scope for automation.
- **Terminal** — exactly one operator-launched, interactive agent session per workstream (or
  phase). It verifies prerequisites, creates the phase branch, spawns headless phase
  sessions one at a time, verifies each, maintains project state docs, and reports at phase
  boundaries. It MUST NOT auto-advance across a phase boundary without operator review.
- **Headless phase session** — a fully autonomous, non-interactive agent invocation that
  completes ONE bounded deliverable, commits to a feature branch, and returns a structured
  status. It MUST run under the headless marker (§4) and MUST NOT push to protected branches.
- **Worker** — a scoped subagent spawned by a phase session to do implementation, bounded by
  a four-field contract: objective / output format / tools+sources / boundaries. (Backends
  without a subagent primitive MAY collapse this into the phase session; see §6.)

## 2. Safety invariants (load-bearing)

A conformant implementation MUST guarantee:

- **S1 — Protected-branch isolation.** A headless session MUST be structurally prevented from
  pushing to protected branches (default `main`, `dev`). The mechanism MUST key off a
  headless marker that interactive operator sessions do not set, so operator pushes are
  unaffected.
- **S2 — Non-bypassable backstop available.** The implementation MUST document, and SHOULD
  require, an origin-side protection that a misbehaving session cannot remove locally. The
  local hook alone is necessary but not sufficient.
- **S3 — Single sanctioned entry point.** Headless sessions MUST be spawned only through a
  wrapper that (a) sets the headless marker, (b) enforces a wall-clock timeout with a
  process-tree kill, and (c) writes an audit record. Direct backend invocation bypasses the
  audit trail and is non-conformant.
- **S4 — Auditability.** Every spawn and completion MUST be recorded with: timestamp,
  session id, git HEAD + branch before and after, duration, and exit status.
- **S5 — Hard-stops.** In unattended operation the session MUST stop (committing clean work
  first) rather than guess on declared hard-stop conditions (§7).
- **S6 — Human promotion gate.** Autonomous output MUST stage on feature branches; promotion
  to a protected branch MUST require a human.
- **S7 — Frozen safety core.** Any self-modification capability MUST NOT be able to alter the
  components implementing S1–S4. Those components MUST be integrity-checked, and a run in
  which they have drifted MUST fail.

## 3. The Terminal prompt (contract)

A Terminal prompt SHOULD contain, in order: identity + autonomy mode; a pointer to this
pattern; autonomy-mode rules (pre-baked decisions + hard-stops if unattended, else
escalation routing); prerequisites as verifiable commands; goal + target branch; the ordered
sub-session sequence; event handling; hard constraints; phase-completion criteria; and any
steps explicitly deferred to a supervised session.

## 4. The headless marker

A single environment signal (reference: the env var `CLAUDE_HEADLESS=1`) distinguishes
autonomous sessions from interactive operator sessions. The spawn wrapper sets it; operator
terminals do not. The protected-branch guard (S1) reads it. Implementations MAY rename it but
MUST keep the property that it is set *only* by the sanctioned spawn path.

## 5. The backend interface

The only backend-specific operation is **"spawn one headless agent."** A backend adapter MUST
provide an operation equivalent to:

```
spawn_headless(prompt: string, timeout_seconds: int) -> { stdout: string, exit_code: int }
```

with these obligations:

- It MUST pass the prompt without truncation (reference backends require stdin, not a
  positional CLI argument, to avoid shell quote-mangling of multi-line prompts).
- It MUST run the agent non-interactively with permission prompts disabled.
- It MUST enforce `timeout_seconds` with a process-tree kill, returning a distinguishable
  timeout exit code.
- It MUST inherit (or explicitly set) the headless marker so S1 holds.
- It SHOULD return all output (stdout + stderr) for the audit record.

Everything else in the pattern — the Q&A protocol, audit log, branch policy, hooks, lessons
memory — is backend-neutral and MUST NOT be reimplemented per backend.

## 6. Backends without a subagent primitive

The reference backend spawns Workers via a native subagent tool. A backend lacking one
remains conformant if the phase session performs the worker's deliverables itself under the
same four-field discipline. Quality MAY degrade (no fresh worker context per subtask); this
SHOULD be documented for that backend.

## 7. Autonomy modes & hard-stops

- **Supervised** — phase sessions surface forks via the Q&A channel (§8); the Terminal routes
  tactical vs architectural.
- **Best-judgment / unattended** — phase sessions decide and document; they write a question
  only for a genuine architectural fork or a declared hard-stop. This mode is conformant only
  if the Terminal prompt supplies (a) pre-baked decisions and (b) hard-stop conditions.

Hard-stops (minimum set): missing/rejected credentials; would hit a live/non-sandbox
endpoint; would touch protected/frozen files; would push to a protected branch; scope
ballooning beyond the phase; would spend real money or mutate shared external state.

## 8. File protocols

All runtime artifacts live under a gitignored `data/automation/` directory.

**Q&A channel.** A phase session asks by writing `inbox/Q_<session_id>_<seq>.json`:

```json
{
  "session_id": "...", "sequence_num": 1, "timestamp_utc": "<ISO8601>",
  "category": "tactical | architectural",
  "question": "...", "context": "...",
  "options": ["A: ...", "B: ..."], "recommended": "A — because ...",
  "blocking_subtask": "...", "phase_session_will_wait_until": "<deadline>"
}
```

It then polls `outbox/A_<session_id>_<seq>.json` until a deadline, applying the answer or
returning `BLOCKED_AWAITING_ANSWER` with clean pre-block work committed. An answer file
contains at least: `session_id`, `sequence_num`, `answer`, `rationale`, `signed_by`.

**Audit log.** `headless_log/<session_id>.jsonl` — one `spawn` record and one `complete`
record per the fields in S4.

**Lessons memory (roadmap, Phase 3).** `lessons_log.jsonl` (append-only, raw, per session)
plus a curated, version-controlled `LESSONS.md`. A phase session SHOULD read curated lessons
at bootstrap and append raw lessons at completion; the Terminal SHOULD curate raw → promoted
at phase boundaries. This is the pattern's analog of an autoresearch experiment journal: it
lets knowledge compound across otherwise-fresh sessions without weakening the safety core.

## 9. Conformance

An implementation is **conformant** if it satisfies S1–S7, provides the §5 backend interface,
and implements the §8 Q&A and audit protocols. It is **safety-conformant** (the minimum bar
for unattended use) if at least S1–S6 hold with origin-side protection (S2) actually enabled.
