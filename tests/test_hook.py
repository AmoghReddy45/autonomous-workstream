"""Verify the pre-push hook's load-bearing contract (SPEC S1).

Runs the actual rendered hook through bash with the documented test vectors.
The hook source is passed via an env var and `eval`-ed, so bash never has to
open a file path — this avoids Windows path-translation problems (spaces,
backslashes) and works identically on Linux CI and Git Bash. Skipped if no
real bash is available.
"""
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autows.hooks import PRE_PUSH_HOOK  # noqa: E402


def _find_bash():
    """Prefer a real bash. On Windows, skip the WSL `WindowsApps\\bash.exe`
    stub, which can't run the hook reliably."""
    found = shutil.which("bash")
    if found and "WindowsApps" not in found:
        return found
    for c in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        "/bin/bash", "/usr/bin/bash",
    ):
        if os.path.exists(c):
            return c
    return found  # may be None; tests skip if so


BASH = _find_bash()
MAIN = "refs/heads/main abc refs/heads/main def"
FEATURE = "refs/heads/feature/x abc refs/heads/feature/x def"


@unittest.skipUnless(BASH, "bash not available")
class PrePushHookTest(unittest.TestCase):
    def _run(self, stdin, headless_env):
        env = dict(os.environ)
        env.pop("AUTOWS_HEADLESS", None)
        env.pop("CLAUDE_HEADLESS", None)
        env["AUTOWS_HOOK_SRC"] = PRE_PUSH_HOOK
        if headless_env:
            env[headless_env] = "1"
        # Trailing newline matters: `while read` skips a final unterminated line.
        return subprocess.run(
            [BASH, "-c", 'eval "$AUTOWS_HOOK_SRC"'],
            input=stdin + "\n", text=True, capture_output=True, env=env,
        ).returncode

    def test_headless_push_to_main_blocked(self):
        self.assertEqual(self._run(MAIN, "AUTOWS_HEADLESS"), 1)

    def test_legacy_marker_still_blocks(self):
        self.assertEqual(self._run(MAIN, "CLAUDE_HEADLESS"), 1)

    def test_headless_push_to_feature_allowed(self):
        self.assertEqual(self._run(FEATURE, "AUTOWS_HEADLESS"), 0)

    def test_operator_push_to_main_allowed(self):
        self.assertEqual(self._run(MAIN, None), 0)


if __name__ == "__main__":
    unittest.main()
