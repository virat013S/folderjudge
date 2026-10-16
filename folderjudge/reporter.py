"""Rendering: terminal color-print + markdown report."""
from __future__ import annotations

import webbrowser as _wb
from pathlib import Path

from . import __version__
from .utils import c, human, paths, paint

ACTION_STYLE = {
    "trash": ("31", "TRASH"),
    "archive": ("33", "ARCHIVE"),
    "review": ("36", "REVIEW"),
    "keep": ("32", "KEEP"),
}

DETAIL_LIMIT = 40


def render(plan, target: Path, persona, *, deep: bool, dry: bool, ai_note: str) -> None:
    counts = plan.counts()
    freed = plan.bytes_moved("trash")
    total_size = sum(d.info.size for d in plan.decisions)

    print()
    print(paint(f"⚖️  FOLDERJUDGE  ·  a court for your junk", "1"))
    print(f"  folder   {target}{'' if not deep else '  (deep scan)'}")
    print(f"  files    {len(plan.decisions)} · {human(total_size)}")
    print(f"  judge    {persona.label}{ai_note}")
    print()
    if plan.intro:
        print(c("2", f"  “{plan.intro}”"))
        print()

    print(paint(f"  {'action':<10}{'files':>6}   {'size':>10}", "1"))
    for act in ("trash", "archive", "review", "keep"):
        docs = plan.group(act)
        code, label = ACTION_STYLE[act]
        size = plan.bytes_moved(act)
        print(f"  {c(code, f'{label:<10}')}{len(docs):>6}   {c(code, human(size) if size else '—'):>10}")
    print()

    for act in ("trash", "archive", "review"):
        doc = plan.group(act)
        if not doc:
            continue
        code, label = ACTION_STYLE[act]
        print(paint(f"── {label} {'─' * 46}", code))
        doc_sorted = sorted(doc, key=lambda d: -d.info.size)
        for d in doc_sorted[:DETAIL_LIMIT]:
            f = d.info
            print(f"  {f.icon} {c('1', f.name)}"
                  f"{c('2', f' · {human(f.size)} · {f.age_days:.0f}d')}")
            print(f"    {c('2', d.reason)}")
        if len(doc_sorted) > DETAIL_LIMIT:
            print(c("2", f"    …and {len(doc_sorted) - DETAIL_LIMIT} more like this"))
        print()

    if plan.verdict:
        print(c("1", f"  ⚖️  {plan.verdict}"))
    print()

    if plan.has_removals():
        print(c("2", f"  trash lives at {paths()['trash']} — undo anytime: folderjudge restore"))
    if dry:
        print(paint("  DRY-RUN — nothing was moved. run without --dry-run to execute.", "33"))


def to_markdown(plan, target: Path, persona, *, ai_note: str, dry: bool,
                count_detail: bool = True) -> str:
    L: list[str] = []
    counts = plan.counts()
    total_size = sum(d.info.size for d in plan.decisions)
    L.append(f"# {__import__('folderjudge').APP} verdict")
    L.append("")
    L.append(f"- **folder**: `{target}`")
    L.append(f"- **files**: {len(plan.decisions)} ({human(total_size)})")
    L.append(f"- **judge**: {persona.label}{ai_note}")
    if plan.intro:
        L.append(f"> {plan.intro}")
    L.append("")
    L.append("| action | files | size |")
    L.append("|---|---|---|")
    for act in ("trash", "archive", "review", "keep"):
        n = counts[act]
        sz = plan.bytes_moved(act)
        L.append(f"| **{act}** | {n} | {human(sz) if sz else '—'} |")
    L.append("")
    if plan.intro:
        L.append(f"*“{plan.intro}”*")
        L.append("")
    for act in ("archive", "trash", "review"):
        docs = plan.group(act)
        if not docs:
            continue
        L.append(f"## {act}")
        L.append("")
        for d in sorted(docs, key=lambda x: -x.info.size):
            f = d.info
            L.append(f"- `{f.name}` — {human(f.size)}, {f.age_days:.0f}d old · *{d.reason}*")
        L.append("")
    if plan.verdict:
        L.append(f"**Verdict:** {plan.verdict}")
    L.append("")
    if dry:
        L.append("*dry-run: nothing was moved*")
    return "\n".join(L) + "\n"


def save(plan, target: Path, persona, *, ai_note: str, dry: bool) -> Path:
    import time
    rep_dir = paths()["reports"]
    rep_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H%M%S")
    p = rep_dir / f"{stamp}{'-dry' if dry else ''}-{persona.id}.md"
    p.write_text(to_markdown(plan, target, persona, ai_note=ai_note, dry=dry), encoding="utf-8")
    return p


def print_last_report() -> bool:
    reports = sorted(paths()["reports"].glob("*.md"))
    if not reports:
        print("  no reports yet — run `folderjudge` first.")
        return False
    p = reports[-1]
    print_path(p)
    return True


def open_report() -> bool:
    reports = sorted(paths()["reports"].glob("*.md"))
    if not reports:
        print("  no reports yet — run `folderjudge` first.")
        return False
    print(f"opening {reports[-1]}")
    try:
        _wb.open(str(reports[-1]))
    except Exception:
        print("(no browser on this box — the file is right here though)")
    return True


def print_path(p: Path) -> None:
    print(p)
