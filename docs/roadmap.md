# Build roadmap

## Milestone 1: Pilot harness — in progress

- [x] Define and validate a versioned case schema.
- [x] Add 20 synthetic cases across five task types.
- [x] Add OpenAI and Claude adapters, deterministic scorers, CLI, and MLflow logging.
- [x] Add a Dockerfile and offline tests.
- [ ] Run paid API smoke tests against chosen model IDs.
- [ ] Review pilot score disagreements and improve prompts/rubrics.

## Milestone 2: Credible 500-case benchmark

- [ ] Agree on a real use case and success criteria for each task.
- [ ] Build 100 reviewed cases per task, including edge and adversarial cases.
- [ ] Hold out benchmark cases from prompt tuning.
- [ ] Add a human-labeled sample and calibrate any judge-based scoring against it.
- [ ] Add provider-specific settings and a dated pricing table for cost estimates.
- [ ] Record code revision and image digest with every run.

**Acceptance:** each selected model completes 500 cases; every case is accounted for; the report contains per-task scores, error rate, latency, token usage, and reviewed failure examples.

## Milestone 3: Cloud Run

- [ ] Configure a Google Cloud project, billing, Artifact Registry, Cloud Storage, and Secret Manager.
- [ ] Deploy an authenticated remote MLflow service backed by Cloud SQL PostgreSQL and Cloud Storage.
- [ ] Add Cloud Storage checkpoints and resume behavior for job retries.
- [ ] Deploy the evaluator image as a Cloud Run Job with a dedicated service account.
- [ ] Run a 20-case cloud smoke test, then a 500-case benchmark.
- [ ] Set provider request limits and a run-level spending limit before the full run.

**Acceptance:** a fresh Cloud Run Job execution produces a durable MLflow comparison and downloadable case-level report; interrupted execution can resume without losing completed results.
