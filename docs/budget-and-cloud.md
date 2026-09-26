# Budget and cloud status

As of September 24, 2026, Google Cloud project `evalframe-rithik-2026` is linked to billing account `01B297-BF7CD4-99F6E3`. A separate **$5 monthly alert budget** named `EvalFrame $5 monthly alert` is scoped to this project, with email thresholds at 50%, 80%, and 100%. Google Cloud budget alerts can lag and **do not stop charges**. Review the project's Billing page before further cloud work.

The dedicated EvalFrame OpenRouter key was previously documented with a $4 monthly limit. On September 25, the key's read-only API reported a **$5 limit with no reset interval** and $0.518937705 cumulative usage after the [second prompt-injection experiment](../results/retrieval-injection-v2/README.md). The key configuration therefore differs from the earlier documentation; check it again before new paid runs. Auto top-up was previously turned off. OpenRouter charges are separate from Google Cloud charges. The user prefers a separate $5 monthly Google Cloud alert, which does not have to be a hard limit. Keep runs finite and check key usage and billing before new experiments.

## Current resources

- Cloud Run Job: `evalframe-benchmark` in `us-central1`, one task, zero retries, 1 vCPU, 1 GiB memory, and a 60-minute task timeout.
- Cloud Storage bucket: `gs://evalframe-rithik-2026-results`, with per-case checkpoints and exported reports/MLflow data.
- Artifact Registry repository: `us-central1-docker.pkg.dev/evalframe-rithik-2026/evalframe`.
- Secret Manager secret: `evalframe-openrouter-key`. The job reads a pinned secret version; the key value is never placed in source control or job arguments.
- Job identity: `evalframe-job@evalframe-rithik-2026.iam.gserviceaccount.com`, with object access on the results bucket and secret access on that one secret.

The synthetic 20-case-per-model smoke test and [500-case-per-model cloud benchmark](../results/cloud-benchmark500-v1/README.md), plus the public-source diagnostic and [500-case-per-model public benchmark](../results/public-benchmark500-v1/README.md), completed with zero request errors; see [Cloud Run operations](cloud-run.md) for execution details. The public benchmark uses a second finite job, `evalframe-public-benchmark`, with the same resource limits and no schedule.

The job exits after each run. MLflow uses SQLite inside the container while running, then exports its database and artifacts to Cloud Storage. There is no continuously running MLflow server or Cloud SQL instance.

## Cost controls and limits

Google Cloud's [budget documentation](https://docs.cloud.google.com/billing/docs/how-to/budgets) says an alerts-only budget does not cap spend and notifications can be delayed. [Cloud Run Jobs](https://cloud.google.com/run/pricing), [Cloud Build](https://cloud.google.com/build/pricing), [Artifact Registry](https://cloud.google.com/artifact-registry/pricing), [Secret Manager](https://cloud.google.com/secret-manager/pricing), and [Cloud Storage](https://cloud.google.com/storage/pricing) each have separate pricing and free allowances. The allowances can be shared across projects on the same billing account. A successful test run and its current alert setting do not prove that future monthly charges will remain under $5.

Use a fresh run ID for changed inputs or images. Before another paid model run, verify the OpenRouter key's remaining credit and current model prices. Keep auto top-up disabled. The Cloud Run job has no scheduled trigger and therefore incurs compute charges only when manually executed.
