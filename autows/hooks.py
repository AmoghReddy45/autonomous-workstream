"""The pre-push safety hook + its installer.

The hook is bash (git runs hooks via its bundled shell on every platform,
including Git for Windows). It blocks pushes to protected branches when a
headless marker env var is set; operator interactive pushes are unaffected.
"""
import os
import stat

# NOTE: keep this LF-only. Checks BOTH markers so it works with the new CLI
# (AUTOWS_HEADLESS) and the legacy PowerShell scripts (CLAUDE_HEADLESS).
PRE_PUSH_HOOK = """#!/bin/bash
# pre-push — blocks pushes to protected branches when a headless agent marker is set.
# Installed by `autows install-hooks` (Autonomous Workstream pattern).
# Operator interactive pushes (no headless marker) are unaffected.
protected_branches=("main" "dev")
if [ -n "$AUTOWS_HEADLESS" ] || [ -n "$CLAUDE_HEADLESS" ]; then headless=1; else headless=0; fi
while read local_ref local_sha remote_ref remote_sha; do
    remote_branch="${remote_ref##*/}"
    for protected in "${protected_branches[@]}"; do
        if [ "$remote_branch" = "$protected" ] && [ "$headless" = "1" ]; then
            echo ""
            echo "  PRE-PUSH BLOCKED: a headless agent session tried to push to '$protected'."
            echo "  Headless sessions may push to feature/* only. Promotions to $protected"
            echo "  require an operator at an interactive terminal (review the work first)."
            echo ""
            exit 1
        fi
    done
done
exit 0
"""


def install_pre_push(git_root: str) -> str:
    """Write the pre-push hook into <git_root>/.git/hooks/. Returns its path."""
    hooks_dir = os.path.join(git_root, ".git", "hooks")
    if not os.path.isdir(hooks_dir):
        raise FileNotFoundError(f"No .git/hooks at {hooks_dir}. Is this a git repo?")
    dst = os.path.join(hooks_dir, "pre-push")
    # Always LF, no BOM — a CRLF hook fails on POSIX shells.
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(PRE_PUSH_HOOK)
    # Make it executable (no-op effect on Windows, required on POSIX).
    mode = os.stat(dst).st_mode
    os.chmod(dst, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return dst
