"""Smoke tests for the cross-platform timeout watchdog and prompt-via-stdin path."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autows.config import TIMEOUT_EXIT_CODE  # noqa: E402
from autows.process import run_with_timeout  # noqa: E402

PY = sys.executable


class RunWithTimeoutTest(unittest.TestCase):
    def test_prompt_reaches_child_via_stdin(self):
        # Child echoes back whatever it reads on stdin -> proves no truncation.
        out, code, timed = run_with_timeout(
            [PY, "-c", "import sys; sys.stdout.write(sys.stdin.read())"],
            "hello\nmulti-line\nprompt", 30,
        )
        self.assertFalse(timed)
        self.assertEqual(code, 0)
        self.assertIn("multi-line", out)

    def test_timeout_kills_and_reports(self):
        out, code, timed = run_with_timeout(
            [PY, "-c", "import time; time.sleep(30)"], "", 1,
        )
        self.assertTrue(timed)
        self.assertEqual(code, TIMEOUT_EXIT_CODE)

    def test_missing_executable_raises(self):
        with self.assertRaises(FileNotFoundError):
            run_with_timeout(["definitely-not-a-real-binary-xyz"], "", 5)


if __name__ == "__main__":
    unittest.main()
