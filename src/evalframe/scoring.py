"""Transparent deterministic pilot scorers.

The summary scorer checks reference facts as phrases. It is intentionally a
limited proxy for quality; the report must not call it a human quality score.
"""

from __future__ import annotations

import json
import re
from collections import Counter
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


def _token_f1(actual: str, reference: str) -> float:
    actual_words = _words(actual)
    reference_words = _words(reference)
    if not actual_words or not reference_words:
        return 0.0
    overlap = sum((Counter(actual_words) & Counter(reference_words)).values())
    if not overlap:
        return 0.0
    precision = overlap / len(actual_words)
    recall = overlap / len(reference_words)
    return 2 * precision * recall / (precision + recall)


def _rouge_l_f1(actual: str, reference: str) -> float:
    actual_words = _words(actual)
    reference_words = _words(reference)
    if not actual_words or not reference_words:
        return 0.0
    previous = [0] * (len(reference_words) + 1)
    for word in actual_words:
        current = [0]
        for index, reference_word in enumerate(reference_words, 1):
            current.append(previous[index - 1] + 1 if word == reference_word else max(previous[index], current[-1]))
        previous = current
    longest = previous[-1]
    precision = longest / len(actual_words)
    recall = longest / len(reference_words)
    return 2 * precision * recall / (precision + recall) if longest else 0.0


def score_case(case: EvalCase, output: str) -> Score:
    expected = case.expected
    if case.task_type == "classification":
        passed = _normalize(output) == _normalize(expected)
        return Score(float(passed), {"exact_match": passed})

    if case.task_type == "extraction":
        if "reference_text" in expected:
            value = _token_f1(output, expected["reference_text"])
            return Score(value, {"reference_token_f1": value, "method": "reference_token_f1"})
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
        f1 = _token_f1(output, expected)
        return Score(f1, {"exact_match": exact, "token_f1": f1})

    if case.task_type == "summarization":
        if "reference_summary" in expected:
            value = _rouge_l_f1(output, expected["reference_summary"])
            return Score(value, {"rouge_l_f1": value, "method": "reference_rouge_l_f1"})
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

    if "ifeval" in expected:
        from instruction_following_eval.evaluation_lib import InputExample, test_instruction_following_strict

        source = expected["ifeval"]
        example = InputExample(
            key=source["key"],
            instruction_id_list=source["instruction_id_list"],
            prompt=case.input,
            kwargs=source["kwargs"],
        )
        result = test_instruction_following_strict(example, {case.input: output})
        return Score(float(result.follow_all_instructions), {
            "method": "ifeval_strict",
            "instruction_ids": result.instruction_id_list,
            "instruction_checks": result.follow_instruction_list,
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
