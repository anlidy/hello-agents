from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Skill(Protocol):
    name: str

    def prompt(self) -> str:
        ...


@dataclass(slots=True)
class StaticSkill:
    name: str
    instructions: str

    def prompt(self) -> str:
        return self.instructions
