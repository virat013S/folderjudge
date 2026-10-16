"""Execution. NOTHING is ever deleted — removals go to FolderJudge's own
trash with a manifest, and `folderjudge restore` puts everything back."""
from __future__ import annotations

import json
import platform as py_platform
import shutil
import time
import uuid
from pathlib import Path

from . import APP, __version__
from .plan import ACT_ARCHIVE, ACT_TRASH, ACTIONS, Plan
from .utils import human, paths, stored_name, unique_path


def _session_dir() -> tuple[Path, str]:
    trash_root = paths()["trash"]
    trash_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H%M%S")
    for tag in (uuid.uuid4().hex[:4],):
        d = trash_root / f"{stamp}--{tag}"
        if not d.exists():
            d.mkdir(parents=True)
            return d, d.name
    return d, d.name


def _protection_check(f: Path) -> str | None:
    """Last line of defense against touching something the OS cares about."""
    try:
        st = f.stat()
        if getattr(st, "st_file_attributes", 0) & (0x2 | 0x4):  # HIDDEN | SYSTEM (Win)
            return "hidden/system attribute"
    except OSError:
        return "unreadable"
    return None


def confirm_text(plan: Plan) -> str:
    trash = plan.group(ACT_TRASH)
    arch = plan.group(ACT_ARCHIVE)
    freed = plan.bytes_moved(ACT_TRASH, ACT_ARCHIVE)
    lines = [
        "",
        f"  {len(trash)} file(s) -> trash    ({human(plan.bytes_moved(ACT_TRASH))})",
        f"  {len(arch)} file(s) -> archive  ({human(plan.bytes_moved(ACT_ARCHIVE))})",
        f"  total freespace: {human(freed)}   ·   nothing deleted, all restorable",
    ]
    big = max(trash + arch, key=lambda d: d.info.size, default=None)
    if big and big.info.size > 500 * 1024 * 1024:
        lines.append(f"  ⚠ moving '{big.info.name}' ({human(big.info.size)})")
    return "\n".join(lines)


def execute(plan: Plan, *, assume_yes: bool = False) -> Path | None:
    moves = [d for d in plan.decisions if d.action in (ACT_TRASH, ACT_ARCHIVE)]
    if not moves:
        return None

    print(confirm_text(plan))
    if not assume_yes:
        try:
            ans = input("  execute the sentence? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = ""
        if ans not in ("y", "yes"):
            print("  spared. nothing moved.")
            return None

    session, session_id = _session_dir()
    sessions = session / "files"
    sessions.mkdir()

    manifest_entries = []
    failed = []
    for d in moves:
        src: Path = d.info.path
        block = _protection_check(src)
        if block:
            failed.append((src, block))
            continue
        dst = unique_path(sessions / stored_name(d.info.name))
        try:
            shutil.move(str(src), str(dst))
        except (shutil.Error, OSError) as e:
            failed.append((src, str(e)))
            continue
        manifest_entries.append({
            "src": str(src),
            "dst": str(dst),
            "action": d.action,
            "reason": d.reason,
            "size": d.info.size,
        })

    meta = {
        "app": APP, "version": __version__, "session": session_id,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": py_platform.platform(),
    }
    (session / "manifest.json").write_text(
        json.dumps({"meta": meta, "files": manifest_entries}, indent=2),
        encoding="utf-8",
    )

    if failed:
        print(f"  skipped {len(failed)} (locked/permitted-out): see manifest")
    return session


def list_sessions() -> list[Path]:
    root = paths()["trash"]
    if not root.is_dir():
        return []
    return sorted([d for d in root.iterdir() if (d / "manifest.json").is_file()],
                  key=lambda d: d.name, reverse=True)


def restore(session_id: str | None = None, *, last: bool = False, assume_yes: bool = False) -> int:
    sessions = list_sessions()
    if not sessions:
        print("  nothing to restore — trash is empty. Ibn Battuta, meet the desert")
        return 0

    session: Path
    if last:
        session = sessions[0]
    elif session_id:
        match = next((s for s in sessions if session_id in s.name), None)
        if not match:
            print(f"  no session matches '{session_id}'")
            return 1
        session = match
    else:
        for i, s in enumerate(sessions[:10], 1):
            n = _session_count(s)
            print(f"  {i}. {s.name}  ({n} files)")
        try:
            pick = input("  restore which? [1/number/Enter=quit] ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if not pick.isdigit() or not (1 <= int(pick) <= min(10, len(sessions))):
            print("  nullDeep. cancel.")
            return 0
        session = sessions[int(pick) - 1]

    bundle = json.loads((session / "manifest.json").read_text(encoding="utf-8"))
    entries = bundle.get("files", [])
    if not assume_yes:
        freed = sum(e.get("size", 0) for e in entries)
        print(f"  session {session.name}: {len(entries)} files, {human(freed)}")
        try:
            ans = input("  bring them home? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = ""
        if ans not in ("y", "yes"):
            print("  staying in the bin.")
            return 0

    restored, gone, blok = 0, 0, 0
    log = []
    for e in entries:
        src = Path(e["dst"])
        back = Path(e["src"])
        if not src.exists():
            gone += 1
            continue
        parent = back.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            home = back if not back.exists() else unique_path(back)
            shutil.move(str(src), str(home))
        except (shutil.Error, OSError):
            blok += 1
            continue
        restored += 1
        log.append({"from_trash": str(src), "back_to": str(home)})

    if log:
        (session / "restore-log.json").write_text(
            json.dumps({"meta": bundle["meta"], "restored": log}, indent=2), encoding="utf-8")
    print(f"  restored {restored} · already-gone {gone} · blocked {blok}")
    return restored


def _session_count(session: Path) -> int:
    try:
        bundle = json.loads((session / "manifest.json").read_text(encoding="utf-8"))
        return len(bundle.get("files", []))
    except Exception:
        return -1
