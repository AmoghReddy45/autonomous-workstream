"""Thin, cross-platform git helpers (stdlib only)."""
import subprocess


def _git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True
    )


def inside_work_tree() -> bool:
    r = _git("rev-parse", "--is-inside-work-tree")
    return r.returncode == 0 and r.stdout.strip() == "true"


def toplevel():
    """Absolute path to the repo root, or None if not in a git repo."""
    r = _git("rev-parse", "--show-toplevel")
    return r.stdout.strip() if r.returncode == 0 else None


def head_sha() -> str:
    r = _git("rev-parse", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else ""


def current_branch() -> str:
    r = _git("branch", "--show-current")
    return r.stdout.strip() if r.returncode == 0 else ""
