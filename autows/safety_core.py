"""Frozen safety core (SPEC S7).

The files listed in FROZEN_FILES implement the safety invariants (protected-branch
isolation, the headless marker, the timeout/process-tree-kill watchdog, the audit
log). A self-improvement loop (Phase 4) MUST NOT alter them. `autows verify-core`
and CI recompute their checksums and fail on drift; the spawn path refuses to run
on drift. Checksums are over LF-normalized content so they're stable across OSes.

Regenerate the manifest intentionally (`autows verify-core --update`) ONLY after a
reviewed change to one of these files.
"""
import hashlib
import os

FROZEN_FILES = [
    "hooks.py",                       # the pre-push hook + installer (S1)
    "config.py",                      # headless markers, protected branches, timeout code
    "process.py",                     # timeout + process-tree-kill watchdog (S3)
    "audit.py",                       # the audit log writer (S4)
    os.path.join("backends", "base.py"),  # sets the headless markers (S1) + spawn path
    "safety_core.py",                 # this guard itself
]

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(_PKG_DIR, "safety_core.sha256")


def _rel_key(rel):
    return rel.replace(os.sep, "/")


def _hash_file(path):
    with open(path, "rb") as f:
        data = f.read().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def compute() -> dict:
    return {_rel_key(rel): _hash_file(os.path.join(_PKG_DIR, rel)) for rel in FROZEN_FILES}


def load_manifest() -> dict:
    out = {}
    if not os.path.exists(MANIFEST):
        return out
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("  ", 1)
            if len(parts) != 2:
                continue
            h, rel = parts
            out[_rel_key(rel.strip())] = h.strip()
    return out


def write_manifest() -> str:
    cur = compute()
    lines = [
        "# Frozen safety core — sha256 of LF-normalized content.",
        "# These files implement the safety invariants (SECURITY.md). A self-",
        "# improvement loop MUST NOT change them; `autows verify-core` and CI fail",
        "# on drift. Regenerate intentionally with `autows verify-core --update`",
        "# only after a reviewed change to a safety-core file.",
    ]
    for rel in FROZEN_FILES:
        k = _rel_key(rel)
        lines.append(f"{cur[k]}  {k}")
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return MANIFEST


def verify_against(expected: dict):
    """Returns (ok: bool, drift: list[(rel, expected_hash, actual_hash)])."""
    cur = compute()
    drift = []
    for rel in FROZEN_FILES:
        k = _rel_key(rel)
        exp = expected.get(k)
        act = cur[k]
        if exp != act:
            drift.append((k, exp, act))
    ok = (len(drift) == 0) and (len(expected) > 0)
    return ok, drift


def verify():
    return verify_against(load_manifest())
