# Cloud Run operations

**Status (September 25, 2026):** Two finite jobs are deployed in Google Cloud project `evalframe-rithik-2026`, region `us-central1`. `evalframe-benchmark` completed the [synthetic throughput run](../results/cloud-benchmark500-v1/README.md), and `evalframe-public-benchmark` completed the [public-source run](../results/public-benchmark500-v1/README.md). Each full run processed 500 cases per model with zero API errors. Neither job has a schedule.

The project has a separate **$5 monthly Google Cloud budget alert**, with 50%, 80%, and 100% thresholds. It is not a hard spending cap. The OpenRouter key's current read-only API reports a $5 limit with no reset interval; this differs from the earlier $4 monthly setting. See [budget details](budget-and-cloud.md).

## Synthetic job configuration

| Item | Value |
| --- | --- |
| Job | `evalframe-benchmark` |
| Region | `us-central1` |
| Results bucket | `gs://evalframe-rithik-2026-results` |
| Dataset | `data/benchmark500.jsonl` (500 synthetic cases across five task types) |
| Prompt | `prompts/baseline.toml` |
| Models | `openrouter:openai/gpt-6-luna` and `openrouter:anthropic/claude-haiku-4.5` |
| Task limits | One task, one vCPU, 1 GiB memory, 60-minute timeout, zero automatic retries |
| Service account | `evalframe-job@evalframe-rithik-2026.iam.gserviceaccount.com` |
| Image | `us-central1-docker.pkg.dev/evalframe-rithik-2026/evalframe/evalframe@sha256:481fa54d8bccdc4f4479e7c95b60fd88f6504546edd4a39ac333ebf368b835e4` |
| Code revision in manifest | `869495ffde3d58fb6cfb885f31eb61de9877a315` |

The service account has object access on the results bucket and access to the `evalframe-openrouter-key` secret. The job references a pinned Secret Manager version; never paste the key into source files, job arguments, or chat. The image was built by Cloud Build because Docker is not installed locally.

The current job arguments point to the full run ID `cloud-benchmark500-v1`. The smoke run used `cloud-smoke-v1` with `--max-cases 20`. Completed cases are saved individually under `evalframe/runs/RUN_ID/cases/`; a resumed execution with the **same run ID and unchanged inputs** restores them before sending new model requests. Do not run two executions of one run ID at the same time.

## Inspect results

Use the [Cloud Run job page](https://console.cloud.google.com/run/jobs/details/us-central1/evalframe-benchmark?project=evalframe-rithik-2026) to see executions and logs. The reports are in the results bucket:

```powershell
gcloud storage cat gs://evalframe-rithik-2026-results/evalframe/runs/cloud-smoke-v1/artifacts/run/summary.json
gcloud storage cat gs://evalframe-rithik-2026-results/evalframe/runs/cloud-benchmark500-v1/artifacts/run/summary.json
```

Each run also stores `manifest.json`, per-model case JSONL files under `artifacts/run/`, and the MLflow SQLite database plus artifacts under `artifacts/mlflow/`. The SQLite artifact paths were written inside `/app` in the job container; the JSON summary and case files are directly portable. Review individual failures before interpreting aggregate scores. This dataset proves evaluation throughput and reproducibility, not production model quality.

## Subsequent runs

Before running again, check Google Cloud billing, OpenRouter key usage, and current model pricing. Make a fresh run ID if the dataset, prompt, models, output limit, code, or image changes. The job has no schedule and only runs on manual execution:

```powershell
gcloud run jobs execute evalframe-benchmark --region=us-central1 --project=evalframe-rithik-2026 --wait
```

Cloud Run's `gcloud run jobs deploy --args` parser rejected repeated `--model` arguments. To change the model list or run ID, export the job YAML (`gcloud run jobs describe evalframe-benchmark --region=us-central1 --project=evalframe-rithik-2026 --format=export`), edit the `spec.template.spec.template.spec.containers[0].args` array, then use `gcloud run jobs replace JOB.yaml --region=us-central1 --project=evalframe-rithik-2026`. Verify the image digest, secret version, service account, one task, zero retries, and timeout after replacement. Reuse the existing bucket and repository; do not recreate them for each run.

## Verification performed

- Local suite: 19 tests passed before deployment.
- Cloud Build `b69c9692-321a-4c3c-9550-ebb5211b1534` succeeded and pushed the immutable image digest above.
- Smoke execution `evalframe-benchmark-dgmcs` finished successfully. Both models completed 20 of 20 cases with zero errors; the GCS summary and MLflow SQLite export exist.
- Full execution `evalframe-benchmark-2pdxh` completed successfully in 13 minutes 33 seconds. Each model has 500 completed cases and zero errors. The downloaded case files match the manifest's 500 IDs, and their mean scores match the summary. The MLflow SQLite export exists in Cloud Storage.

## Public-source benchmark job

The separate `evalframe-public-benchmark` job uses `data/public500-v1.jsonl` and `prompts/public-v1.toml` with the same two models. It is pinned to image digest `sha256:d514168c61408f093c7308bbaf5f19382c37d4cf78e71b83ead296d65c73efca` and code revision `416d906f69182c2e5aacda0253f1698143d71c5c`. It uses the existing service account, pinned secret version 2, bucket, one vCPU, 1 GiB memory, one task, zero retries, and 60-minute timeout. The job currently points at run ID `public-benchmark500-v1`; re-executing that ID would restore the completed checkpoints.

The diagnostic execution `evalframe-public-benchmark-7t6vd` finished 20 cases per model with zero errors. The full execution [`evalframe-public-benchmark-rrkfr`](https://console.cloud.google.com/run/jobs/executions/details/us-central1/evalframe-public-benchmark-rrkfr?project=472137125970) completed 500 cases per model with zero API errors in 18 minutes 47 seconds. The [published report](../results/public-benchmark500-v1/README.md) includes the downloaded case files and limitations. Cloud artifacts, including MLflow, are under `gs://evalframe-rithik-2026-results/evalframe/runs/public-benchmark500-v1/`. The job has no schedule.
