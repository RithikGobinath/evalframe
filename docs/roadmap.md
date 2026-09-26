# Project status and next work

EvalFrame has a working evaluation harness, published case-level results, and a finite Cloud Run deployment. The public-source benchmark is reproducible, but its references are not individually human-reviewed. The prompt-injection experiment is small and synthetic. Those limits define the next work more clearly than another large model run would.

## Shipped

| Area | Evidence |
| --- | --- |
| Five-task pilot and scoring | [Pilot dataset](../data/pilot.jsonl), provider adapters, CLI, and local tests |
| Synthetic throughput benchmark | [500-case Cloud Run report](../results/cloud-benchmark500-v1/README.md); useful for runner and scorer behavior, not general model quality |
| Public-source comparison | [500 cases per model](../results/public-benchmark500-v1/README.md), pinned [source manifest](../data/public500-v1.sources.json), task-specific metrics, and all 1,000 outputs |
| Prompt-injection experiment | [40 paired cases](../results/prompt-injection-40-v1/README.md) with frozen protocol, baseline, one mitigation, outputs, costs, and limitations |
| Durable cloud execution | [Cloud Run operations](cloud-run.md): dedicated service account, Secret Manager key, per-case Cloud Storage checkpoints, MLflow export, one task, zero retries, no schedule |
| Budget visibility | [Budget status](budget-and-cloud.md): separate Google Cloud $5 monthly **alert** and OpenRouter key limit; neither should be described as a combined hard cap |

## Highest-value follow-up work

1. **Audit references.** Have an independent human review a sample of each public task, especially ambiguous extraction answers and the Dolly `summarization` rows that are really question answering. Record corrections as a new dataset version; keep v1 unchanged for reproducibility.
2. **Calibrate quality measures.** Compare lexical F1 and ROUGE-L against human judgments for factual correctness and acceptable paraphrases. Keep strict exact checks for formats and IFEval constraints.
3. **Build a true holdout.** Choose a real application, collect permissioned task examples, separate prompt development from final evaluation, and document data handling. Public examples may overlap model training data.
4. **Strengthen prompt-injection testing.** Add independent human review, realistic multi-document retrieval, benign controls, varied attacker goals, and repeated responses. The first 40-case baseline had zero attack successes, so it cannot establish mitigation efficacy.
5. **Tighten operational controls.** Add a run-level cost guard and provider request limits before larger paid runs; keep checking the live key limit and Google Cloud billing. The Cloud budget is an alert, not a stop mechanism.
6. **Automate verification.** Promote the existing workflow template into an active CI workflow once GitHub credentials allow workflow changes. The offline verifier already checks the published summaries and case files.

Each new benchmark version should publish its frozen inputs, exact scorer, model settings, case-level outputs, cost basis, and known failure examples before making comparative claims.
