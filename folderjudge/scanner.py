"""File discovery + duplicate fingerprinting. No dirs are ever touched — files only."""
from __future__ import annotations

import os
import stat as statmod
import time
from dataclasses import dataclass
from pathlib import Path

from .categorize import JUNK, categorize, emoji_for
from .utils import partial_hash

# Files bigger than this are exempt from duplicate matching (cost control).
SIG_MAX = 256 * 1024 * 1024


@dataclass
class FileInfo:
    path: Path
    name: str
    ext: str
    category: str
    size: int
    age_days: float
    mtime: float
    hidden: bool
    sig: str | None = None

    @property
    def icon(self) -> str:
        return emoji_for(self.category)


def default_target() -> Path:
    from .utils import default_target as _dt
    got = _dt()
    if got:
        return got
    raise SystemExit("no Downloads folder found — pass one: folderjudge <path>")


def scan(target: Path, deep: bool = False, include_hidden: bool = False) -> list[FileInfo]:
    base = Path(target).expanduser()
    now = time.time()
    out: list[FileInfo] = []

    iterator = base.rglob("*") if deep else base.iterdir()
    for p in sorted(iterator):
        try:
            st = os.lstat(p)  # never follow symlinks
        except OSError:
            continue
        if statmod.S_ISLNK(st.st_mode) or not statmod.S_ISREG(st.st_mode):
            continue

        win_hidden = bool(getattr(st, "st_file_attributes", 0) & 0x2)  # FILE_ATTRIBUTE_HIDDEN
        hidden = p.name.startswith(".") or win_hidden
        if hidden and not include_hidden:
            continue

        ext = p.suffix.lower()
        cat = categorize(ext)
        age = max(0.0, (now - st.st_mtime) / 86400)

        sig = None
        if cat != JUNK and st.st_size <= SIG_MAX:
            sig = partial_hash(p, st.st_size)

        out.append(FileInfo(
            path=p.resolve(), name=p.name, ext=ext, category=cat,
            size=st.st_size, age_days=age, mtime=st.st_mtime,
            hidden=hidden, sig=sig,
        ))
    return out
