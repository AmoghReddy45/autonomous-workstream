"""CLI robustness tests (regression for dogfood-found bugs)."""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autows import cli  # noqa: E402


class WriteStdoutTest(unittest.TestCase):
    def test_survives_unencodable_char_on_cp1252_stdout(self):
        # Regression: an agent's '✓' (U+2713) in child output crashed the wrapper
        # on a Windows cp1252 stdout. The helper must not raise.
        real = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
        try:
            cli._write_stdout("status: ok ✓ done\n")  # would raise without the guard
            sys.stdout.flush()
        finally:
            captured = sys.stdout
            sys.stdout = real
        self.assertTrue(captured.buffer.getvalue())  # something was written


if __name__ == "__main__":
    unittest.main()
