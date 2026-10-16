"""Small shared helpers: colors, human units, app data dirs, safe moves."""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from . import APP

# ---------------- colors ----------------

_ENABLE = None

RESET = "0"
BOLD = "1"
DIM = "2"
RED = "31"
GREEN = "32"
YELLOW = "33"
MAGENTA = "35"
CYAN = "36"


def _enable_windows_vt() -> None:
    if os.name == "nt":
        try:
            os.system("")  # enables ANSI in classic Windows consoles
        except Exception:
            pass


def colors_on() -> bool:
    global _ENABLE
    if _ENABLE is None:
        _enable_windows_vt()
        if os.environ.get("NO_COLOR"):
            _ENABLE = False
        elif not sys.stdout.isatty():
            _ENABLE = False
        elif os.environ.get("TERM") == "dumb":
            _ENABLE = False
        else:
            _ENABLE = True
    return _ENABLE


def c(code: str, text: object) -> str:
    s = str(text)
    return f"\x1b[{code}m{s}\x1b[{RESET}m" if colors_on() else s


def paint(text: object, *codes: str) -> str:
    s = str(text)
    if not colors_on() or not codes:
        return s
    return f"\x1b[{'m'.join(codes)}m{s}\x1b[{RESET}m"


# ---------------- dates / units ----------------

import time  # noqa: E402


def clock_st() -> str:
    return time.strftime("%Y-%m-%dT%H%M%S")


def human(n: int) -> str:
    """1234567 -> '1.2 MB'"""
    n = int(n)
    if n < 1024:
        return f"{n} B"
    x = float(n)
    for unit in ("KB", "MB", "GB", "TB", "PB"):
        x /= 1024.0
        if x < 1024 or unit == "PB":
            return f"{x:.1f} {unit}"
    return f"{n} B"


# ---------------- app dirs (per-OS, stdlib only) ----------------

def data_root() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP


def paths() -> dict:
    root = data_root()
    return {
        "data": root,
        "trash": root / "trash",
        "reports": root / "reports",
    }


def ensure_dirs() -> None:
    for key in ("trash", "reports"):
        p = paths()[key]
        p.mkdir(parents=True, exist_ok=True)


# ---------------- hashing / moves ----------------

_HEAD = 131072  # 128 KB


def partial_hash(path: Path, size: int) -> str | None:
    """Fast fingerprint: head + (tail if big enough) + size. Collisions ~ never."""
    try:
        h = hashlib.md5()  # fine — integrity heuristic, not crypto
        h.update(b"fj:%d" % size)
        with open(path, "rb") as f:
            h.update(f.read(_HEAD))
            if size > 2 * _HEAD:
                f.seek(-_HEAD, 2)
                h.update(f.read(_HEAD))
        return h.hexdigest()
    except OSError:
        return None


_BAD_CHARS = '<>:"/\\|?*'


def stored_name(rel: str) -> str:
    """Flatten a relative path into one filesystem-safe file name."""
    flat = rel.replace("/", "__").replace("\\", "__").replace(":", "_")
    out = "".join(ch if ch not in _BAD_CHARS and ord(ch) >= 32 else "_" for ch in flat)
    if len(out) > 180:
        half = (180 - 15) // 2
        out = out[:half] + "__…snip…" + out[-half:]
    return out


def unique_path(dst: Path) -> Path:
    if not dst.exists():
        return dst
    i = 2
    while True:
        cand = dst.with_name(f"{dst.stem} ({i}){dst.suffix}")
        if not cand.exists():
            return cand
        i += 1


# ---------------- default folder ----------------

def default_target() -> Path | None:
    home = Path.home()
    candidates = [
        home / "Downloads",
        home / "OneDrive" / "Downloads",   # Windows with OneDrive sync
        home / "Download",
    ]
    for cand in candidates:
        if cand.is_dir():
            return cand
    return None
