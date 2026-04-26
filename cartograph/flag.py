from __future__ import annotations

from dataclasses import dataclass

STALE = "STALE"
UNTRACKED = "UNTRACKED"
GAP = "GAP"
STALE_REF = "STALE_REF"
ALREADY_DONE = "ALREADY_DONE"
BROKEN_DEP = "BROKEN_DEP"
UNDECLARED = "UNDECLARED"


@dataclass
class Flag:
    id: str
    channel: int
    type: str
    source: str
    detail: str
    resolved: bool = False
