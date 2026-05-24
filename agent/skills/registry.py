from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from agent.skills.base import Skill


@dataclass(slots=True)
class SkillRegistry:
    skills: Iterable[Skill] = field(default_factory=tuple)
    _skills_by_name: dict[str, Skill] = field(init=False)

    def __post_init__(self) -> None:
        self._skills_by_name = {skill.name: skill for skill in self.skills}

    def get(self, name: str) -> Skill | None:
        return self._skills_by_name.get(name)

    def prompts_for(self, active_skill_names: list[str]) -> list[str]:
        prompts: list[str] = []
        for name in active_skill_names:
            skill = self.get(name)
            if skill is not None:
                prompts.append(skill.prompt())
        return prompts
