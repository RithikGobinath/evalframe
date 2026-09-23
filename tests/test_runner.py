import asyncio
import json

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
