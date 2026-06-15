# install_safety_hooks.ps1  (portable / project-agnostic, self-contained)
# Installs a pre-push hook that blocks pushes to protected branches
# (main/dev by default) when CLAUDE_HEADLESS=1 is set. Operator
# interactive pushes are unaffected. The hook body is embedded here so
# this script is the only file you need to drop into a new project.
#
# Part of the Autonomous Workstream pattern (global skill
# `autonomous-workstream`).
#
# Usage:  .\scripts\install_safety_hooks.ps1

$ErrorActionPreference = "Stop"

$gitRoot = (git rev-parse --show-toplevel).Trim()
$hooksDir = Join-Path $gitRoot ".git/hooks"
if (-not (Test-Path $hooksDir)) { Write-Error "No .git/hooks at $hooksDir. Is this a git repo?"; exit 1 }

$hook = @'
#!/bin/bash
# pre-push — blocks pushes to protected branches when CLAUDE_HEADLESS=1.
# Installed by install_safety_hooks.ps1 (Autonomous Workstream pattern).
# Operator interactive pushes (no CLAUDE_HEADLESS) are unaffected.
protected_branches=("main" "dev")
while read local_ref local_sha remote_ref remote_sha; do
    remote_branch="${remote_ref##*/}"
    for protected in "${protected_branches[@]}"; do
        if [ "$remote_branch" = "$protected" ]; then
            if [ -n "$CLAUDE_HEADLESS" ]; then
                echo ""
                echo "  PRE-PUSH BLOCKED: a headless Claude session tried to push to '$protected'."
                echo "  Headless sessions may push to feature/* only. Promotions to $protected"
                echo "  require an operator at an interactive terminal (review the work first)."
                echo ""
                exit 1
            fi
        fi
    done
done
exit 0
'@

$dst = Join-Path $hooksDir "pre-push"
# Write with LF line endings (bash hook) and no BOM.
$hookLf = $hook -replace "`r`n", "`n"
[IO.File]::WriteAllText($dst, $hookLf, [Text.UTF8Encoding]::new($false))
Write-Host "Installed: $dst"

Write-Host ""
Write-Host "Verify:"
Write-Host '  echo "refs/heads/main abc refs/heads/main def" | CLAUDE_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"   # expect 1'
Write-Host '  echo "refs/heads/feature/x abc refs/heads/feature/x def" | CLAUDE_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"   # expect 0'
Write-Host ""
Write-Host "STRONGLY RECOMMENDED next: add origin-side branch protection on main + dev"
Write-Host "(the local hook is bypassable; origin protection is the non-bypassable layer)."
Write-Host "To protect branches other than main/dev, edit the protected_branches array in $dst."
