"""The plan: decisions per file + merge rules that cap what the model may do."""
from __future__ import annotations

from dataclasses import dataclass, field
from .scanner import FileInfo

ACT_KEEP = "keep"
ACT_TRASH = "trash"
ACT_ARCHIVE = "archive"
ACT_REVIEW = "review"
ACTIONS = {ACT_KEEP, ACT_TRASH, ACT_ARCHIVE, ACT_REVIEW}


@dataclass
class Decision:
    info: FileInfo
    action: str
    reason: str


@dataclass
class Plan:
    decisions: list[Decision] = field(default_factory=list)
    intro: str | None = None
    verdict: str | None = None
    kept: str | None = None
    ai_meta: dict | None = None

    def group(self, action: str) -> list[Decision]:
        return [d for d in self.decisions if d.action == action]

    def counts(self) -> dict[str, int]:
        out = {a: 0 for a in sorted(ACTIONS)}
        for d in self.decisions:
            out[d.action] += 1
        return out

    def bytes_moved(self, *actions: str) -> int:
        return sum(d.info.size for d in self.decisions if d.action in actions)

    def has_removals(self) -> bool:
        return bool(self.group(ACT_TRASH) or self.group(ACT_ARCHIVE))


def merge_ai(base: Plan, ai: dict) -> Plan:
    """AI overrides the heuristic verdicts, with guardrails the model itself
    cannot talk its way past — big or brand-new files never go to the bin on
    a hunch alone."""
    acts = ai.get("actions") or {}
    decisions: list[Decision] = []
    for i, d in enumerate(base.decisions):
        a = acts.get(i)
        if not a:
            decisions.append(d)
            continue
        act, reason = a
        if act == ACT_TRASH and d.action != ACT_TRASH:
            info = d.info
            big = info.size > 200 * 1024 * 1024
            fresh = info.age_days < 7
            if (big and fresh) or (big and info.category not in ("installer", "junk", "disc")):
                act = ACT_REVIEW  # escalate, don't nuke
        decisions.append(Decision(d.info, act, reason or d.reason))
    return Plan(
        decisions=decisions,
        intro=ai.get("intro") or base.intro,
        verdict=ai.get("verdict") or base.verdict,
        ai_meta=ai.get("meta"),
    )
