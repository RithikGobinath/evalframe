# Public-source 500-case Cloud Run benchmark — September 25, 2026

[Cloud Run execution `evalframe-public-benchmark-rrkfr`](https://console.cloud.google.com/run/jobs/executions/details/us-central1/evalframe-public-benchmark-rrkfr?project=472137125970) completed successfully in **18 minutes 47 seconds**. GPT-6 Luna and Claude Haiku 4.5 each processed the same 500 public-source cases: 100 cases in each of five task types. All 1,000 requests returned without a recorded API error. The 20-case-per-model live diagnostic also completed with zero errors.

| Metric | GPT-6 Luna | Claude Haiku 4.5 |
| --- | ---: | ---: |
| Cases completed | 500 / 500 | 500 / 500 |
| API errors | 0 | 0 |
| Overall mean of task scores | **68.6%** | **64.5%** |
| Classification: exact intent | 92.0% | 82.0% |
| Extraction: reference token F1 | 67.0% | 68.4% |
| Grounded Q&A: reference token F1 | 60.4% | 51.0% |
| Summarization: reference ROUGE-L F1 | 40.5% | 31.2% |
| Instruction following: strict IFEval | 83.0% | 90.0% |
| Median response latency | 1,896 ms | 1,074 ms |
| 95th percentile response latency | 5,439 ms | 4,023 ms |
| Input / output tokens | 86,002 / 45,348 | 93,286 / 46,862 |
| Responses stopped at output limit | 22 | 6 |

These scores are **specific to this dataset, prompt, output limit, and scorer**. The overall mean combines exact pass rates and lexical similarity metrics, so it is not a calibrated quality percentage. GPT scored higher on classification, Q&A, and reference-summary overlap; Claude scored higher on extraction overlap and IFEval constraints. This is a descriptive comparison, not a statistically validated ranking.

## Review notes

- The 512-token output limit affected 22 GPT responses and 6 Claude responses, all in instruction following. Six GPT responses had no visible text and scored zero; they used the full output-token allowance. A higher output limit could change the instruction-following result.
- Reference overlap can understate a valid answer. For example, case `pub-qa-004` has the one-word reference “Walmart.” Both models answered “Walmart” in a fuller sentence and received low token F1. This score measures text overlap, not whether the answer is factually correct.
- Some source questions admit more than one passage-supported answer. In `pub-ext-089`, the Dolly reference is “Odyssey,” while both models returned “The Aeneid by Virgil”; the passage mentions the Trojan Horse in both poems. The automatic scorer assigns zero to both model outputs. This case needs human review before being used for a quality claim.
- The Dolly `summarization` category includes requests phrased as questions or fact lists. The 100 cases came from that source category but are not all conventional short-summary requests. ROUGE-L F1 is particularly sensitive to response length and wording.
- The 500 references were screened by deterministic rules and were not individually human-reviewed. These public examples may have appeared in model training.

## Reproducibility and cost

- [Dataset and scoring guide](../../docs/public-benchmark.md); [source manifest](../../data/public500-v1.sources.json). Dataset SHA-256: `9440105600e3ad7e5535821117d62885bd5c593c6f91cd44008d74de93e3d840`.
- Prompt: [`public-v1.toml`](../../prompts/public-v1.toml), SHA-256 `1f2c38b4224aab6d64ebdacf858026fce508371417d1f3374eccc882040cc822`.
- Models: `openrouter:openai/gpt-6-luna` and `openrouter:anthropic/claude-haiku-4.5`; maximum 512 output tokens, concurrency 2, one Cloud Run task.
- [Run manifest](manifest.json) records code revision `416d906f69182c2e5aacda0253f1698143d71c5c` and image digest `sha256:d514168c61408f093c7308bbaf5f19382c37d4cf78e71b83ead296d65c73efca`.
- At OpenRouter's September 25 posted token rates ([GPT-6 Luna](https://openrouter.ai/openai/gpt-6-luna), [Claude Haiku 4.5](https://openrouter.ai/anthropic/claude-haiku-4.5)), the recorded token totals imply about **$0.36 in model charges** for this full run. This is an estimate, not the billed amount, and excludes the diagnostic, cloud infrastructure, taxes, and any routing or cache adjustments. Google Cloud has a separate $5/month **alert**, not a hard cap. The OpenRouter key setting has changed since earlier reports; see [current budget status](../../docs/budget-and-cloud.md).

## Artifacts

- [Full summary](summary.json)
- [Run manifest](manifest.json)
- [GPT case results](gpt-6-luna.jsonl)
- [Claude case results](claude-haiku-4.5.jsonl)
- Cloud Storage, including MLflow SQLite and artifacts: `gs://evalframe-rithik-2026-results/evalframe/runs/public-benchmark500-v1/`

Both downloaded case files were checked against all 500 manifest IDs and the summary's per-task means. Each has 500 successful rows with unique IDs. The full outputs and scoring details are in the case files.
