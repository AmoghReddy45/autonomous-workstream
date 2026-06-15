# spawn_phase_session.ps1  (portable / project-agnostic)
# High-level wrapper: builds a phase-shaped prompt (with the file-based
# Q&A protocol baked in) and calls spawn_headless_session.ps1. Used by a
# Terminal session to spawn headless phase sessions.
#
# Part of the Autonomous Workstream pattern (global skill
# `autonomous-workstream`).
#
# Usage:
#   .\scripts\spawn_phase_session.ps1 `
#       -Workstream "rust" -Phase 2 -SessionInPhase 1 `
#       -Scope "Implement crate X ..." `
#       -PhaseSpecificGuidance "doc refs; pre-baked decisions; best-judgment mode" `
#       [-WorkerType "general-purpose"] `
#       [-GateCommands "cargo build && cargo test && cargo clippy -- -D warnings && cargo fmt --check"] `
#       [-BranchPrefix "feature"] [-BranchOverride ""] [-TimeoutSeconds 7200]

param(
    [Parameter(Mandatory=$true)] [string]$Workstream,
    [Parameter(Mandatory=$true)] [int]$Phase,
    [Parameter(Mandatory=$true)] [int]$SessionInPhase,
    [Parameter(Mandatory=$true)] [string]$Scope,
    [string]$PhaseSpecificGuidance = "",
    [string]$WorkerType = "general-purpose",
    [string]$GateCommands = "the project's standard build/test/lint gates (see CLAUDE.md)",
    [string]$BranchPrefix = "feature",
    [string]$BranchOverride = "",
    [int]$TimeoutSeconds = 7200
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path ".\scripts\spawn_headless_session.ps1")) {
    Write-Error "spawn_headless_session.ps1 missing in scripts/. Cannot proceed."
    exit 1
}

$date = Get-Date -Format "yyyyMMdd-HHmmss"
$sessionId = "${Workstream}-phase-${Phase}-session-${SessionInPhase}-${date}"
if ([string]::IsNullOrEmpty($BranchOverride)) {
    $branch = "${BranchPrefix}/${Workstream}-phase-${Phase}"
} else { $branch = $BranchOverride }

$prompt = @"
You are an autonomous headless phase session. Session ID: ${sessionId}.
Workstream: ${Workstream}. Phase: ${Phase}. Session in phase: ${SessionInPhase}.
Pattern: Autonomous Workstream (global skill autonomous-workstream) — file-based Q&A protocol.

=== BOOTSTRAP ===
1. Read the project's handoff / state docs (e.g. docs/journal/handoff.md) if present.
2. Verify branch: ${branch}. Create off the current base if missing; if it exists,
   check it out and merge the base branch in first to pick up recent updates.
3. Verify any project pre-flight / frozen-state guard is green before starting.
4. Read the phase-specific guidance below.

=== SCOPE ===
${Scope}

${PhaseSpecificGuidance}

=== WORKFLOW ===
1. Decompose the scope into worker-sized subtasks (2-4 hours each, one deliverable).
2. Per subtask: spawn a ${WorkerType} subagent with the four-field contract
   (objective / output format / tools+sources / boundaries). Review its diff.
   Run gates: ${GateCommands}. All must pass before commit. Commit incrementally
   on ${branch} with a descriptive message.
3. After all subtasks: write/update the session journal + project handoff +
   any workstream dashboard, and commit them.

=== Q&A PROTOCOL (when you hit a fork you can't resolve confidently) ===
Default: if this session was told 'best-judgment mode', make the call, document
the rationale in the journal, and continue — do NOT write a Q file for normal
decisions. Only write a Q file for genuine forks (architectural choices, or any
declared hard-stop).

To ask: write data/automation/inbox/Q_${sessionId}_<seq>.json (seq = 001, 002...):
{
  "session_id": "${sessionId}", "sequence_num": <int>, "timestamp_utc": "<ISO8601>",
  "category": "tactical" | "architectural",
  "question": "<complete sentence>", "context": "<why + what's blocking>",
  "options": ["A: ...","B: ..."], "recommended": "A — because ...",
  "blocking_subtask": "<paused subtask>", "phase_session_will_wait_until": "<now+30min>"
}
Then poll data/automation/outbox/A_${sessionId}_<seq>.json every 30s for up to
30 min. On answer: apply + continue. On timeout: return BLOCKED_AWAITING_ANSWER
with the Q path, having committed clean pre-block work.

=== HARD CONSTRAINTS ===
- DO NOT push to main or dev (pre-push hook + origin protection block it). Work
  on ${branch} only.
- DO NOT touch protected/frozen files unless this scope explicitly authorizes it.
- DO NOT skip the gates. Every commit passes: ${GateCommands}.
- DO NOT make architectural decisions you're unsure about unless in best-judgment
  mode — then decide + document.
- If the project's pre-flight/doorman fails at bootstrap, return DOORMAN_FAIL.

=== FINAL OUTPUT (to the Terminal) ===
Status: COMPLETE | BLOCKED_AWAITING_ANSWER | DOORMAN_FAIL | ERROR
Subtasks done / remaining; commits (SHAs); branch state; Q&A files created;
frozen-state guard status on ${branch}; suggested next session.

Begin now.
"@

Write-Host "Spawning phase session: $sessionId  (branch: $branch, timeout: ${TimeoutSeconds}s)"
& .\scripts\spawn_headless_session.ps1 -Prompt $prompt -SessionLabel $sessionId -TimeoutSeconds $TimeoutSeconds
