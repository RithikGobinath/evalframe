"""Prompt loading and rendering."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .cases import TASK_TYPES, EvalCase


@dataclass(frozen=True)
class PromptSet:
    version: str
    digest: str
    systems: dict[str, str]

    def render(self, case: EvalCase) -> tuple[str, str]:
        return self.systems[case.task_type], case.input


def load_prompts(path: Path) -> PromptSet:
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode("utf-8-sig"))
    version = data.get("version")
    tasks = data.get("tasks")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"{path}: version must be a nonempty string")
    if not isinstance(tasks, dict):
        raise ValueError(f"{path}: missing [tasks] section")
    systems = {}
    for task_type in TASK_TYPES:
        config = tasks.get(task_type)
        system = config.get("system") if isinstance(config, dict) else None
        if not isinstance(system, str) or not system.strip():
            raise ValueError(f"{path}: missing system prompt for {task_type}")
        systems[task_type] = system
    return PromptSet(version, hashlib.sha256(raw).hexdigest(), systems)
