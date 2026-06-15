"""autows command-line interface.

Subcommands (cross-platform replacements for the original PowerShell scripts):

    autows install-hooks                  -> install_safety_hooks.ps1
    autows spawn   --prompt ... [...]     -> spawn_headless_session.ps1
    autows phase   --workstream ... [...] -> spawn_phase_session.ps1
    autows answer  --qfile ... [...]      -> answer_question.ps1
"""
import argparse
import json
import os
import re
import sys
import time

from . import audit, config, gitutil, hooks, lessons, prompts, safety_core
from .backends import available, get_backend


def _read_prompt(args) -> str:
    if args.prompt is not None:
        return args.prompt
    if args.prompt_file is not None:
        with open(args.prompt_file, encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("ERROR: provide a prompt via --prompt, --prompt-file, or stdin.")


def _do_spawn(prompt: str, label: str, timeout: int, backend_name: str) -> int:
    """Shared spawn path used by both `spawn` and `phase`."""
    if not gitutil.inside_work_tree():
        print("ERROR: not inside a git work tree. cd to the project root first.",
              file=sys.stderr)
        return 1
    if not os.path.isdir(".claude"):
        print("WARNING: no .claude/ at cwd — agents/skills may not load for the "
              "child. Continuing.", file=sys.stderr)

    git_root = gitutil.toplevel()
    hook = os.path.join(git_root, ".git", "hooks", "pre-push")
    if not os.path.exists(hook):
        print("ERROR: pre-push safety hook not installed. Run `autows install-hooks` "
              "first.", file=sys.stderr)
        return 1

    backend = get_backend(backend_name)
    audit.ensure_dirs()
    session_id = audit.new_session_id(label)
    head_before = gitutil.head_sha()
    branch_before = gitutil.current_branch()

    audit.write_record(session_id, {
        "timestamp": audit.now_iso(), "event": "spawn", "session_id": session_id,
        "label": label, "backend": backend.name, "head_sha": head_before,
        "branch_at_spawn": branch_before, "prompt_first_200_chars": prompt[:200],
        "prompt_length": len(prompt), "timeout_seconds": timeout,
    })

    start = time.time()
    result = backend.spawn_headless(prompt, timeout)
    duration = round(time.time() - start, 1)

    head_after = gitutil.head_sha()
    branch_after = gitutil.current_branch()
    output = result.stdout
    if result.timed_out:
        output = f"[wrapper] Exceeded {timeout}s; process tree killed.\n" + output

    audit.write_record(session_id, {
        "timestamp": audit.now_iso(), "event": "complete", "session_id": session_id,
        "duration_seconds": duration, "exit_code": result.exit_code,
        "head_sha_after": head_after, "branch_after": branch_after,
        "head_changed": head_before != head_after,
        "branch_changed": branch_before != branch_after,
        "output_first_500_chars": output[:500], "output_length": len(output),
        "timed_out": result.timed_out,
    })

    sys.stdout.write(output)
    if not output.endswith("\n"):
        sys.stdout.write("\n")
    print("---")
    print(f"Headless session {session_id} complete. Duration: {duration}s. "
          f"Exit: {result.exit_code}.")
    print(f"Branch before: {branch_before} ({head_before}). "
          f"After: {branch_after} ({head_after}).")
    print(f"Audit log: {audit.log_path(session_id)}")
    return result.exit_code


def cmd_spawn(args) -> int:
    return _do_spawn(_read_prompt(args), args.label, args.timeout, args.backend)


def cmd_phase(args) -> int:
    date = time.strftime("%Y%m%d-%H%M%S")
    session_id = (f"{args.workstream}-phase-{args.phase}"
                  f"-session-{args.session_in_phase}-{date}")
    branch = args.branch_override or f"{args.branch_prefix}/{args.workstream}-phase-{args.phase}"
    backend = get_backend(args.backend)
    prompt = prompts.build_phase_prompt(
        session_id=session_id, workstream=args.workstream, phase=args.phase,
        session_in_phase=args.session_in_phase, branch=branch, scope=args.scope,
        guidance=args.guidance, worker_type=args.worker_type,
        gate_commands=args.gate_commands,
        supports_subagents=backend.supports_subagents,
    )
    print(f"Spawning phase session: {session_id} (branch: {branch}, "
          f"timeout: {args.timeout}s)", file=sys.stderr)
    return _do_spawn(prompt, session_id, args.timeout, args.backend)


def cmd_answer(args) -> int:
    if not os.path.exists(args.qfile):
        print(f"ERROR: Q file not found: {args.qfile}", file=sys.stderr)
        return 1
    # utf-8-sig tolerates a UTF-8 BOM (PowerShell's Out-File writes one) and is
    # fine for plain UTF-8 too.
    with open(args.qfile, encoding="utf-8-sig") as f:
        q = json.load(f)

    if args.show_only:
        print()
        print("==== QUESTION FROM HEADLESS PHASE SESSION ====")
        print(f"session_id: {q.get('session_id')}   seq: {q.get('sequence_num')}   "
              f"category: {q.get('category')}")
        print(f"blocking: {q.get('blocking_subtask')}   "
              f"deadline: {q.get('phase_session_will_wait_until')}")
        print()
        print(f"QUESTION: {q.get('question')}")
        print(f"CONTEXT:  {q.get('context')}")
        print("OPTIONS:")
        for o in q.get("options", []):
            print(f"  - {o}")
        print(f"RECOMMENDED: {q.get('recommended')}")
        print("==============================================")
        print("Copy into architect chat; then re-run with --answer/--rationale to unblock.")
        return 0

    if not args.answer:
        print("ERROR: --answer required unless --show-only.", file=sys.stderr)
        return 1

    name = os.path.basename(args.qfile)
    m = re.match(r"^Q_(.+)_(\d+)\.json$", name)
    if not m:
        print(f"ERROR: Q file name doesn't match Q_<session_id>_<seq>.json: {name}",
              file=sys.stderr)
        return 1
    a_name = f"A_{m.group(1)}_{m.group(2)}.json"
    os.makedirs(config.OUTBOX_DIR, exist_ok=True)
    a_path = os.path.join(config.OUTBOX_DIR, a_name)
    with open(a_path, "w", encoding="utf-8") as f:
        json.dump({
            "session_id": q.get("session_id"), "sequence_num": q.get("sequence_num"),
            "timestamp_utc": audit.now_iso(), "answer": args.answer,
            "rationale": args.rationale, "signed_by": args.signed_by,
            "additional_context": args.additional_context,
        }, f, indent=2)
    print(f"Wrote {a_path} - phase session {q.get('session_id')} resumes on next "
          f"poll (<=30s).")
    return 0


def _split(csv):
    return [s.strip() for s in csv.split(",") if s.strip()]


def cmd_lessons_add(args) -> int:
    rec = lessons.add(
        text=args.text, category=args.category, session_id=args.session_id,
        tags=_split(args.tags), files=_split(args.files),
    )
    print(f"Recorded lesson ({rec['category']}) to {config.RAW_LESSONS_LOG}")
    return 0


def cmd_lessons_show(args) -> int:
    print(lessons.format_show(limit=args.limit))
    return 0


def cmd_verify_core(args) -> int:
    if args.update:
        path = safety_core.write_manifest()
        print(f"Wrote frozen-core manifest: {path}")
        print(f"({len(safety_core.FROZEN_FILES)} files). Commit it so the change is reviewed.")
        return 0
    ok, drift = safety_core.verify()
    if ok:
        print(f"Frozen safety core OK ({len(safety_core.FROZEN_FILES)} files verified).")
        return 0
    print("FROZEN SAFETY CORE DRIFT DETECTED:", file=sys.stderr)
    if not safety_core.load_manifest():
        print("  No manifest (autows/safety_core.sha256). Generate it with "
              "`autows verify-core --update`.", file=sys.stderr)
    for rel, exp, act in drift:
        print(f"  {rel}: expected {exp or '(missing)'} got {act}", file=sys.stderr)
    print("If this change was intentional and reviewed, regenerate with "
          "`autows verify-core --update`.", file=sys.stderr)
    return 1


def cmd_install_hooks(args) -> int:
    git_root = gitutil.toplevel()
    if not git_root:
        print("ERROR: not inside a git repo.", file=sys.stderr)
        return 1
    dst = hooks.install_pre_push(git_root)
    print(f"Installed: {dst}")
    print()
    print("Verify:")
    print('  echo "refs/heads/main abc refs/heads/main def" | '
          'AUTOWS_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"   # expect 1')
    print('  echo "refs/heads/feature/x abc refs/heads/feature/x def" | '
          'AUTOWS_HEADLESS=1 bash .git/hooks/pre-push; echo "EXIT=$?"   # expect 0')
    print()
    print("STRONGLY RECOMMENDED next: add origin-side branch protection on main + dev")
    print("(the local hook is bypassable; origin protection is the non-bypassable layer).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autows",
        description="Autonomous Workstream — spawn and supervise headless agent "
                    "sessions safely. See SPEC.md and SECURITY.md.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("install-hooks", help="install the pre-push safety hook")
    sp.set_defaults(func=cmd_install_hooks)

    sp = sub.add_parser("verify-core", help="verify the frozen safety core hasn't drifted")
    sp.add_argument("--update", action="store_true",
                    help="regenerate the manifest after a reviewed safety-core change")
    sp.set_defaults(func=cmd_verify_core)

    sp = sub.add_parser("spawn", help="spawn a low-level headless session")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--prompt", help="the prompt text")
    g.add_argument("--prompt-file", help="read the prompt from a file")
    sp.add_argument("--label", default="untitled", help="session label (audit log)")
    sp.add_argument("--timeout", type=int, default=config.DEFAULT_TIMEOUT_SECONDS,
                    help="wall-clock timeout in seconds")
    sp.add_argument("--backend", default="claude", choices=available(),
                    help="agent backend")
    sp.set_defaults(func=cmd_spawn)

    sp = sub.add_parser("phase", help="spawn a phase session (prompt is built for you)")
    sp.add_argument("--workstream", required=True)
    sp.add_argument("--phase", type=int, required=True)
    sp.add_argument("--session-in-phase", type=int, required=True)
    sp.add_argument("--scope", required=True, help="1-3 sentence bounded scope")
    sp.add_argument("--guidance", default="", help="doc refs, prior commits, pre-baked decisions")
    sp.add_argument("--worker-type", default="general-purpose")
    sp.add_argument("--gate-commands",
                    default="the project's standard build/test/lint gates (see CLAUDE.md)")
    sp.add_argument("--branch-prefix", default="feature")
    sp.add_argument("--branch-override", default="")
    sp.add_argument("--timeout", type=int, default=config.DEFAULT_PHASE_TIMEOUT_SECONDS)
    sp.add_argument("--backend", default="claude", choices=available())
    sp.set_defaults(func=cmd_phase)

    sp = sub.add_parser("answer", help="answer (or show) a phase session's question")
    sp.add_argument("--qfile", required=True, help="path to data/automation/inbox/Q_*.json")
    sp.add_argument("--answer", default="")
    sp.add_argument("--rationale", default="")
    sp.add_argument("--signed-by", default="operator",
                    help="operator | architect-chat | terminal-autonomous")
    sp.add_argument("--additional-context", default="")
    sp.add_argument("--show-only", action="store_true",
                    help="print the question for routing instead of answering")
    sp.set_defaults(func=cmd_answer)

    sp = sub.add_parser("lessons", help="accumulated lessons memory (read / append)")
    lsub = sp.add_subparsers(dest="lessons_cmd", required=True)
    la = lsub.add_parser("add", help="append a lesson for future sessions")
    la.add_argument("--text", required=True)
    la.add_argument("--category", default="gotcha", choices=list(lessons.VALID_CATEGORIES))
    la.add_argument("--session-id", default="")
    la.add_argument("--tags", default="", help="comma-separated")
    la.add_argument("--files", default="", help="comma-separated")
    la.set_defaults(func=cmd_lessons_add)
    ls = lsub.add_parser("show", help="print curated + recent raw lessons")
    ls.add_argument("--limit", type=int, default=20)
    ls.set_defaults(func=cmd_lessons_show)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
