# Why these public sources

The [public-source benchmark](public-benchmark.md) uses three datasets. The exact revisions, download URLs, licenses, and SHA-256 values are pinned in [`data/public500-v1.sources.json`](../data/public500-v1.sources.json). The [builder](../scripts/build_public500.py) turns the pinned files into the committed 500-case JSONL dataset.

| EvalFrame task | Selected source | Reason for the choice |
| --- | --- | --- |
| Banking intent classification | [PolyAI BANKING77 test split](https://github.com/PolyAI-LDN/task-specific-datasets) | Fixed intent names support exact-label scoring. We selected ten examples from each of ten intents. |
| Information extraction | [Databricks Dolly 15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k) `information_extraction` | Passage, request, and reference answer are available together. Answers are free text, so the scorer uses reference token F1 rather than the pilot's JSON-field scorer. |
| Grounded Q&A | Dolly 15k `closed_qa` | The passage is supplied to the model; reference token F1 provides a reproducible, limited overlap measure. |
| Summarization | Dolly 15k `summarization` | Provides a passage and reference response for ROUGE-L F1. Some source prompts ask questions or request fact lists, so the label is imperfect. |
| Instruction following | [Google IFEval](https://huggingface.co/datasets/google/IFEval) | Its published instruction constraints can be checked by the [official strict verifier](https://github.com/google-research/google-research/tree/master/instruction_following_eval). The selected subset contains one constraint per prompt. |

The earlier plan considered Dolly's `classification` rows, but their open-ended labels did not make a consistent exact-label benchmark. BANKING77 provided a fixed taxonomy. The builder applies deterministic length, duplicate, and answer-overlap filters, then selects by a stable hash order. No benchmark cases were chosen based on the models' measured scores.

These public labels are **not individually human-reviewed**. A passage can support more than one answer, a model can give a correct paraphrase with low lexical overlap, and the public examples may have been present in model training. The [run report](../results/public-benchmark500-v1/README.md) calls out concrete examples. This dataset is a reproducible public-source comparison, not an uncontaminated holdout or a customer-support production benchmark.

The source cards mark BANKING77 as CC BY 4.0, Dolly 15k as CC BY-SA 3.0, and IFEval as Apache 2.0. The case file retains the source and revision for each row. Keep that attribution and the applicable source terms with redistributed derivatives.
