"""Self-improvement loop: prompt construction + outcomes summary."""
import importlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autows import safety_core  # noqa: E402
from autows.prompts import build_improve_prompt  # noqa: E402


class ImprovePromptTest(unittest.TestCase):
    def _prompt(self):
        frozen = ["autows/" + r.replace(os.sep, "/") for r in safety_core.FROZEN_FILES]
        return build_improve_prompt(
            outcomes_summary="3 sessions, 1 timed out",
            lessons_text="- (gotcha) protoc on PATH",
            frozen_files=frozen, branch="feature/self-improve-x",
        )

    def test_lists_frozen_files(self):
        p = self._prompt()
        self.assertIn("autows/hooks.py", p)
        self.assertIn("autows/process.py", p)

    def test_enforces_verify_core_and_branch(self):
        p = self._prompt()
        self.assertIn("autows verify-core", p)
        self.assertIn("NEVER run `autows verify-core --update`", p)
        self.assertIn("feature/self-improve-x", p)
        self.assertIn("DO NOT push to main/dev", p)

    def test_dollar_in_lessons_is_safe(self):
        # Injected content with a literal $ must not break Template substitution.
        p = build_improve_prompt(
            outcomes_summary="ok", lessons_text="- watch $PATH and $HOME",
            frozen_files=["autows/hooks.py"], branch="b",
        )
        self.assertIn("$PATH", p)


class OutcomesTest(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix="autows_outcomes_")
        os.chdir(self._tmp)
        import autows.config as cfg
        import autows.outcomes as oc
        importlib.reload(cfg)
        importlib.reload(oc)
        self.oc = oc

    def tearDown(self):
        os.chdir(self._cwd)

    def test_empty_is_zero(self):
        s = self.oc.summarize_recent()
        self.assertEqual(s["sessions"], 0)
        self.assertIn("0 completed sessions", self.oc.format_summary(s))


if __name__ == "__main__":
    unittest.main()
