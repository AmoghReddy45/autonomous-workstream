"""Shared constants for the Autonomous Workstream CLI.

All runtime artifacts (audit log, Q&A inbox/outbox, lessons log) live under a
single gitignored directory inside the *consuming* project.
"""
import os

DATA_DIR = os.path.join("data", "automation")
HEADLESS_LOG_DIR = os.path.join(DATA_DIR, "headless_log")
INBOX_DIR = os.path.join(DATA_DIR, "inbox")
OUTBOX_DIR = os.path.join(DATA_DIR, "outbox")

# Branches a headless session must never push to (the pre-push hook enforces it).
PROTECTED_BRANCHES = ("main", "dev")

# Headless marker env vars. The spawn layer sets BOTH; the pre-push hook blocks
# protected-branch pushes when EITHER is set. AUTOWS_HEADLESS is canonical;
# CLAUDE_HEADLESS is kept for backward compatibility with the original scripts.
HEADLESS_ENV_VARS = ("AUTOWS_HEADLESS", "CLAUDE_HEADLESS")

# Distinguishable exit code when the wrapper kills a hung process tree.
TIMEOUT_EXIT_CODE = -2

DEFAULT_TIMEOUT_SECONDS = 1800
DEFAULT_PHASE_TIMEOUT_SECONDS = 7200
