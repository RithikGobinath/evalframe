# EvalFrame Cloud Run benchmark — September 24, 2026

Cloud Run execution [`evalframe-benchmark-2pdxh`](https://console.cloud.google.com/run/jobs/executions/details/us-central1/evalframe-benchmark-2pdxh?project=472137125970) completed successfully in **13 minutes 33 seconds**. Both models processed the same 500 synthetic cases, covering five task types. All 1,000 model requests completed without recorded errors. The job exported the summary, case files, and MLflow data to `gs://evalframe-rithik-2026-results/evalframe/runs/cloud-benchmark500-v1/`.

| Metric | GPT-6 Luna | Claude Haiku 4.5 |
| --- | ---: | ---: |
| Cases completed | 500 / 500 | 500 / 500 |
| Errors | 0 | 0 |
| Overall mean score | **96.8%** | **68.0%** |
| Classification | 99.0% | 91.0% |
| Extraction (strict raw JSON) | 98.7% | 0.0% |
| Grounded Q&A (token F1) | 86.3% | 74.1% |
| Summarization (required phrase proxy) | 100.0% | 100.0% |
| Instruction following | 100.0% | 75.0% |
| Median response latency | 1,385 ms | 794 ms |
| 95th percentile response latency | 2,346 ms | 1,250 ms |
| Input / output tokens | 35,007 / 19,146 | 36,177 / 9,045 |

Claude wrapped all 100 extraction responses in Markdown code fences, which the raw JSON scorer rejects. **95 of those 100 fenced outputs contained the exact expected JSON object inside the fences.** The 0% extraction score therefore primarily measures a format mismatch, not missing field content. Its 75% instruction-following score also reflects 25 cases that failed a JSON-format constraint. The scores are specific to this prompt and deterministic rubric.

## Reproducibility and limits

- Dataset: [`data/benchmark500.jsonl`](../../data/benchmark500.jsonl), 100 synthetic cases per task type. These generated examples verify throughput and repeatability; they do not measure performance on an independent public dataset or real user data.
- Prompt: [`prompts/baseline.toml`](../../prompts/baseline.toml), version `baseline-v1`.
- Models: `openrouter:openai/gpt-6-luna` and `openrouter:anthropic/claude-haiku-4.5`; maximum 512 output tokens, concurrency 2, one Cloud Run task.
- The [manifest](manifest.json) records dataset/prompt SHA-256 hashes, code revision `869495ffde3d58fb6cfb885f31eb61de9877a315`, and container digest `sha256:481fa54d8bccdc4f4479e7c95b60fd88f6504546edd4a39ac333ebf368b835e4`.
- Google Cloud has a separate $5 monthly **alert** for this project; it is not a hard cost cap. The actual cloud bill can report with delay. OpenRouter spending is separately limited by the dedicated key's $4 monthly credit limit.

## Artifacts

- [Full summary](summary.json)
- [Run manifest](manifest.json)
- [GPT case results](gpt-6-luna.jsonl)
- [Claude case results](claude-haiku-4.5.jsonl)
- MLflow SQLite database and artifacts: `gs://evalframe-rithik-2026-results/evalframe/runs/cloud-benchmark500-v1/artifacts/mlflow/`

The downloaded case files were checked against all 500 IDs in the manifest and against the summary means; each contains 500 successful rows. The [earlier local run](../benchmark500-v1/README.md) is available for comparison.
