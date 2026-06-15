"""Backend registry. Phase 2 adds a Codex backend here."""
from .base import Backend, SpawnResult
from .claude import ClaudeBackend

_BACKENDS = {
    ClaudeBackend.name: ClaudeBackend,
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
