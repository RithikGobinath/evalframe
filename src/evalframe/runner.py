"""Concurrent evaluation, local checkpoints, and MLflow reporting."""

from __future__ import annotations

import asyncio
import json
import re
import statistics
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .cases import EvalCase, load_cases
from .prompts import load_prompts
from .providers import Provider, create_provider
from .scoring import score_case


def parse_model_spec(spec: str) -> tuple[str, str]:
    provider, separator, model = spec.partition(":")
    if not separator or provider not in {"openai", "anthropic", "openrouter"} or not model.strip():
        raise ValueError(f"Invalid model {spec!r}; use openai:MODEL_ID, anthropic:MODEL_ID, or openrouter:MODEL_ID")
    return provider, model


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * percentile
    low, high = int(index), min(int(index) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def summarize(records: list[dict]) -> dict[str, float]:
    if not records:
        raise ValueError("Cannot summarize an empty run")
    scores = [float(row["score"]) if row["status"] == "ok" else 0.0 for row in records]
    latency = [float(row["latency_ms"]) for row in records if row["status"] == "ok"]
    metrics = {
        "cases": len(records),
        "completed": sum(row["status"] == "ok" for row in records),
        "errors": sum(row["status"] != "ok" for row in records),
        "mean_score": statistics.mean(scores),
        "latency_p50_ms": _percentile(latency, 0.50),
        "latency_p95_ms": _percentile(latency, 0.95),
        "input_tokens": sum(row.get("input_tokens") or 0 for row in records),
        "output_tokens": sum(row.get("output_tokens") or 0 for row in records),
    }
    by_task: dict[str, list[float]] = defaultdict(list)
    for row, score in zip(records, scores):
        by_task[row["task_type"]].append(score)
    for task_type, task_scores in by_task.items():
        metrics[f"{task_type}_mean_score"] = statistics.mean(task_scores)
        metrics[f"{task_type}_cases"] = len(task_scores)
    return metrics


async def _evaluate_case(
    case: EvalCase,
    provider: Provider,
    model: str,
    system: str,
    max_output_tokens: int,
    semaphore: asyncio.Semaphore,
    rate_limited: asyncio.Event,
) -> dict | None:
    async with semaphore:
        if rate_limited.is_set():
            return None
        started = time.perf_counter()
        try:
            response = await provider.generate(model, system, case.input, max_output_tokens)
            score = score_case(case, response.text)
            return {
                "case_id": case.case_id,
                "task_type": case.task_type,
                "status": "ok",
                "output": response.text,
                "score": score.value,
                "score_details": score.details,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "request_id": response.request_id,
                "finish_reason": response.finish_reason,
                "tags": list(case.tags),
            }
        except Exception as exc:
            # Provider error bodies may contain user content; keep only safe metadata.
            if getattr(exc, "status_code", None) == 429:
                rate_limited.set()
            return {
                "case_id": case.case_id,
                "task_type": case.task_type,
                "status": "error",
                "error_type": type(exc).__name__,
                "status_code": getattr(exc, "status_code", None),
                "score": 0.0,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "tags": list(case.tags),
            }


def _read_checkpoint(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    completed: dict[str, dict] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Corrupt checkpoint at {path}:{line_number}") from exc
        completed[row["case_id"]] = row
    return completed


async def _run_model(
    cases: list[EvalCase],
    spec: str,
    systems: dict[str, str],
    checkpoint: Path,
    concurrency: int,
    max_output_tokens: int,
    provider_factory: Callable[[str], Provider],
) -> list[dict]:
    provider_name, model = parse_model_spec(spec)
    existing = _read_checkpoint(checkpoint)
    unknown = set(existing) - {case.case_id for case in cases}
    if unknown:
        raise ValueError(f"Checkpoint contains unknown case IDs: {sorted(unknown)}")
    # Older checkpoints may contain 429 rows. Those requests never produced an
    # evaluation result, so allow the same run ID to retry them later.
    pending = [
        case for case in cases
        if case.case_id not in existing or existing[case.case_id].get("status_code") == 429
    ]
    if pending:
        provider = provider_factory(provider_name)
        try:
            semaphore = asyncio.Semaphore(concurrency)
            rate_limited = asyncio.Event()
            tasks = [
                asyncio.create_task(
                    _evaluate_case(
                        case, provider, model, systems[case.task_type], max_output_tokens,
                        semaphore, rate_limited,
                    )
                )
                for case in pending
            ]
            with checkpoint.open("a", encoding="utf-8") as stream:
                for task in asyncio.as_completed(tasks):
                    row = await task
                    if row is None or row.get("status_code") == 429:
                        continue
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    existing[row["case_id"]] = row
            if rate_limited.is_set():
                raise ValueError(
                    f"{spec} returned HTTP 429 (rate limited). Pending cases were not called; "
                    "retry this run ID after checking OpenRouter activity and limits."
                )
        finally:
            await provider.close()
    return [existing[case.case_id] for case in cases]


async def run_evaluation(
    dataset: Path,
    prompt_file: Path,
    model_specs: list[str],
    output_root: Path,
    run_id: str | None = None,
    max_cases: int | None = None,
    concurrency: int = 5,
    max_output_tokens: int = 512,
    tracking_uri: str | None = None,
    log_mlflow: bool = True,
    provider_factory: Callable[[str], Provider] = create_provider,
) -> tuple[Path, dict[str, dict[str, float]]]:
    if not model_specs or len(set(model_specs)) != len(model_specs):
        raise ValueError("Provide one or more unique --model values")
    for spec in model_specs:
        parse_model_spec(spec)
    if concurrency < 1 or max_output_tokens < 1 or (max_cases is not None and max_cases < 1):
        raise ValueError("concurrency, max_output_tokens, and max_cases must be positive")
    cases, dataset_digest = load_cases(dataset)
    prompts = load_prompts(prompt_file)
    if max_cases is not None:
        cases = cases[:max_cases]
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id) or run_id in {".", ".."}:
        raise ValueError("run_id may contain only letters, numbers, dots, underscores, and hyphens")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    manifest = {
        "run_id": run_id,
        "dataset_sha256": dataset_digest,
        "prompt_sha256": prompts.digest,
        "prompt_version": prompts.version,
        "models": model_specs,
        "case_ids": [case.case_id for case in cases],
        "max_output_tokens": max_output_tokens,
    }
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            raise ValueError(f"Run ID {run_id!r} already exists with different inputs")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summaries: dict[str, dict[str, float]] = {}
    result_paths: dict[str, Path] = {}
    for spec in model_specs:
        import hashlib

        path = run_dir / f"cases-{hashlib.sha256(spec.encode()).hexdigest()[:12]}.jsonl"
        records = await _run_model(
            cases, spec, prompts.systems, path, concurrency, max_output_tokens, provider_factory
        )
        summaries[spec] = summarize(records)
        result_paths[spec] = path
    (run_dir / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")

    if log_mlflow:
        import mlflow

        # Current MLflow releases put the legacy filesystem backend in
        # maintenance mode. Use SQLite for a durable local development store.
        mlflow.set_tracking_uri(tracking_uri or "sqlite:///mlflow.db")
        mlflow.set_experiment("evalframe")
        with mlflow.start_run(run_name=run_id):
            mlflow.log_params({
                "dataset_sha256": dataset_digest,
                "prompt_sha256": prompts.digest,
                "prompt_version": prompts.version,
                "case_count": len(cases),
            })
            mlflow.log_artifact(str(dataset), artifact_path="inputs")
            mlflow.log_artifact(str(prompt_file), artifact_path="inputs")
            mlflow.log_artifact(str(manifest_path), artifact_path="inputs")
            for spec in model_specs:
                provider_name, model = parse_model_spec(spec)
                with mlflow.start_run(run_name=spec, nested=True):
                    mlflow.log_params({
                        "provider": provider_name,
                        "model": model,
                        "max_output_tokens": max_output_tokens,
                        "concurrency": concurrency,
                    })
                    mlflow.log_metrics(summaries[spec])
                    mlflow.log_artifact(str(result_paths[spec]), artifact_path="cases")
            mlflow.log_artifact(str(run_dir / "summary.json"), artifact_path="reports")
    return run_dir, summaries
