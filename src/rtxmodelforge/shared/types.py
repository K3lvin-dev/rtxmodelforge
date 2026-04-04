from __future__ import annotations
from enum import Enum
from dataclasses import dataclass

class StageStatus(str, Enum):
    PENDING = "—"
    RUNNING = "⠸"
    DONE = "✔"
    FAILED = "✘"

@dataclass
class StageResult:
    label: str
    status: StageStatus = StageStatus.PENDING
    duration_s: float = 0.0

    @property
    def duration_display(self) -> str:
        minutes, seconds = divmod(int(self.duration_s), 60)
        return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
