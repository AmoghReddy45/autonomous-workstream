"""Lessons memory — the autoresearch-style accumulating journal (SPEC §8).

Two layers:
- RAW_LESSONS_LOG (append-only JSONL, gitignored): every session appends what it
  learned — gotchas, pitfalls, decisions, reusable patterns.
- CURATED_LESSONS (a version-controlled markdown file): the operator/Terminal
  promotes and dedupes raw lessons here at phase boundaries; because it's
  committed, it passes through human review (see SECURITY.md).

Phase sessions READ this at bootstrap (so knowledge compounds across otherwise-
fresh sessions) and APPEND to it at completion. Curation itself is a judgment
task done by the agent/operator editing CURATED_LESSONS; this module provides the
mechanical add / read / show.
"""
import json
import os
from datetime import datetime, timezone

from . import config

VALID_CATEGORIES = ("gotcha", "pitfall", "decision", "pattern")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add(text, category="gotcha", session_id="", tags=None, files=None) -> dict:
    os.makedirs(os.path.dirname(config.RAW_LESSONS_LOG) or ".", exist_ok=True)
    rec = {
        "timestamp_utc": _now_iso(), "session_id": session_id,
        "category": category, "text": text,
        "tags": list(tags or []), "files": list(files or []),
    }
    with open(config.RAW_LESSONS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")
    return rec


def read_raw() -> list:
    path = config.RAW_LESSONS_LOG
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def read_curated() -> str:
    path = config.CURATED_LESSONS
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    return ""


def format_show(limit=20) -> str:
    parts = []
    curated = read_curated()
    if curated.strip():
        parts.append(f"=== Curated lessons ({config.CURATED_LESSONS}) ===")
        parts.append(curated.rstrip())
    else:
        parts.append(f"(no curated lessons yet at {config.CURATED_LESSONS})")

    raw = read_raw()
    if raw:
        recent = raw[-limit:]
        parts.append("")
        parts.append(f"=== Recent raw lessons (last {len(recent)} of {len(raw)}) ===")
        for r in recent:
            tags = (" [" + ",".join(r.get("tags", [])) + "]") if r.get("tags") else ""
            parts.append(f"- ({r.get('category', '?')}) {r.get('text', '')}{tags}")
    return "\n".join(parts)
