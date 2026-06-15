"""Phase-session prompt builder.

Builds the phase-shaped prompt (with the file-based Q&A protocol baked in) that
a Terminal hands to a headless phase session. Uses string.Template ($name) so
the embedded JSON braces don't collide with placeholder syntax.

The worker step adapts to the backend: backends with a subagent primitive spawn
Workers; backends without one (SPEC section 6) do the work in-session.
"""
from string import Template

_PHASE = Template(
    """You are an autonomous headless phase session. Session ID: $session_id.
Workstream: $workstream. Phase: $phase. Session in phase: $session_in_phase.
Pattern: Autonomous Workstream (skill autonomous-workstream) — file-based Q&A protocol.

=== BOOTSTRAP ===
1. Read the project's handoff / state docs (e.g. docs/journal/handoff.md) if present.
2. Verify branch: $branch. Create off the current base if missing; if it exists,
   check it out and merge the base branch in first to pick up recent updates.
3. Verify any project pre-flight / frozen-state guard is green before starting.
4. Read the phase-specific guidance below.

=== SCOPE ===
$scope

$guidance

=== WORKFLOW ===
1. Decompose the scope into worker-sized subtasks (2-4 hours each, one deliverable).
$worker_step
3. After all subtasks: write/update the session journal + project handoff +
   any workstream dashboard, and commit them.

=== Q&A PROTOCOL (when you hit a fork you can't resolve confidently) ===
Default: if this session was told 'best-judgment mode', make the call, document
the rationale in the journal, and continue — do NOT write a Q file for normal
decisions. Only write a Q file for genuine forks (architectural choices, or any
declared hard-stop).

To ask: write data/automation/inbox/Q_${session_id}_<seq>.json (seq = 001, 002...):
{
  "session_id": "$session_id", "sequence_num": <int>, "timestamp_utc": "<ISO8601>",
  "category": "tactical" | "architectural",
  "question": "<complete sentence>", "context": "<why + what's blocking>",
  "options": ["A: ...","B: ..."], "recommended": "A — because ...",
  "blocking_subtask": "<paused subtask>", "phase_session_will_wait_until": "<now+30min>"
}
Then poll data/automation/outbox/A_${session_id}_<seq>.json every 30s for up to
30 min. On answer: apply + continue. On timeout: return BLOCKED_AWAITING_ANSWER
with the Q path, having committed clean pre-block work.

=== HARD CONSTRAINTS ===
- DO NOT push to main or dev (pre-push hook + origin protection block it). Work
  on $branch only.
- DO NOT touch protected/frozen files unless this scope explicitly authorizes it.
- DO NOT skip the gates. Every commit passes: $gate_commands.
- DO NOT make architectural decisions you're unsure about unless in best-judgment
  mode — then decide + document.
- If the project's pre-flight/doorman fails at bootstrap, return DOORMAN_FAIL.

=== FINAL OUTPUT (to the Terminal) ===
Status: COMPLETE | BLOCKED_AWAITING_ANSWER | DOORMAN_FAIL | ERROR
Subtasks done / remaining; commits (SHAs); branch state; Q&A files created;
frozen-state guard status on $branch; suggested next session.

Begin now.
"""
)

_WORKER_STEP_SUBAGENT = (
    "2. Per subtask: spawn a {worker_type} subagent with the four-field contract\n"
    "   (objective / output format / tools+sources / boundaries). Review its diff.\n"
    "   Run gates: {gate_commands}. All must pass before commit. Commit incrementally\n"
    "   on {branch} with a descriptive message."
)

_WORKER_STEP_SELF = (
    "2. Per subtask: complete it yourself under the four-field discipline (objective /\n"
    "   output format / tools+sources / boundaries) — this backend has no subagent\n"
    "   primitive. After each, run gates: {gate_commands}. All must pass before commit.\n"
    "   Commit incrementally on {branch} with a descriptive message."
)


def build_phase_prompt(
    *, session_id, workstream, phase, session_in_phase, branch, scope,
    guidance, worker_type, gate_commands, supports_subagents=True,
) -> str:
    template = _WORKER_STEP_SUBAGENT if supports_subagents else _WORKER_STEP_SELF
    worker_step = template.format(
        worker_type=worker_type, gate_commands=gate_commands, branch=branch,
    )
    return _PHASE.substitute(
        session_id=session_id,
        workstream=workstream,
        phase=phase,
        session_in_phase=session_in_phase,
        branch=branch,
        scope=scope,
        guidance=guidance or "",
        gate_commands=gate_commands,
        worker_step=worker_step,
    )
