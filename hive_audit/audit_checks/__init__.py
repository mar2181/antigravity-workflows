"""Audit check modules. Each module exports a `run() -> Finding` function."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal

Severity = Literal["info", "warn", "error"]


@dataclass
class Finding:
    id: str
    severity: Severity
    problem: str
    root_cause_guess: str
    proposed_fix: str
    first_seen: str

    @classmethod
    def now(cls, **kwargs) -> "Finding":
        kwargs.setdefault("first_seen", datetime.now().isoformat(timespec="seconds"))
        return cls(**kwargs)

    def to_dict(self) -> dict:
        return asdict(self)
