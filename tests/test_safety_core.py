"""Frozen safety core (SPEC S7) checksum guard tests."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autows import safety_core  # noqa: E402


class SafetyCoreTest(unittest.TestCase):
    def test_compute_covers_all_frozen_files(self):
        keys = set(safety_core.compute().keys())
        expected = {safety_core._rel_key(r) for r in safety_core.FROZEN_FILES}
        self.assertEqual(keys, expected)

    def test_committed_manifest_matches_current_files(self):
        ok, drift = safety_core.verify()
        self.assertTrue(ok, f"frozen-core drift vs committed manifest: {drift}")

    def test_drift_is_detected(self):
        expected = safety_core.compute()
        tampered = next(iter(expected))
        expected[tampered] = "0" * 64
        ok, drift = safety_core.verify_against(expected)
        self.assertFalse(ok)
        self.assertTrue(any(d[0] == tampered for d in drift))

    def test_empty_manifest_is_not_ok(self):
        ok, _ = safety_core.verify_against({})
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
