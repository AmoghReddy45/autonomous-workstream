# spawn_headless_session.ps1  (portable / project-agnostic)
# Spawn a one-shot headless Claude Code session with full autonomy to
# feature/* branches. Headless pushes to main/dev are blocked by the
# pre-push hook (install_safety_hooks.ps1) + origin branch protection.
#
# Part of the Autonomous Workstream pattern (global skill
# `autonomous-workstream`). Returns the session's final response on
# stdout; logs spawn + completion to data/automation/headless_log/.
#
# Usage:
#   .\scripts\spawn_headless_session.ps1 -Prompt "<prompt>" `
#       [-SessionLabel "my-task"] [-TimeoutSeconds 1800]

param(
    [Parameter(Mandatory=$true)] [string]$Prompt,
    [string]$SessionLabel = "untitled",
    [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"

# Verify we're inside a git work tree (project root with .claude recommended).
try { $null = git rev-parse --is-inside-work-tree 2>$null } catch {}
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not inside a git work tree. cd to the project root first."
    exit 1
}
if (-not (Test-Path ".claude" -PathType Container)) {
    Write-Warning "No .claude/ at cwd — agents/skills may not load for the child. Continuing."
}

# Verify the pre-push safety hook is installed (else autonomy is unsafe).
$gitRoot = (git rev-parse --show-toplevel).Trim()
$prePushHook = Join-Path $gitRoot ".git/hooks/pre-push"
if (-not (Test-Path $prePushHook)) {
    Write-Error "Pre-push safety hook not installed. Run .\scripts\install_safety_hooks.ps1 first."
    exit 1
}

# Audit log.
$logDir = "data/automation/headless_log"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$sessionId = "${timestamp}_${SessionLabel}"
$logFile = Join-Path $logDir "${sessionId}.jsonl"

$headSha = (git rev-parse HEAD).Trim()
$currentBranch = (git branch --show-current).Trim()

@{
    timestamp = (Get-Date -Format "o"); event = "spawn"; session_id = $sessionId
    label = $SessionLabel; head_sha = $headSha; branch_at_spawn = $currentBranch
    prompt_first_200_chars = $Prompt.Substring(0, [Math]::Min(200, $Prompt.Length))
    prompt_length = $Prompt.Length; timeout_seconds = $TimeoutSeconds
} | ConvertTo-Json -Compress | Out-File -Append -Encoding utf8 -FilePath $logFile

# Mark this as a headless session so the pre-push hook blocks main/dev.
$env:CLAUDE_HEADLESS = "1"

# Invoke headless Claude.
# - Prompt via stdin (temp file): avoids PowerShell native-arg quote mangling
#   that silently truncates multi-line prompts.
# - WaitForExit(timeout) + taskkill /F /T: claude -p can hang at exit on long
#   sessions even after committing; the watchdog kills the whole process tree.
# - Output to temp files: avoids stdout/stderr buffer deadlock on large output.
$startTime = Get-Date
$tempIn = [IO.Path]::GetTempFileName()
$tempOut = [IO.Path]::GetTempFileName()
$tempErr = [IO.Path]::GetTempFileName()
$timedOut = $false
try {
    [IO.File]::WriteAllText($tempIn, $Prompt, [Text.UTF8Encoding]::new($false))
    $proc = Start-Process -FilePath "claude" `
        -ArgumentList @("-p", "--allow-dangerously-skip-permissions") `
        -NoNewWindow -PassThru `
        -RedirectStandardInput $tempIn -RedirectStandardOutput $tempOut -RedirectStandardError $tempErr
    if ($proc.WaitForExit($TimeoutSeconds * 1000)) {
        $exitCode = $proc.ExitCode
    } else {
        $timedOut = $true
        try { & taskkill /F /T /PID $proc.Id 2>&1 | Out-Null } catch { try { $proc.Kill() } catch {} }
        try { $proc.WaitForExit(5000) } catch {}
        $exitCode = -2   # wrapper-enforced timeout
    }
    $stdoutContent = if (Test-Path $tempOut) { [IO.File]::ReadAllText($tempOut) } else { "" }
    $stderrContent = if (Test-Path $tempErr) { [IO.File]::ReadAllText($tempErr) } else { "" }
    $output = $stdoutContent + $stderrContent
    if ($timedOut) { $output = "[wrapper] Exceeded ${TimeoutSeconds}s; killed via taskkill /F /T.`n" + $output }
} catch {
    $output = "EXCEPTION: $_"; $exitCode = -1
} finally {
    Remove-Item $tempIn, $tempOut, $tempErr -ErrorAction SilentlyContinue
}
$durationSeconds = ((Get-Date) - $startTime).TotalSeconds

$headShaAfter = (git rev-parse HEAD).Trim()
$branchAfter = (git branch --show-current).Trim()

@{
    timestamp = (Get-Date -Format "o"); event = "complete"; session_id = $sessionId
    duration_seconds = $durationSeconds; exit_code = $exitCode
    head_sha_after = $headShaAfter; branch_after = $branchAfter
    head_changed = ($headSha -ne $headShaAfter); branch_changed = ($currentBranch -ne $branchAfter)
    output_first_500_chars = ($output -join "`n").Substring(0, [Math]::Min(500, ($output -join "`n").Length))
    output_length = ($output -join "`n").Length
} | ConvertTo-Json -Compress | Out-File -Append -Encoding utf8 -FilePath $logFile

$env:CLAUDE_HEADLESS = $null

$output -join "`n"
Write-Host ""
Write-Host "---"
Write-Host "Headless session $sessionId complete. Duration: $([Math]::Round($durationSeconds,1))s. Exit: $exitCode."
Write-Host "Branch before: $currentBranch ($headSha). After: $branchAfter ($headShaAfter)."
Write-Host "Audit log: $logFile"
exit $exitCode
