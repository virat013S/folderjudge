"""CLI front door.

    folderjudge                  judge your Downloads folder
    folderjudge <path>           judge any folder
    folderjudge <path> --deep    also judge subfolders
    folderjudge --dry-run        verdict only, no file moves
    folderjudge restore          undo a session (--last / --list / <name>)
    folderjudge report           open or print the latest markdown verdict
    folderjudge ai               check the local model setup
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import APP, __version__
from .utils import c, colors_on, default_target, ensure_dirs, paint

EPILOG = (
    "safety: nothing is deleted. removals go into FolderJudge's own trash with a\n"
    "manifest — `folderjudge restore` puts files back exactly where they were.\n"
    "AI: uses your local Ollama (free, offline). without it, heuristics still judge."
)

SPECIAL = ("restore", "report", "ai")
AI_CAP = 300


# ------------------------------------------------------------------ judge --

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="folderjudge",
        description=f"{APP} {__version__} — an AI judge for messy folders. It sees your "
                    "Downloads. It has opinions. Nothing goes without sign-off.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", nargs="?", default=None,
                   help="folder to judge (default: your Downloads)")
    p.add_argument("--deep", action="store_true", help="also judge inside subfolders")
    p.add_argument("--dry-run", action="store_true", help="verdict only — never move a file")
    p.add_argument("--yes", action="store_true", help="skip the execute confirmation")
    p.add_argument("--no-ai", action="store_true", help="skip the local model — heuristics only")
    p.add_argument("--persona", default="judge", choices=["judge", "butler", "gremlin"],
                   help="the judge's temperament (default: judge)")
    p.add_argument("--include-hidden", action="store_true", help="also judge dotfiles/hidden")
    p.add_argument("--version", action="version", version=f"folderjudge {__version__}")
    return p


def _restore_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="folderjudge restore",
                                description="put files from a cleanup session back home")
    p.add_argument("--last", action="store_true", help="restore the newest session, no menu")
    p.add_argument("--list", action="store_true", help="list recent sessions, no actions")
    p.add_argument("--yes", action="store_true", help="no prompts")
    p.add_argument("session", nargs="?", default=None, help="session name (or part of one)")
    return p


def main(argv: list[str] | None = None) -> int:
    colors_on()
    ensure_dirs()
    raw = list(sys.argv[1:] if argv is None else argv)

    head = raw[0] if raw else None
    if head == "restore":
        args, rest = _restore_parser().parse_known_args(raw[1:])
        if args.list:
            from .executor import list_sessions
            sessions = list_sessions()
            if not sessions:
                print(c("2", "  trash empty — no sessions yet."))
                return 0
            for s in sessions[:15]:
                print(f"  {s.name}  ({_count(s)} files)")
            return 0
        from .executor import restore
        restore(args.session, last=args.last, assume_yes=args.yes)
        return 0

    if head == "report":
        from .reporter import open_report, print_last_report
        argset = raw[1:]
        ok = (open_report if "--open" in argset else print_last_report)()
        return 0 if ok else 1

    if head == "ai":
        from .ai_ollama import ping, pick_model
        info = ping()
        if not info:
            print(c("33", "  Ollama: not reachable (fine — heuristic mode still works)"))
            print(c("2", "  linux:   curl -fsSL https://ollama.com/install.sh | sh"))
            print(c("2", "  macos:   brew install ollama && ollama serve"))
            print(c("2", "  windows: winget install Ollama.Ollama"))
            print(c("2", "  then:    ollama pull gemma3:1b"))
            return 0
        models = info["models"]
        print(c("32", "  Ollama: up (localhost:11434)"))
        print(f"  models: {', '.join(models) or '(none pulled yet — `ollama pull gemma3:1b`)'}")
        print(f"  judge : {pick_model(models) or '(no model available)'}")
        return 0

    args = _parser().parse_args(raw)
    return _judge(args)


def _judge(args) -> int:
    from .ai_ollama import ping, pick_model
    from .ai_ollama import analyze as ai_analyze
    from .executor import execute
    from .heuristic import analyze as heuristics
    from .plan import merge_ai
    from .persona import get as get_persona
    from .reporter import render, save
    from .scanner import scan

    raw = args.path
    target = Path(raw).expanduser() if raw else default_target()
    if target is None or not Path(target).is_dir():
        print(c("31", f"  not a folder: {raw or '(no Downloads found)'} — pass one: folderjudge <path>"))
        return 2
    target = Path(target).resolve()

    persona = get_persona(args.persona)
    files = scan(target, deep=args.deep, include_hidden=args.include_hidden)
    if not files:
        print(paint(f"  {target} is immaculate. the judge respects this.", "32"))
        return 0

    plan = heuristics(files, persona)
    ai_note = c("2", " · heuristics only")
    if not args.no_ai:
        info = ping()
        if info and info["models"]:
            model = pick_model(info["models"])
            print(c("2", f"  summoning local judge — {model} (offline, private; loads slowly the first time)"))
            ai = ai_analyze(files, persona, model)
            if ai:
                plan = merge_ai(plan, ai)
                ai_note = c("32", f" · AI judge: {ai['meta']['model']} (offline)")
                if len(files) > AI_CAP:
                    print(c("33", f"  note: AI judged the first {AI_CAP} of {len(files)} files; "
                                   "the rest by heuristics"))
            else:
                ai_note = c("33", " · heuristics (model hiccoughed)")
        else:
            ai_note = c("33", " · heuristics (Ollama off — `folderjudge ai` for setup)")

    render(plan, target, persona, deep=args.deep, dry=args.dry_run, ai_note=ai_note)
    report = save(plan, target, persona, ai_note=ai_note, dry=args.dry_run)
    print(c("2", f"  report: {report}"))
    if args.dry_run:
        print(c("33", "  dry-run — nothing moved. drop --dry-run to execute the sentence."))
        return 0

    session = execute(plan, assume_yes=args.yes)
    if session:
        print(c("32", f"  done. session {session.name} — undo anytime: folderjudge restore --last"))
    return 0


def _count(session: Path) -> int:
    import json
    try:
        return len(json.loads((session / "manifest.json").read_text(encoding="utf-8"))["files"])
    except Exception:
        return -1
