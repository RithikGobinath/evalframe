# Public-source benchmark: 500 cases per model

**Run:** September 25, 2026 · [Cloud Run execution](https://console.cloud.google.com/run/jobs/executions/details/us-central1/evalframe-public-benchmark-rrkfr?project=472137125970) · 18m 47s · 1,000 completed requests · **0 API errors**

GPT-6 Luna and Claude Haiku 4.5 answered the **same 500 public-source cases**, 100 per task. Cases came from [BANKING77, Dolly 15k, and IFEval](../../docs/public-benchmark.md). The table is organized by metric because an exact pass rate and a text-overlap score do not mean the same thing.

| Task | Measure | GPT-6 Luna | Claude Haiku 4.5 |
| --- | --- | ---: | ---: |
| Banking intent classification | Exact label | **92/100** | 82/100 |
| Instruction following | Strict IFEval pass | 83/100 | **90/100** |
| Information extraction | Reference token F1, mean | 0.670 | **0.684** |
| Grounded Q&A | Reference token F1, mean | **0.604** | 0.510 |
| Summarization | Reference ROUGE-L F1, mean | **0.405** | 0.312 |

**Read the rows separately.** GPT had more exact classification passes; Claude had more strict IFEval passes. GPT had higher reference overlap on Q&A and summarization; extraction overlap was close. These are scores for this prompt, sample, and 512-token output limit. They are not a general quality ranking.

## Paired view

The two models saw identical case IDs. Counts below show which model scored higher **on an individual case**; a tie includes cases where both passed, both failed, or received the same overlap score.

| Task | GPT higher | Claude higher | Tied |
| --- | ---: | ---: | ---: |
| Classification | 11 | 1 | 88 |
| Instruction following | 5 | 12 | 83 |
| Extraction | 17 | 23 | 60 |
| Grounded Q&A | 73 | 27 | 0 |
| Summarization | 79 | 20 | 1 |

This is a descriptive paired comparison on a deterministically selected public sample. It is not a significance test or evidence of performance on unseen production requests. The [machine-readable paired analysis](paired-analysis.json) is recomputed from the case files by [`scripts/analyze_public_benchmark.py`](../../scripts/analyze_public_benchmark.py).

## Where the score needs context

- **Output cap:** 22 GPT and 6 Claude responses stopped at the 512-token limit, all on instruction-following cases. Six GPT responses had no visible text despite using the output allowance; they scored zero. The IFEval comparison could change with a different limit.
- **Valid answer, low text overlap:** `pub-qa-004` has the reference `Walmart`. Both models named Walmart in a longer correct sentence and received low token F1. The scorer measures overlap with one reference, not factual correctness.
- **Ambiguous source reference:** `pub-ext-089` asks which epic poem discussed the Trojan Horse. The Dolly reference is `Odyssey`; both models answered `The Aeneid by Virgil`. The supplied passage supports both, yet token F1 assigns zero to the model answers. This case should be adjudicated before drawing a quality conclusion.
- **Task-label drift:** Dolly's `summarization` category includes questions and fact-list requests. The selected 100 cases inherit that category, but not every prompt asks for a conventional summary. ROUGE-L rewards shared wording and can miss factual errors or valid paraphrases.

The 500 source references were selected by fixed filters and were **not individually human-reviewed**. Public examples may have been seen during model training. The [dataset method and source licenses](../../docs/public-benchmark.md) describe the selection and attribution.

## Run health and cost

| Measure | GPT-6 Luna | Claude Haiku 4.5 |
| --- | ---: | ---: |
| Completed / errors | 500 / 0 | 500 / 0 |
| Median latency | 1,896 ms | 1,074 ms |
| 95th-percentile latency | 5,439 ms | 4,023 ms |
| Input tokens | 86,002 | 93,286 |
| Output tokens | 45,348 | 46,862 |
| Responses stopped at output cap | 22 | 6 |

At OpenRouter's September 25 posted text-token rates for [GPT-6 Luna](https://openrouter.ai/openai/gpt-6-luna) and [Claude Haiku 4.5](https://openrouter.ai/anthropic/claude-haiku-4.5), these token totals imply approximately **$0.36 in model charges** for the full run. This is an estimate, not a provider invoice. It excludes the diagnostic run, Cloud Build/Run/Storage, taxes, and any cache or routing adjustments. Google Cloud has a separate **$5 monthly alert**, which does not stop charges; see [budget status](../../docs/budget-and-cloud.md).

## Reproduce and inspect

- [Dataset](../../data/public500-v1.jsonl) and [source manifest](../../data/public500-v1.sources.json); dataset SHA-256 `9440105600e3ad7e5535821117d62885bd5c593c6f91cd44008d74de93e3d840`.
- [Prompt](../../prompts/public-v1.toml), version `public-v1`; SHA-256 `1f2c38b4224aab6d64ebdacf858026fce508371417d1f3374eccc882040cc822`.
- [Run manifest](manifest.json) records model IDs, case IDs, code revision `416d906f69182c2e5aacda0253f1698143d71c5c`, and image digest `sha256:d514168c61408f093c7308bbaf5f19382c37d4cf78e71b83ead296d65c73efca`.
- [GPT outputs](gpt-6-luna.jsonl), [Claude outputs](claude-haiku-4.5.jsonl), [summary](summary.json), and [paired analysis](paired-analysis.json). The case files contain every output, score detail, token count, latency, and finish reason.
- Cloud artifacts, including the exported MLflow SQLite database: `gs://evalframe-rithik-2026-results/evalframe/runs/public-benchmark500-v1/`.

After installing the project, `python scripts/verify_published_results.py` checks both 500-row files against the dataset, prompt, manifest, summary, and paired analysis **without making API calls**. The separate [synthetic throughput run](../cloud-benchmark500-v1/README.md) tested the harness at scale; its easier generated examples should not be compared with these public-source scores.
