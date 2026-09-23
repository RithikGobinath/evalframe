import asyncio
import json

import pytest

from evalframe.providers import ProviderResponse
from evalframe.runner import run_evaluation


class FakeProvider:
    calls = 0

    async def generate(self, model, system, user, max_output_tokens):
        self.calls += 1
        return ProviderResponse("billing", 5, 1, "fake-request", "completed")

    async def close(self):
        pass


def test_run_resumes_without_repeating_completed_cases(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps({"case_id": "a", "task_type": "classification", "input": "Ticket A", "expected": "billing"}) + "\n"
        + json.dumps({"case_id": "b", "task_type": "classification", "input": "Ticket B", "expected": "billing"}) + "\n",
        encoding="utf-8",
    )
    prompt = tmp_path / "prompts.toml"
    prompt.write_text(
        'version = "v1"\n' + "\n".join(
            f'[tasks.{task}]\nsystem = "Answer briefly"'
            for task in ("classification", "extraction", "qa", "summarization", "instruction_following")
        ),
        encoding="utf-8",
    )
    fake = FakeProvider()
    kwargs = dict(
        dataset=dataset,
        prompt_file=prompt,
        model_specs=["openai:fake-model"],
        output_root=tmp_path / "runs",
        run_id="test-run",
        provider_factory=lambda _: fake,
        log_mlflow=False,
    )
    first_dir, first_summary = asyncio.run(run_evaluation(**kwargs))
    second_dir, second_summary = asyncio.run(run_evaluation(**kwargs))
    assert first_dir == second_dir
    assert first_summary == second_summary
    assert fake.calls == 2
    assert first_summary["openai:fake-model"]["mean_score"] == 1.0


def test_run_logs_comparison_to_mlflow(tmp_path):
    import mlflow

    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps({"case_id": "a", "task_type": "classification", "input": "Ticket A", "expected": "billing"}) + "\n",
        encoding="utf-8",
    )
    prompt = tmp_path / "prompts.toml"
    prompt.write_text(
        'version = "v1"\n' + "\n".join(
            f'[tasks.{task}]\nsystem = "Answer briefly"'
            for task in ("classification", "extraction", "qa", "summarization", "instruction_following")
        ),
        encoding="utf-8",
    )
    tracking_uri = "sqlite:///" + (tmp_path / "mlflow.db").as_posix()
    asyncio.run(run_evaluation(
        dataset=dataset,
        prompt_file=prompt,
        model_specs=["openai:fake-model"],
        output_root=tmp_path / "runs",
        run_id="mlflow-run",
        tracking_uri=tracking_uri,
        provider_factory=lambda _: FakeProvider(),
    ))
    experiment = mlflow.get_experiment_by_name("evalframe")
    assert experiment is not None
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    assert len(runs) == 2


def test_rate_limit_stops_queued_cases_without_checkpointing_429(tmp_path):
    class RateLimitError(Exception):
        status_code = 429

    class RateLimitedProvider:
        calls = 0

        async def generate(self, model, system, user, max_output_tokens):
            self.calls += 1
            raise RateLimitError()

        async def close(self):
            pass

    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        "\n".join(
            json.dumps({"case_id": str(i), "task_type": "classification", "input": "Ticket", "expected": "billing"})
            for i in range(3)
        ) + "\n",
        encoding="utf-8",
    )
    prompt = tmp_path / "prompts.toml"
    prompt.write_text(
        'version = "v1"\n' + "\n".join(
            f'[tasks.{task}]\nsystem = "Answer briefly"'
            for task in ("classification", "extraction", "qa", "summarization", "instruction_following")
        ),
        encoding="utf-8",
    )
    fake = RateLimitedProvider()
    with pytest.raises(ValueError, match="HTTP 429"):
        asyncio.run(run_evaluation(
            dataset=dataset,
            prompt_file=prompt,
            model_specs=["openrouter:fake-model"],
            output_root=tmp_path / "runs",
            run_id="rate-limited",
            concurrency=1,
            provider_factory=lambda _: fake,
            log_mlflow=False,
        ))
    assert fake.calls == 1
    checkpoint = next((tmp_path / "runs" / "rate-limited").glob("cases-*.jsonl"))
    assert checkpoint.read_text(encoding="utf-8") == ""

    # A 429 saved by an older version must not permanently skip that case.
    checkpoint.write_text(json.dumps({"case_id": "0", "status": "error", "status_code": 429}) + "\n", encoding="utf-8")
    healthy = FakeProvider()
    _, summary = asyncio.run(run_evaluation(
        dataset=dataset,
        prompt_file=prompt,
        model_specs=["openrouter:fake-model"],
        output_root=tmp_path / "runs",
        run_id="rate-limited",
        concurrency=1,
        provider_factory=lambda _: healthy,
        log_mlflow=False,
    ))
    assert healthy.calls == 3
    assert summary["openrouter:fake-model"]["mean_score"] == 1.0
