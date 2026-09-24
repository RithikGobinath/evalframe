"""EvalFrame command line interface."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter
from pathlib import Path

from .cases import load_cases
from .prompts import load_prompts
from .runner import parse_model_spec, run_evaluation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evalframe", description="Cross-provider LLM evaluations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="Validate dataset and prompt versions")
    validate.add_argument("--dataset", type=Path, required=True)
    validate.add_argument("--prompt", type=Path, required=True)

    run = subparsers.add_parser("run", help="Run one or more models on the same cases")
    run.add_argument("--dataset", type=Path, required=True)
    run.add_argument("--prompt", type=Path, required=True)
    run.add_argument("--model", action="append", required=True, help="openai:MODEL_ID, anthropic:MODEL_ID, or openrouter:MODEL_ID")
    run.add_argument("--output-root", type=Path, default=Path("runs"))
    run.add_argument("--run-id")
    run.add_argument("--max-cases", type=int)
    run.add_argument("--concurrency", type=int, default=5)
    run.add_argument("--max-output-tokens", type=int, default=512)
    run.add_argument("--tracking-uri", default=os.getenv("MLFLOW_TRACKING_URI"))
    run.add_argument("--no-mlflow", action="store_true", help="Local diagnostic runs only")
    run.add_argument("--gcs-bucket", help="Durable checkpoints and artifacts for a Cloud Run Job")
    run.add_argument("--gcs-prefix", default="evalframe")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            cases, dataset_hash = load_cases(args.dataset)
            prompts = load_prompts(args.prompt)
            print(json.dumps({
                "cases": len(cases),
                "task_counts": Counter(case.task_type for case in cases),
                "dataset_sha256": dataset_hash,
                "prompt_version": prompts.version,
                "prompt_sha256": prompts.digest,
            }, indent=2))
            return 0
        for spec in args.model:
            provider, _ = parse_model_spec(spec)
            key = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
            }[provider]
            if not os.getenv(key):
                raise ValueError(f"{key} is required for {provider} runs")
        run_store = None
        if args.gcs_bucket:
            from .cloud_store import GCSRunStore

            if not args.run_id:
                raise ValueError("--run-id is required with --gcs-bucket")
            if args.no_mlflow or args.tracking_uri:
                raise ValueError("Cloud runs require local MLflow with the default tracking URI")
            for name in ("EVALFRAME_CODE_REVISION", "EVALFRAME_IMAGE_DIGEST"):
                if not os.getenv(name):
                    raise ValueError(f"{name} is required for cloud runs")
            run_store = GCSRunStore(args.gcs_bucket, args.gcs_prefix)
        run_dir, summaries = asyncio.run(run_evaluation(
            dataset=args.dataset,
            prompt_file=args.prompt,
            model_specs=args.model,
            output_root=args.output_root,
            run_id=args.run_id,
            max_cases=args.max_cases,
            concurrency=args.concurrency,
            max_output_tokens=args.max_output_tokens,
            tracking_uri=args.tracking_uri,
            log_mlflow=not args.no_mlflow,
            run_store=run_store,
        ))
        print(json.dumps({"run_dir": str(run_dir), "models": summaries}, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        build_parser().error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
