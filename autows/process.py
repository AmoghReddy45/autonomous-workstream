"""Cross-platform headless process execution with a timeout watchdog.

Mirrors the load-bearing behaviour of the original PowerShell wrapper, portably:

- Prompt is fed via a temp file on stdin (not a CLI argument) so multi-line
  prompts are never truncated by shell quote-mangling.
- stdout+stderr go to a temp file (not a pipe) so large output can't deadlock,
  and partial output is still recoverable after a forced kill.
- On timeout the *whole process tree* is killed: POSIX via the session's
  process group, Windows via `taskkill /F /T`. `claude -p` can hang at exit on
  long sessions even after committing, so this watchdog is required, not optional.

Zero third-party dependencies.
"""
import os
import shutil
import signal
import subprocess
import tempfile

from .config import TIMEOUT_EXIT_CODE


def _resolve(argv):
    """Resolve argv[0] on PATH (incl. .cmd/.bat shims on Windows)."""
    exe = shutil.which(argv[0])
    if exe is None:
        raise FileNotFoundError(
            f"Executable not found on PATH: {argv[0]!r}. "
            "Is the agent backend installed and on PATH?"
        )
    real = [exe, *argv[1:]]
    # CreateProcess can't run .cmd/.bat directly; route them through cmd.exe.
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        real = ["cmd", "/c", *real]
    return real


def _kill_tree(pid):
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def run_with_timeout(argv, prompt, timeout_seconds, env=None):
    """Run argv non-interactively, feeding `prompt` on stdin.

    Returns (output: str, exit_code: int, timed_out: bool).
    """
    real = _resolve(argv)
    in_fd, in_path = tempfile.mkstemp()
    out_fd, out_path = tempfile.mkstemp()
    os.close(out_fd)
    try:
        with os.fdopen(in_fd, "wb") as f:
            f.write(prompt.encode("utf-8"))

        popen_kwargs = dict(env=env)
        if os.name != "nt":
            # New session => its own process group, so we can kill the whole tree.
            popen_kwargs["start_new_session"] = True

        with open(in_path, "rb") as stdin_f, open(out_path, "wb") as stdout_f:
            proc = subprocess.Popen(
                real, stdin=stdin_f, stdout=stdout_f,
                stderr=subprocess.STDOUT, **popen_kwargs,
            )
            timed_out = False
            try:
                proc.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_tree(proc.pid)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass

        with open(out_path, "rb") as f:
            output = f.read().decode("utf-8", "replace")

        if timed_out:
            exit_code = TIMEOUT_EXIT_CODE
        elif proc.returncode is None:
            exit_code = -1
        else:
            exit_code = proc.returncode
        return output, exit_code, timed_out
    finally:
        for p in (in_path, out_path):
            try:
                os.unlink(p)
            except OSError:
                pass
