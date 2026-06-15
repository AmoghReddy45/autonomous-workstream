# Autonomous Workstream — Troubleshooting

Concrete fixes for every failure mode observed running this pattern.
Each entry: symptom → cause → fix.

---

## Prompt silently truncated (phase session ignores half its instructions)

**Symptom**: a headless phase session behaves as if it never saw the
later parts of its prompt (skips the Q&A protocol, misses constraints).

**Cause**: passing a multi-line prompt as a `-p "..."` positional
argument. PowerShell native-command argument passing mangles embedded
double quotes and truncates the prompt at the first stray quote.

**Fix**: pipe the prompt via stdin instead. `spawn_headless_session.ps1`
in `assets/scripts/` already does this:
```powershell
$Prompt | & claude -p --allow-dangerously-skip-permissions
```
`claude -p` with no positional argument reads from stdin. If you wrote
your own wrapper, switch to stdin.

---

## Phase session hangs at exit (wrapper never returns)

**Symptom**: a phase session finishes all its work and commits, but the
`claude` process never exits, so the wrapper blocks forever.

**Cause**: `claude -p` occasionally hangs at exit on long sessions even
after the work is done.

**Fix**: the wrapper enforces a timeout with a process-tree kill. In
`spawn_headless_session.ps1`:
```powershell
$proc = Start-Process claude -ArgumentList @("-p","--allow-dangerously-skip-permissions") `
  -NoNewWindow -PassThru -RedirectStandardInput $tempIn `
  -RedirectStandardOutput $tempOut -RedirectStandardError $tempErr
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
  & taskkill /F /T /PID $proc.Id    # /T kills the whole process tree
}
```
Exit code `-2` means the wrapper killed a hung process. The work is
usually already committed — check `git log` on the feature branch
before assuming failure.

**Detection workaround for a Terminal**: if you can't rely on the
wrapper timeout, poll for the expected commit on the feature branch
instead of waiting on the process, and proactively stop the process
once the commit appears.

---

## Stale `claude` processes pile up

**Symptom**: many `claude.exe` processes lingering after hung exits.

**Cause**: hang-on-exit episodes before the watchdog was in place.

**Fix** (safe — protects the current session by walking its own parent
chain, then kills only the others):
```powershell
$mine=@(); $cur=$PID
for ($i=0;$i -lt 12;$i++){ $p=Get-CimInstance Win32_Process -Filter "ProcessId=$cur" -EA SilentlyContinue; if(-not $p){break}; if($p.Name -like 'claude*'){$mine+=$p.ProcessId}; $cur=$p.ParentProcessId; if(-not $cur){break} }
Get-Process claude -EA SilentlyContinue | Where-Object { $mine -notcontains $_.Id } | Stop-Process -Force
```
Never blanket-kill by age alone — your active session's process may be
old too.

---

## External tool off PATH for the headless child (e.g. protoc, a compiler)

**Symptom**: a phase session fails a build step because a tool isn't
found, even though you installed it.

**Cause**: a headless child inherits the **parent's environment at spawn
time**. A tool installed (or a PATH edit made) AFTER the Terminal
launched is invisible to it. Some installers also fail to register a
durable PATH shim.

**Fix** (do NOT edit `scripts/`): write a gitignored launcher under
`data/automation/` that sets the env var before calling the spawn
wrapper:
```powershell
# data/automation/_launch_<label>.ps1
$env:SOMETOOL = "C:\full\path\to\tool.exe"
$env:PATH = "C:\full\path\to\bin;" + $env:PATH
& .\scripts\spawn_phase_session.ps1 -Workstream "..." -Phase 1 -SessionInPhase 1 -Scope "..." -PhaseSpecificGuidance "..."
```
Alternatively, fully install the tool + verify `tool --version` in a
fresh shell, then relaunch the Terminal so it inherits clean PATH.

---

## Pre-push hook test "fails" but the hook is fine

**Symptom**: your hook test prints `EXIT=0` where you expected a block.

**Cause**: a malformed test vector. The hook reads stdin lines as
`<local_ref> <local_sha> <remote_ref> <remote_sha>` and keys off the
THIRD field (`remote_ref`). A vector like `"refs/heads/main x x x"` has
`x` as field 3, which doesn't match a protected branch, so the hook
correctly allows it.

**Fix**: use a well-formed vector:
```bash
echo "refs/heads/main abc refs/heads/main def" | CLAUDE_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"
# expect EXIT=1
echo "refs/heads/feature/x abc refs/heads/feature/x def" | CLAUDE_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"
# expect EXIT=0
```

---

## Concurrent sessions collide (branch checkout / journal divergence)

**Symptom**: HEAD moves unexpectedly mid-session; duplicate journal
files with different SHAs on different branches; a feature branch name
you wanted is "already taken."

**Cause**: two coordinator sessions (e.g., an architect chat doing git
ops + a Terminal spawning phase sessions) operating on the **same
working tree**. Git's working tree + index + HEAD are a single shared
resource.

**Fix / discipline**:
- Run only ONE coordinator session per working tree at a time, OR
- Give each session its own working tree: `git worktree add ../proj-ws2 <branch>`.
- While a Terminal is live, the architect chat should AVOID `git switch`
  / `git commit` (writing untracked files is fine; moving HEAD is not).
- Reconcile divergence afterward by copying the canonical journal files
  to main and rewriting handoff/workstreams to the merged truth, rather
  than git-merging two stale snapshots.

---

## Phase session returns BLOCKED_AWAITING_ANSWER

**Symptom**: a sub-session stopped waiting for an answer that never
came.

**Cause**: it wrote a Q file and the 30-minute poll window expired with
no matching A file (the Terminal's inbox Monitor lagged, or nobody was
watching).

**Fix**: write the A file now via `answer_question.ps1`, then re-spawn
the same sub-session with the answer threaded into its
PhaseSpecificGuidance (the original committed its clean pre-block work,
so you continue from there). In best-judgment mode, prefer pre-baking
the decision so the question never arises.

---

## Hard-stop hit during an unattended run

**Symptom**: morning report says "BLOCKED — needs operator" with a
hard-stop code.

**Cause**: the run hit one of the conditions you told it not to guess
on (missing credentials, would touch frozen/protected files, would
touch shared external state, scope ballooning, etc.). This is the
system working correctly.

**Fix**: resolve the named condition (install the credential, make the
decision, clean the shared resource), then re-spawn the blocked
sub-session or continue manually. The run committed clean work up to
the stop; nothing is lost.

---

## Verifier / frozen-state guard red after an autonomous run

**Symptom**: the project's protected-state check is failing on a branch
it shouldn't be.

**Cause**: a phase session edited a protected/frozen file outside its
authorized scope.

**Fix**: this is exactly what the guard is for — it caught the overreach
before promotion. Inspect the diff, revert the unauthorized change, and
tighten the sub-session's boundaries (the four-field contract) before
re-running. Never promote a branch whose protected-state guard is red.

---

## Nothing was logged (a session ran but left no audit trail)

**Symptom**: commits appeared but `data/automation/headless_log/` has no
matching entry.

**Cause**: a `claude -p` was invoked directly, bypassing
`spawn_headless_session.ps1`.

**Fix**: treat unaccounted-for commits as a red flag — review them
carefully. Discipline: the wrapper is the ONLY sanctioned way to spawn
headless sessions; cron jobs and Terminals must call it, never raw
`claude -p`.
