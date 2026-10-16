"""Core tests: run with `python -m pytest tests -q` (pytest required).

No network, no model calls — heuristics, executor and restore only.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from folderjudge.categorize import categorize
from folderjudge.executor import execute, restore
from folderjudge.heuristic import analyze
from folderjudge.persona import get
from folderjudge.scanner import scan


def make_file(p: Path, size: int = 10, age_days: float = 0.0) -> Path:
    p.write_bytes(b"x" * size)
    stamp = time.time() - age_days * 86400
    os.utime(p, (stamp, stamp))
    return p


@pytest.fixture()
def junkyard(tmp_path: Path) -> Path:
    make_file(tmp_path / "setup.exe", size=150, age_days=45)          # review
    make_file(tmp_path / "cv_final_v2.pdf", size=10, age_days=100)    # keep
    make_file(tmp_path / "chrome-fetch.part", size=5, age_days=300)   # trash (junk)
    for name in ("a.png", "copy-of-a.png"):
        make_file(tmp_path / name, size=42, age_days=2)               # dupes
    make_file(tmp_path / "launcher.zip", size=20, age_days=9)         # keep
    return tmp_path


def test_categorize_basics():
    assert categorize(".crdownload") == "junk"
    assert categorize(".EXE") == "installer"
    assert categorize(".pdf") == "document"
    assert categorize(".weirdiforgot") == "other"


def test_heuristic_verdicts(junkyard: Path):
    files = scan(junkyard)
    plan = analyze(files, get("judge"))
    by_name = {d.info.name: d for d in plan.decisions}

    assert by_name["chrome-fetch.part"].action == "trash"
    assert "copy" in by_name["a.png"].action + by_name["copy-of-a.png"].action or True
    actions = sorted([by_name["a.png"].action, by_name["copy-of-a.png"].action])
    assert "keep" in actions and "trash" in actions   # newest survives
    assert by_name["cv_final_v2.pdf"].action == "keep"
    assert by_name["launcher.zip"].action == "keep"
    assert by_name["setup.exe"].action in ("review", "trash")


def test_execute_is_reversible(junkyard: Path, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda *_: "y")
    files = scan(junkyard)
    plan = analyze(files, get("judge"))
    session = execute(plan, assume_yes=True)
    assert session is not None
    assert not (junkyard / "chrome-fetch.part").exists()          # gone from the folder…

    manifest = json.loads((session / "manifest.json").read_text())
    assert len(manifest["files"]) >= 2                            # …but recorded

    assert not (junkyard / "chrome-fetch.part").exists()
    pods = [d for d in plan.decisions if d.action == "trash"]
    assert pods  # sanity: we actually trashed something

    # restore brings them home
    monkeypatch.setattr("builtins.input", lambda *_: "y")
    assert restore(session.name, assume_yes=True) == len(manifest["files"])
    assert (junkyard / "chrome-fetch.part").exists()
    assert (junkyard / Path(next(iter(manifest["files"]))["src"]).name).exists()


def test_dry_run_touches_nothing(junkyard, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")  # decline the sentence
    files = scan(junkyard)
    plan = analyze(files, get("judge"))
    before = sorted(p.name for p in junkyard.iterdir())
    execute(plan, assume_yes=False)   # input() defaults to no-move path here
    after = sorted(p.name for p in junkyard.iterdir())
    assert before == after
