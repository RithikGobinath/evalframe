"""Public benchmark schema and scoring checks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from evalframe.cases import EvalCase, load_cases
from evalframe.scoring import score_case


ROOT = Path(__file__).resolve().parents[1]


def test_public_dataset_is_sourced_and_balanced():
    path = ROOT / "data" / "public500-v1.jsonl"
    cases, digest = load_cases(path)
    manifest = json.loads((ROOT / "data" / "public500-v1.sources.json").read_text(encoding="utf-8"))
    raw = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert len(cases) == 500
    assert Counter(case.task_type for case in cases) == {task: 100 for task in (
        "classification", "extraction", "qa", "summarization", "instruction_following"
    )}
    assert manifest["dataset_sha256"] == digest
    assert all(Counter(case.task_type for case in cases[start:start + 5]) == {
        task: 1 for task in ("classification", "extraction", "qa", "summarization", "instruction_following")
    } for start in range(0, 500, 5))
    assert all(row["source_id"] and row["source_revision"] and row["source_license"] for row in raw)
    assert {row["source"] for row in raw} == {
        "PolyAI BANKING77 test split", "Databricks Dolly 15k", "Google IFEval"
    }


def test_public_reference_metrics():
    extraction = EvalCase("x", "extraction", "request", {"reference_text": "Ava ordered two folders"})
    summary = EvalCase("s", "summarization", "request", {"reference_summary": "A B C"})
    assert score_case(extraction, "Ava ordered").value == pytest.approx(2 / 3)
    assert score_case(summary, "A C").value == pytest.approx(0.8)
    assert score_case(summary, "unrelated").value == 0.0


def test_official_ifeval_strict_checker_is_used():
    cases, _ = load_cases(ROOT / "data" / "public500-v1.jsonl")
    case = next(case for case in cases if case.task_type == "instruction_following"
                and case.expected["ifeval"]["instruction_id_list"] == ["punctuation:no_comma"])
    passed = score_case(case, "Hello world")
    failed = score_case(case, "Hello, world")
    assert passed.value == 1.0
    assert failed.value == 0.0
    assert passed.details["method"] == "ifeval_strict"


@pytest.mark.parametrize("task,expected", [
    ("extraction", {"reference_text": ""}),
    ("summarization", {"reference_summary": ""}),
    ("instruction_following", {"ifeval": {"key": 1, "instruction_id_list": ["punctuation:no_comma"], "kwargs": []}}),
])
def test_invalid_public_expected_is_rejected(tmp_path, task, expected):
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps({"case_id": "x", "task_type": task, "input": "test", "expected": expected}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_cases(path)
