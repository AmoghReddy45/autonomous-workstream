"""Lessons memory round-trip tests.

Lessons paths are resolved from config at call time and are relative to CWD, so
each test runs in a temporary working directory.
"""
import importlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LessonsTest(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix="autows_lessons_")
        os.chdir(self._tmp)
        # Re-import so config re-evaluates its CWD-relative path defaults.
        import autows.config as cfg
        import autows.lessons as les
        importlib.reload(cfg)
        importlib.reload(les)
        self.les = les

    def tearDown(self):
        os.chdir(self._cwd)

    def test_add_then_read_raw(self):
        self.les.add(text="protoc must be on PATH", category="gotcha",
                     session_id="s1", tags=["build", "env"])
        raw = self.les.read_raw()
        self.assertEqual(len(raw), 1)
        self.assertEqual(raw[0]["text"], "protoc must be on PATH")
        self.assertEqual(raw[0]["category"], "gotcha")
        self.assertEqual(raw[0]["tags"], ["build", "env"])

    def test_show_includes_raw_and_curated(self):
        os.makedirs(os.path.dirname(self.les.config.CURATED_LESSONS), exist_ok=True)
        with open(self.les.config.CURATED_LESSONS, "w", encoding="utf-8") as f:
            f.write("# Lessons\n- The X module has hidden coupling to Y.\n")
        self.les.add(text="flaky test: retry network suite", category="pitfall")
        out = self.les.format_show()
        self.assertIn("hidden coupling", out)
        self.assertIn("flaky test", out)
        self.assertIn("(pitfall)", out)

    def test_show_empty_is_graceful(self):
        out = self.les.format_show()
        self.assertIn("no curated lessons yet", out)


if __name__ == "__main__":
    unittest.main()
