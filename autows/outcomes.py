"""Summarize recent run outcomes from the audit log.

Read-only over the audit log (audit.py is frozen; this reader is not). Feeds the
self-improvement loop a signal of what's going wrong — timeouts, non-zero exits,
hard-stops — so improvements can target real problems, not guesses.
"""
import glob
import json
import os

from . import config

_FAIL_MARKERS = ("BLOCKED", "DOORMAN_FAIL", "HARD-STOP", "hard-stop")


def summarize_recent(limit=20) -> dict:
    files = sorted(glob.glob(os.path.join(config.HEADLESS_LOG_DIR, "*.jsonl")))
    files = files[-limit:]
    s = {"files": len(files), "sessions": 0, "timeouts": 0,
         "nonzero_exit": 0, "blocked_or_failed": 0}
    for fp in files:
        try:
            with open(fp, encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("event") != "complete":
                        continue
                    s["sessions"] += 1
                    if rec.get("timed_out"):
                        s["timeouts"] += 1
                    if rec.get("exit_code") not in (0, None):
                        s["nonzero_exit"] += 1
                    out = rec.get("output_first_500_chars") or ""
                    if any(m in out for m in _FAIL_MARKERS):
                        s["blocked_or_failed"] += 1
        except OSError:
            continue
    return s


def format_summary(s: dict) -> str:
    return (
        f"{s['sessions']} completed sessions across {s['files']} log files: "
        f"{s['timeouts']} timed out, {s['nonzero_exit']} non-zero exit, "
        f"{s['blocked_or_failed']} blocked/hard-stopped."
    )
