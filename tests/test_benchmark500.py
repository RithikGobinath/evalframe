import asyncio
import json
from collections import Counter
from pathlib import Path

from evalframe.cases import load_cases
from evalframe.providers import ProviderResponse
from evalframe.runner import run_evaluation
from evalframe.scoring import score_case


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "benchmark500.jsonl"
PROMPTS = ROOT / "prompts" / "baseline.toml"


def test_benchmark500_has_balanced_cases_and_valid_reference_answers():
    cases, _ = load_cases(DATASET)
    raw = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 500
    assert Counter(case.task_type for case in cases) == {
        "classification": 100,
        "extraction": 100,
        "qa": 100,
        "summarization": 100,
        "instruction_following": 100,
    }
    assert len({case.input for case in cases}) == 500
    assert all(case.input.isascii() for case in cases)
    assert all(score_case(case, item["reference_output"]).value == 1.0 for case, item in zip(cases, raw))


def test_benchmark500_runner_accounts_for_every_case(tmp_path):
    raw = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]
    references = {item["input"]: item["reference_output"] for item in raw}

    class ReferenceProvider:
        calls = 0

        async def generate(self, model, system, user, max_output_tokens):
            self.calls += 1
            return ProviderResponse(references[user], 20, 10, None, "stop")

        async def close(self):
            pass

    provider = ReferenceProvider()
    _, summaries = asyncio.run(run_evaluation(
        dataset=DATASET,
        prompt_file=PROMPTS,
        model_specs=["openrouter:reference"],
        output_root=tmp_path,
        run_id="offline-500",
        concurrency=5,
        log_mlflow=False,
        provider_factory=lambda _: provider,
    ))
    summary = summaries["openrouter:reference"]
    assert provider.calls == 500
    assert summary["cases"] == summary["completed"] == 500
    assert summary["errors"] == 0
    assert summary["mean_score"] == 1.0
