# Build roadmap

## Milestone 1: Pilot harness — in progress

- [x] Define and validate a versioned case schema.
- [x] Add 20 synthetic cases across five task types.
- [x] Add OpenAI and Claude adapters, deterministic scorers, CLI, and MLflow logging.
- [x] Add a Dockerfile and offline tests.
- [x] Run paid API smoke tests against chosen model IDs.
- [ ] Review pilot score disagreements and improve prompts/rubrics.

## Milestone 2: Credible 500-case benchmark

- [x] Build a 500-case synthetic throughput dataset with 100 cases per task and an offline harness check; see [500-case run](500-case-run.md). This is separate from the curated benchmark below.
- [x] Run and publish a live 500-case-per-model synthetic comparison; see [results](../results/benchmark500-v1/README.md).
- [ ] Agree on a real use case and success criteria for each task.
- [x] Select candidate public sources for all five task types; see [benchmark sources](benchmark-sources.md).
- [ ] Build 100 reviewed cases per task, including edge and adversarial cases.
- [ ] Hold out benchmark cases from prompt tuning.
- [ ] Add a human-labeled sample and calibrate any judge-based scoring against it.
- [ ] Add provider-specific settings and a dated pricing table for cost estimates.
- [x] Record code revision and image digest with every cloud run.

**Acceptance:** each selected model completes 500 cases; every case is accounted for; the report contains per-task scores, error rate, latency, token usage, and reviewed failure examples.

## Milestone 3: Cloud Run

- [x] Create the Google Cloud project `evalframe-rithik-2026` and link billing for the deployment.
- [x] Create a dedicated, unprivileged `evalframe-job` service account.
- [x] Configure a dedicated OpenRouter key with a $4 monthly credit limit and a separate $5/month Google Cloud alert budget. The Google Cloud alert is not a hard cap.
- [x] Add per-case Cloud Storage checkpoints, restore, and result/MLflow export in the application.
- [x] Configure Artifact Registry, Cloud Storage, and Secret Manager after linking billing and creating the budget.
- [x] Deploy the evaluator image as a Cloud Run Job with a dedicated service account.
- [x] Run a 20-case-per-model cloud smoke test with zero request errors.
- [x] Finish and review the [500-case-per-model cloud benchmark](../results/cloud-benchmark500-v1/README.md): both models completed all cases with zero request errors.
- [ ] Set provider request limits and a run-level spending limit before the full run.

The local and Cloud Run 500-case-per-model runs and the Cloud Run smoke test are complete; see [Cloud Run operations](cloud-run.md).

**Acceptance:** a fresh Cloud Run Job execution produces a durable MLflow comparison and downloadable case-level report; interrupted execution can resume without losing completed results. No live run starts unless its projected spend fits within the remaining monthly budget.
