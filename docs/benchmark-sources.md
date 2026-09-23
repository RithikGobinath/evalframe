# Proposed 500-case benchmark sources

The 20-case pilot in `data/pilot.jsonl` tests the harness. The full benchmark should use 100 reviewed cases in each task category, selected by stable source ID and committed as a versioned dataset only after the scorers are suitable for the source labels.

| EvalFrame task | Proposed source | Selection and scoring work |
| --- | --- | --- |
| Classification | [Databricks Dolly 15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k) `classification` records | Select short, single-label outputs; normalize the allowable labels per case. |
| Extraction | Dolly 15k `information_extraction` records | Review output shapes and support reference-text scoring where answers are lists or prose. Do not force every reference into the pilot's JSON scorer. |
| Grounded Q&A | Dolly 15k `closed_qa` records | Include the supplied context in the prompt; score with answer normalization and token F1. |
| Summarization | Dolly 15k `summarization` records | Replace phrase coverage with a reference metric and a human-calibrated rubric for factuality. |
| Instruction following | [Google IFEval](https://huggingface.co/datasets/google/IFEval) | Implement its instruction-specific checks before selecting 100 cases. |

Dolly is published under CC BY-SA 3.0, and IFEval under Apache 2.0. Preserve source attribution, source revision, original record IDs, and dataset hashes. Dolly's own dataset card warns that annotation guidance was intentionally broad, so each selected record needs review. These are general-purpose language tasks; they should not be described as a customer-support benchmark.

The benchmark should not be called complete until all 500 cases have validated labels and the scoring method for each task has been reviewed. A public benchmark can also overlap model training data, so the report should say it measures performance on these cases rather than unseen production behavior.
