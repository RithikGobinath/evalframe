"""Transparent deterministic pilot scorers.

The summary scorer checks reference facts as phrases. It is intentionally a
limited proxy for quality; the report must not call it a human quality score.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .cases import EvalCase


@dataclass(frozen=True)
class Score:
    value: float
    details: dict[str, Any]


def _normalize(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def _words(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())


def score_case(case: EvalCase, output: str) -> Score:
    expected = case.expected
    if case.task_type == "classification":
        passed = _normalize(output) == _normalize(expected)
        return Score(float(passed), {"exact_match": passed})

    if case.task_type == "extraction":
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return Score(0.0, {"valid_json": False, "correct_fields": 0})
        if not isinstance(parsed, dict):
            return Score(0.0, {"valid_json": True, "correct_fields": 0})
        correct = sum(
            key in parsed and _normalize(parsed[key]) == _normalize(value)
            for key, value in expected.items()
        )
        denominator = max(len(expected), len(parsed))
        return Score(correct / denominator, {
            "valid_json": True,
            "correct_fields": correct,
            "expected_fields": len(expected),
            "output_fields": len(parsed),
        })

    if case.task_type == "qa":
        actual_words = _words(output)
        expected_words = _words(expected)
        exact = actual_words == expected_words
        if not actual_words:
            return Score(0.0, {"exact_match": False, "token_f1": 0.0})
        from collections import Counter

        overlap = sum((Counter(actual_words) & Counter(expected_words)).values())
        precision = overlap / len(actual_words)
        recall = overlap / len(expected_words)
        f1 = 2 * precision * recall / (precision + recall) if overlap else 0.0
        return Score(f1, {"exact_match": exact, "token_f1": f1})

    if case.task_type == "summarization":
        normalized = _normalize(output)
        required = expected["required_phrases"]
        forbidden = expected.get("forbidden_phrases", [])
        covered = sum(_normalize(phrase) in normalized for phrase in required)
        violations = [phrase for phrase in forbidden if _normalize(phrase) in normalized]
        value = covered / len(required) if not violations else 0.0
        return Score(value, {
            "required_covered": covered,
            "required_total": len(required),
            "forbidden_violations": violations,
            "method": "phrase_coverage_proxy",
        })

    checks: dict[str, bool] = {}
    normalized = _normalize(output)
    if "contains_all" in expected:
        checks["contains_all"] = all(
            _normalize(phrase) in normalized for phrase in expected["contains_all"]
        )
    if "contains_none" in expected:
        checks["contains_none"] = all(
            _normalize(phrase) not in normalized for phrase in expected["contains_none"]
        )
    if "max_words" in expected:
        checks["max_words"] = len(output.split()) <= expected["max_words"]
    if "valid_json" in expected:
        try:
            json.loads(output)
            is_json = True
        except json.JSONDecodeError:
            is_json = False
        checks["valid_json"] = is_json == expected["valid_json"]
    return Score(float(all(checks.values())), checks)
