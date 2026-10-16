"""The heuristic judge — zero AI, works everywhere, and is the fallback."""
from __future__ import annotations

from .categorize import JUNK, INSTALLER
from .plan import ACT_KEEP, ACT_ARCHIVE, ACT_REVIEW, ACT_TRASH, Plan, Decision
from .scanner import FileInfo
from .persona import Persona

HUGE = 1024 * 1024 * 1024          # 1 GB
BIG_INSTALLER = 100 * 1024 * 1024  # 100 MB
OLD_INSTALLER_DAYS = 30
FRESH_DAYS = 2


def analyze(files: list[FileInfo], persona: Persona) -> Plan:
    # -- duplicate groups: newest copy keeps the crown -------------------------
    dupe_trash: dict[int, tuple[int, str]] = {}   # idx -> (keeper_idx, keeper name)
    groups: dict[str, list[int]] = {}
    for i, f in enumerate(files):
        if f.sig:
            groups.setdefault(f.sig, []).append(i)
    for members in groups.values():
        if len(members) > 1:
            keeper = max(members, key=lambda i: files[i].mtime)
            for i in members:
                if i != keeper:
                    dupe_trash[i] = (keeper, files[keeper].name)

    decisions: list[Decision] = []
    for i, f in enumerate(files):
        fresh = f.age_days < FRESH_DAYS

        if f.category == JUNK:
            decisions.append(Decision(f, ACT_TRASH, "leftover partial download, never finished"))

        elif i in dupe_trash:
            keeper_name = dupe_trash[i][1]
            decisions.append(Decision(f, ACT_TRASH, f"identical copy of {keeper_name}"))

        elif f.category == INSTALLER:
            if f.size >= BIG_INSTALLER and f.age_days >= OLD_INSTALLER_DAYS:
                decisions.append(Decision(f, ACT_TRASH, f"big installer ({f.age_days:.0f}d old) — reinstallable, rusting"))
            elif fresh:
                decisions.append(Decision(f, ACT_KEEP, "installed today — not judging yet"))
            else:
                decisions.append(Decision(f, ACT_REVIEW, f"installer loose {f.age_days:.0f} days; already using it?"))

        elif f.size >= HUGE and f.age_days >= 30 and f.category not in ("document",):
            decisions.append(Decision(f, ACT_REVIEW, f"{f.size / 1024 / 1024:.1f} GB sitting {f.age_days:.0f} days — do you still need this?"))

        elif f.category == "image" and f.size < 2 * 1024 * 1024 and f.age_days >= 180:
            decisions.append(Decision(f, ACT_ARCHIVE, "old small image — museum material, keep out of sight"))

        elif fresh:
            decisions.append(Decision(f, ACT_KEEP, "hot off the wire (today-ish)"))

        elif f.category in ("document", "sheet", "slides", "code", "ebook", "audio"):
            decisions.append(Decision(f, ACT_KEEP, "work material — lives, breathes"))

        elif f.size < 10 * 1024 * 1024:
            decisions.append(Decision(f, ACT_KEEP, "small enough to not matter; harmless"))

        else:
            decisions.append(Decision(f, ACT_REVIEW, f"mystery crate {f.age_days:.0f}d old — you open it"))

    plan = Plan(decisions=decisions, intro=persona.intro_line(), kept=None)
    plan.verdict = persona.verdict_line(
        trash_n=len(plan.group(ACT_TRASH)),
        freed=plan.bytes_moved(ACT_TRASH),
        keep_n=len(plan.group(ACT_KEEP)),
    )
    return plan
