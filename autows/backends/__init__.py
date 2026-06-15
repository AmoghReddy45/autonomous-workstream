"""Backend registry. Add a new backend by importing + registering it here."""
from .base import Backend, SpawnResult
from .claude import ClaudeBackend
from .codex import CodexBackend

_BACKENDS = {
    ClaudeBackend.name: ClaudeBackend,
    CodexBackend.name: CodexBackend,
}


def available():
    return sorted(_BACKENDS)


def get_backend(name: str) -> Backend:
    try:
        return _BACKENDS[name]()
    except KeyError:
        raise SystemExit(
            f"Unknown backend {name!r}. Available: {', '.join(available())}"
        )


__all__ = ["Backend", "SpawnResult", "get_backend", "available"]
