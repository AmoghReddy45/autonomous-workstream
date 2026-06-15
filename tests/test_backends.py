"""Backend registry + prompt-adaptation tests."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autows.backends import available, get_backend  # noqa: E402
from autows.prompts import build_phase_prompt  # noqa: E402


def _kw(**over):
    base = dict(
        session_id="s1", workstream="w", phase=1, session_in_phase=1,
        branch="feature/x", scope="do the thing", guidance="g",
        worker_type="general-purpose", gate_commands="make test",
    )
    base.update(over)
    return base


class BackendRegistryTest(unittest.TestCase):
    def test_both_registered(self):
        self.assertIn("claude", available())
        self.assertIn("codex", available())

    def test_claude_command(self):
        b = get_backend("claude")
        self.assertEqual(b.command(), ["claude", "-p", "--allow-dangerously-skip-permissions"])
        self.assertTrue(b.supports_subagents)

    def test_codex_command(self):
        b = get_backend("codex")
        self.assertEqual(
            b.command(),
            ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "-"],
        )
        self.assertFalse(b.supports_subagents)

    def test_env_sets_both_markers(self):
        e = get_backend("claude").env()
        self.assertEqual(e["AUTOWS_HEADLESS"], "1")
        self.assertEqual(e["CLAUDE_HEADLESS"], "1")

    def test_unknown_backend_exits(self):
        with self.assertRaises(SystemExit):
            get_backend("nope")


class PromptAdaptationTest(unittest.TestCase):
    def test_subagent_variant(self):
        p = build_phase_prompt(supports_subagents=True, **_kw())
        self.assertIn("subagent", p)
        self.assertIn("feature/x", p)
        self.assertIn("make test", p)

    def test_self_execution_variant(self):
        p = build_phase_prompt(supports_subagents=False, **_kw())
        self.assertIn("complete it yourself", p)
        self.assertIn("no subagent", p)


if __name__ == "__main__":
    unittest.main()
