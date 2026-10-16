"""Local AI judge via Ollama. Stdlib only; graceful to absence."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .plan import ACTIONS, Plan  # noqa: F401 (ACTIONS re-exported for cli)
from .persona import Persona
from .scanner import FileInfo
from .utils import human

BASE = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
CAP = 300  # max files sent to the model in one shot

PREFER = ("llama3", "qwen", "gemma", "mistral", "phi", "tinyllama", "moondream")


def ping(timeout: float = 1.5) -> dict | None:
    """Returns {'models': [...]} when Ollama is alive, else None."""
    try:
        with urllib.request.urlopen(f"{BASE}/api/tags", timeout=timeout) as r:
            data = json.load(r)
        names = [m["name"] for m in data.get("models", [])]
        return {"models": names}
    except Exception:
        return None


def pick_model(models: list[str]) -> str | None:
    if not models:
        return None
    text_only = [m for m in models if "moondream" not in m] or models
    for want in PREFER:
        for m in text_only:
            if want in m.lower():
                return m
    return text_only[0]


def _listing(files: list[FileInfo]) -> tuple[str, int]:
    rows = []
    n = min(len(files), CAP)
    for i in range(n):
        f = files[i]
        rows.append(f"{i}|{f.name}|{f.category}|{human(f.size)}|{f.age_days:.0f}d")
    return "\n".join(rows), n


def analyze(files: list[FileInfo], persona: Persona, model: str,
            timeout: float = 240.0) -> dict | None:
    """Returns {'actions': {idx: (action, reason)}, 'intro', 'verdict', 'meta'}
    or None on any failure (caller falls back to heuristics)."""
    listing, n = _listing(files)
    system = (
        persona.system
        + "\n\nReturn ONLY JSON, no prose, shaped exactly like:\n"
        '{"intro": "one spicy sentence addressing the owner", '
        '"verdict": "one closing sentence after judging", '
        '"files": [{"n": <line number>, "action": "trash|keep|archive|review", '
        '"reason": "max 10 words, no law jargon"}]}\n\n'
        "Rules:\n"
        f"- Judge every line n=0..{n - 1}, exactly once each.\n"
        "- trash: junk parts, true duplicates, installers nobody needs again, obv dead weight.\n"
        "- archive: media/worth-keeping-but-out-of-sight (old photos, classics).\n"
        "- keep: explicit work material and anything recent.\n"
        "- review: you truly cannot tell (mystery bins, giant files, half-finished ideas).\n"
        "- When in doubt: review, not trash. You judge from name+size+age+category only."
    )

    body = json.dumps({
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2, "num_ctx": 4096},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "Line list (n|name|category|size|age):\n" + listing},
        ],
    }).encode()

    req = urllib.request.Request(
        f"{BASE}/api/chat", data=body, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            content = json.load(r)["message"]["content"]
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, KeyError, json.JSONDecodeError):
        return None

    return _parse(content, n, model)


def _parse(content: str, n: int, model: str) -> dict | None:
    s, e = content.find("{"), content.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        blob = json.loads(content[s:e + 1])
    except json.JSONDecodeError:
        return None

    actions: dict[int, tuple[str, str]] = {}
    for item in blob.get("files", []):
        try:
            idx = int(item["n"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= idx < n):
            continue
        act = str(item.get("action", "")).lower().strip()
        if act not in ACTIONS:
            continue
        reason = str(item.get("reason", "")).strip()[:80]
        actions[idx] = (act, reason)

    if len(actions) < max(1, n // 3):   # model must judge most files to count
        if not actions and not (blob.get("intro") and blob.get("verdict")):
            return None

    intro = str(blob.get("intro", "")).strip() or None
    verdict = str(blob.get("verdict", "")).strip() or None
    return {
        "actions": actions,
        "intro": intro,
        "verdict": verdict,
        "meta": {"via": "Ollama", "model": model},
    }
