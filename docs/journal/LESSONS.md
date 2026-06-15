# Lessons

Curated, durable lessons promoted from `data/automation/lessons_log.jsonl` at phase
boundaries (see OPERATOR_GUIDE §7.5). Sessions read this at bootstrap.

## Tooling / platform

- **(gotcha) Windows stdout is cp1252.** Writing an agent/child session's output to
  stdout crashes with `UnicodeEncodeError` when it contains non-ASCII (e.g. the agent's
  `✓`). The CLI reconfigures stdout to UTF-8 and uses a safe-write fallback
  (`cli._write_stdout`). Found by dogfooding `autows phase` on this repo.

## Running autonomous sessions

- **(pitfall) Don't dogfood real workstreams inside a sandboxed parent.** A nested
  headless `claude -p` spawned from inside a sandboxed Claude Code session has no
  file-write/exec capability even with `--allow-dangerously-skip-permissions` — the
  parent harness sandbox still blocks mutations. The orchestration (spawn, timeout,
  audit) works correctly; only the nested agent's writes are blocked. Run real
  autonomous workstreams in a normal (non-sandboxed) terminal.
