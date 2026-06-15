# answer_question.ps1  (portable / project-agnostic)
# Write an A file in response to a phase session's Q file, or print a Q
# for the operator to route to architect chat (-ShowOnly).
#
# Part of the Autonomous Workstream pattern (global skill
# `autonomous-workstream`).
#
# Usage:
#   .\scripts\answer_question.ps1 -QFile "data\automation\inbox\Q_<id>_001.json" `
#       -Answer "option A" -Rationale "..." -SignedBy "operator"
#   .\scripts\answer_question.ps1 -QFile <path> -ShowOnly   # print for architect routing

param(
    [Parameter(Mandatory=$true)] [string]$QFile,
    [string]$Answer = "",
    [string]$Rationale = "",
    [string]$SignedBy = "operator",          # operator | architect-chat | terminal-autonomous
    [string]$AdditionalContext = "",
    [switch]$ShowOnly
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $QFile)) { Write-Error "Q file not found: $QFile"; exit 1 }
$q = Get-Content $QFile -Raw | ConvertFrom-Json

if ($ShowOnly) {
    Write-Host ""
    Write-Host "==== QUESTION FROM HEADLESS PHASE SESSION ===="
    Write-Host "session_id: $($q.session_id)   seq: $($q.sequence_num)   category: $($q.category)"
    Write-Host "blocking: $($q.blocking_subtask)   deadline: $($q.phase_session_will_wait_until)"
    Write-Host ""
    Write-Host "QUESTION: $($q.question)"
    Write-Host "CONTEXT:  $($q.context)"
    Write-Host "OPTIONS:"; $q.options | ForEach-Object { Write-Host "  - $_" }
    Write-Host "RECOMMENDED: $($q.recommended)"
    Write-Host "=============================================="
    Write-Host "Copy into architect chat; then re-run with -Answer/-Rationale to unblock."
    exit 0
}

if ([string]::IsNullOrEmpty($Answer)) { Write-Error "-Answer required unless -ShowOnly."; exit 1 }

$qName = Split-Path $QFile -Leaf
if ($qName -notmatch "^Q_(.+)_(\d+)\.json$") {
    Write-Error "Q file name doesn't match Q_<session_id>_<seq>.json: $qName"; exit 1
}
$aName = "A_" + $matches[1] + "_" + $matches[2] + ".json"
$outboxDir = "data/automation/outbox"
if (-not (Test-Path $outboxDir)) { New-Item -ItemType Directory -Force -Path $outboxDir | Out-Null }
$aFile = Join-Path $outboxDir $aName

@{
    session_id = $q.session_id; sequence_num = $q.sequence_num
    timestamp_utc = (Get-Date -Format "o"); answer = $Answer; rationale = $Rationale
    signed_by = $SignedBy; additional_context = $AdditionalContext
} | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 -FilePath $aFile

Write-Host "Wrote $aFile — phase session $($q.session_id) resumes on next poll (<=30s)."
