# Public-source 500-case benchmark

This benchmark has 100 examples each for classification, extraction, grounded question answering, summarization, and instruction following. The source dataset, source revision, original row ID, and source license are recorded in each JSONL case. The pinned download URLs and SHA-256 hashes are in [`data/public500-v1.sources.json`](../data/public500-v1.sources.json).

| Task | Source | Scoring |
| --- | --- | --- |
| Classification | [PolyAI BANKING77](https://github.com/PolyAI-LDN/task-specific-datasets), test split, ten examples from each of ten banking intents | Exact intent label |
| Extraction | [Databricks Dolly 15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k), information extraction | Token F1 against the reference answer |
| Grounded Q&A | Dolly 15k, closed QA | Token F1 against the reference answer |
| Summarization | Dolly 15k, summarization | ROUGE-L F1 against the reference summary |
| Instruction following | [Google IFEval](https://huggingface.co/datasets/google/IFEval), single-constraint prompts | [Official strict IFEval verifier](https://github.com/google-research/google-research/tree/master/instruction_following_eval) |

Selection uses fixed length, overlap, and duplicate filters plus a stable SHA-256 ordering. The 100 IFEval prompts span 11 verifiable constraint types. Cases are interleaved by task so that a 20-case diagnostic includes four of each type. Rebuild from pinned sources with `python scripts/build_public500.py`, or use `--offline` after the downloads are cached. Validate with `evalframe validate --dataset data/public500-v1.jsonl --prompt prompts/public-v1.toml`. The checked-in dataset SHA-256 is `9440105600e3ad7e5535821117d62885bd5c593c6f91cd44008d74de93e3d840`.

Source terms: BANKING77 is marked CC BY 4.0, Dolly 15k CC BY-SA 3.0, and IFEval Apache 2.0 by their publishers. The pinned Google Research verifier is vendored under `src/instruction_following_eval` with its Apache 2.0 license and source notice. This benchmark is an adapted selection: task prompts and selection rules were added, and only a subset of each source is included. Keep the source attribution and applicable source licenses with redistributed copies.

The reference answers were selected by deterministic filters but were **not individually human-reviewed**. Token overlap and ROUGE-L can reward wording and miss factual errors or valid paraphrases. The overall mean averages unlike metrics, so compare per-task scores and inspect individual outputs. The public data may have appeared in model training. This benchmark is useful for a reproducible comparison on public examples; it is not an uncontaminated holdout or a production quality certification.
