import json

import pytest

from evalframe.cases import EvalCase, load_cases
from evalframe.scoring import score_case


@pytest.mark.parametrize(
    ("case", "output", "expected"),
    [
        (EvalCase("1", "classification", "x", "billing"), " Billing ", 1.0),
        (EvalCase("2", "extraction", "x", {"a": "one", "b": 2}), '{"a":"one","b":2}', 1.0),
        (EvalCase("3", "extraction", "x", {"a": "one"}), "not json", 0.0),
        (EvalCase("4", "qa", "x", "Paris"), "The answer is Paris", 0.4),
        (EvalCase("5", "summarization", "x", {"required_phrases": ["12%"], "forbidden_phrases": ["doubled"]}), "Sales rose 12%", 1.0),
        (EvalCase("6", "instruction_following", "x", {"contains_all": ["blue"], "contains_none": ["red"], "max_words": 2}), "blue sky", 1.0),
    ],
)
def test_scoring(case, output, expected):
    assert score_case(case, output).value == pytest.approx(expected)


def test_duplicate_ids_are_rejected(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    case = {"case_id": "same", "task_type": "classification", "input": "x", "expected": "y"}
    dataset.write_text(json.dumps(case) + "\n" + json.dumps(case) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate case_id"):
        load_cases(dataset)
