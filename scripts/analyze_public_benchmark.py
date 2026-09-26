"""Recompute the published public benchmark and its paired task comparisons."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

from evalframe.runner import summarize


MODELS = {
    "openrouter:openai/gpt-6-luna": "gpt-6-luna.jsonl",
    "openrouter:anthropic/claude-haiku-4.5": "claude-haiku-4.5.jsonl",
}
TASKS = (
    "classification", "extraction", "qa", "summarization", "instruction_following"
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def analyze(dataset: Path, prompt: Path, results_dir: Path) -> dict:
    dataset_bytes = dataset.read_bytes()
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()
    prompt_hash = hashlib.sha256(prompt.read_bytes()).hexdigest()
    cases = _jsonl(dataset)
    case_ids = [case["case_id"] for case in cases]
    if len(cases) != 500 or len(set(case_ids)) != 500:
        raise ValueError("Expected 500 unique public cases")
    manifest = json.loads((results_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["dataset_sha256"] != dataset_hash or manifest["prompt_sha256"] != prompt_hash:
        raise ValueError("Published manifest does not match dataset and prompt bytes")
    if manifest["case_ids"] != case_ids or set(manifest["models"]) != set(MODELS):
        raise ValueError("Published manifest has different cases or models")
    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    if set(summary) != set(MODELS):
        raise ValueError("Published summary has different models")
    by_model = {}
    model_info = {}
    for spec, filename in MODELS.items():
        rows = _jsonl(results_dir / filename)
        if len(rows) != len(case_ids) or {row["case_id"] for row in rows} != set(case_ids):
            raise ValueError(f"Incomplete or duplicate results for {spec}")
        recomputed = summarize(rows)
        for name, value in summary[spec].items():
            if name not in recomputed or not math.isclose(recomputed[name], value, rel_tol=1e-12, abs_tol=1e-9):
                raise ValueError(f"Summary mismatch for {spec}: {name}")
        by_model[spec] = {row["case_id"]: row for row in rows}
        model_info[spec] = {
            "cases": len(rows),
            "request_errors": sum(row["status"] != "ok" for row in rows),
            "output_limit": sum(row.get("finish_reason") == "length" for row in rows),
            "empty_visible_output": sum(row["status"] == "ok" and not row.get("output", "").strip() for row in rows),
            "input_tokens": sum(row.get("input_tokens") or 0 for row in rows),
            "output_tokens": sum(row.get("output_tokens") or 0 for row in rows),
            "latency_p50_ms": recomputed["latency_p50_ms"],
            "latency_p95_ms": recomputed["latency_p95_ms"],
        }
    gpt, claude = (by_model[spec] for spec in MODELS)
    task_stats = {}
    for task in TASKS:
        ids = [case["case_id"] for case in cases if case["task_type"] == task]
        if len(ids) != 100:
            raise ValueError(f"Expected 100 {task} cases")
        gpt_scores = [float(gpt[case_id]["score"]) for case_id in ids]
        claude_scores = [float(claude[case_id]["score"]) for case_id in ids]
        task_stats[task] = {
            "cases": len(ids),
            "gpt_mean": statistics.mean(gpt_scores),
            "claude_mean": statistics.mean(claude_scores),
            "gpt_higher": sum(a > b for a, b in zip(gpt_scores, claude_scores)),
            "claude_higher": sum(a < b for a, b in zip(gpt_scores, claude_scores)),
            "tied": sum(a == b for a, b in zip(gpt_scores, claude_scores)),
        }
    return {
        "dataset_sha256": dataset_hash,
        "prompt_sha256": prompt_hash,
        "models": model_info,
        "tasks": task_stats,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/public500-v1.jsonl"))
    parser.add_argument("--prompt", type=Path, default=Path("prompts/public-v1.toml"))
    parser.add_argument("--results", type=Path, default=Path("results/public-benchmark500-v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.dataset, args.prompt, args.results)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(args.output)
