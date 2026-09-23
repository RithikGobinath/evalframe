# 500-case throughput run

`data/benchmark500.jsonl` contains 500 deterministic **synthetic** cases: 100 each for classification, JSON extraction, grounded Q&A, phrase-constrained summarization, and instruction following. `scripts/build_benchmark500.py` regenerates it exactly. Each case includes an answer for an offline scorer check. The model sees only the `input` field, not the answer. This dataset demonstrates harness throughput and reproducibility; it does not establish production model quality or performance on the proposed Dolly/IFEval public sources.

## Budget as checked September 23, 2026

- OpenRouter account: $4.65 available credit, auto top-up off. A $5.00 credit purchase was recorded today, so no further purchase is planned.
- The dedicated EvalFrame API key is limited to **$4 of credits per month**. This is the provider-side ceiling for its model calls. Do not use a different unlimited key for this run.
- Google Cloud project billing remains disabled. Run locally with local MLflow/SQLite; Cloud Run deployment is a separate milestone.
- Current model prices: [GPT-6 Luna](https://openrouter.ai/openai/gpt-6-luna) is $0.10/M input and $0.50/M output tokens; [Claude Haiku 4.5](https://openrouter.ai/anthropic/claude-haiku-4.5) is $1/M input and $5/M output tokens. Recheck before a live run.

With 500 cases **per model**, 1,024 reserved input tokens per case, and `--max-output-tokens 512`, the offline planning estimate is $0.18 for GPT and $1.79 for Claude, or $1.97 combined. A 2× margin is $3.94, below the $4 key limit. These figures assume the listed text-token prices; provider accounting and pricing may differ. The key cap, rather than this estimate, is the spending control.

Reproduce the estimate without making an API call:

```bash
./.venv/Scripts/python.exe scripts/estimate_benchmark500.py --credit-balance 4.65
```

## Run sequence

1. `evalframe validate` confirms the 500-case dataset before paid calls.
2. Run five cases (one per task) against both models under a new run ID. Inspect the outputs and OpenRouter activity for cost, errors, and truncation. A 429 stops queued cases without automatic retries.
3. If both models return valid outputs, run all 500 cases against each model. The CLI writes a local checkpoint after every case and MLflow parent/child runs at completion. Reusing the same run ID with unchanged inputs skips completed cases. Old 429 rows are retried.

```bash
./.venv/Scripts/evalframe.exe validate --dataset data/benchmark500.jsonl --prompt prompts/baseline.toml

./.venv/Scripts/evalframe.exe run --dataset data/benchmark500.jsonl --prompt prompts/baseline.toml \
  --model openrouter:openai/gpt-6-luna \
  --model openrouter:anthropic/claude-haiku-4.5 \
  --max-cases 5 --max-output-tokens 512 --concurrency 2 --run-id paid-smoke-v1

./.venv/Scripts/evalframe.exe run --dataset data/benchmark500.jsonl --prompt prompts/baseline.toml \
  --model openrouter:openai/gpt-6-luna \
  --model openrouter:anthropic/claude-haiku-4.5 \
  --max-output-tokens 512 --concurrency 2 --run-id benchmark500-v1
```

The full comparison sends up to **1,000 model requests** and may take considerable time. The synthetic benchmark is separate from the planned curated public-source evaluation and from Cloud Run deployment. The run is not complete until `runs/benchmark500-v1/summary.json` reports 500 cases for each model and the case-level files have been reviewed.
