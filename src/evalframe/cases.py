"""Versioned evaluation case validation and loading."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TASK_TYPES = frozenset(
    {"classification", "extraction", "qa", "summarization", "instruction_following"}
)


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    task_type: str
    input: str
    expected: Any
    tags: tuple[str, ...] = ()


def _validate_expected(task_type: str, expected: Any, location: str) -> None:
    if task_type in {"classification", "qa"}:
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(f"{location}: expected must be a nonempty string")
    elif task_type == "extraction":
        if not isinstance(expected, dict) or not expected:
            raise ValueError(f"{location}: expected must be a nonempty object")
    elif task_type == "summarization":
        if not isinstance(expected, dict):
            raise ValueError(f"{location}: expected must be an object")
        required = expected.get("required_phrases")
        forbidden = expected.get("forbidden_phrases", [])
        if not isinstance(required, list) or not required or not all(
            isinstance(item, str) and item.strip() for item in required
        ):
            raise ValueError(f"{location}: required_phrases must be nonempty strings")
        if not isinstance(forbidden, list) or not all(isinstance(item, str) for item in forbidden):
            raise ValueError(f"{location}: forbidden_phrases must be strings")
    else:
        if not isinstance(expected, dict) or not expected:
            raise ValueError(f"{location}: expected must contain constraints")
        allowed = {"contains_all", "contains_none", "max_words", "valid_json"}
        if unknown := set(expected) - allowed:
            raise ValueError(f"{location}: unsupported constraints: {sorted(unknown)}")
        for name in ("contains_all", "contains_none"):
            if name in expected and (
                not isinstance(expected[name], list)
                or not all(isinstance(item, str) and item for item in expected[name])
            ):
                raise ValueError(f"{location}: {name} must be a list of nonempty strings")
        if "max_words" in expected and (
            isinstance(expected["max_words"], bool)
            or not isinstance(expected["max_words"], int)
            or expected["max_words"] < 1
        ):
            raise ValueError(f"{location}: max_words must be a positive integer")
        if "valid_json" in expected and not isinstance(expected["valid_json"], bool):
            raise ValueError(f"{location}: valid_json must be a boolean")


def load_cases(path: Path) -> tuple[list[EvalCase], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    cases: list[EvalCase] = []
    seen: set[str] = set()
    for line_number, line in enumerate(raw.decode("utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        location = f"{path}:{line_number}"
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{location}: invalid JSON: {exc.msg}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{location}: case must be an object")
        case_id = item.get("case_id")
        task_type = item.get("task_type")
        prompt_input = item.get("input")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"{location}: case_id must be a nonempty string")
        if case_id in seen:
            raise ValueError(f"{location}: duplicate case_id {case_id!r}")
        if task_type not in TASK_TYPES:
            raise ValueError(f"{location}: unsupported task_type {task_type!r}")
        if not isinstance(prompt_input, str) or not prompt_input.strip():
            raise ValueError(f"{location}: input must be a nonempty string")
        expected = item.get("expected")
        _validate_expected(task_type, expected, location)
        tags = item.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"{location}: tags must be a list of strings")
        seen.add(case_id)
        cases.append(EvalCase(case_id, task_type, prompt_input, expected, tuple(tags)))
    if not cases:
        raise ValueError(f"{path}: dataset is empty")
    return cases, digest
