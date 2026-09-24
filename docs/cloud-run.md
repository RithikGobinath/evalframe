# Cloud Run deployment plan

**Status (September 24, 2026):** The application is prepared for a one-task Cloud Run Job, but **nothing has been deployed**. Google Cloud project `evalframe-rithik-2026` has billing disabled. The unprivileged service account `evalframe-job@evalframe-rithik-2026.iam.gserviceaccount.com` was created. Google Cloud rejected activation of the Run, Build, Registry, and Secret Manager APIs because billing is disabled. No bucket, secret, image, or job exists. The owner's $5 monthly cash limit was already used for an OpenRouter credit purchase this month, so billing remains disabled until the owner approves a different spending arrangement. The machine preparing this project has no Docker executable; the deployment uses Cloud Build after billing is resolved.

## Job design

- Region: `us-central1`; one task, one vCPU, 1 GiB memory, no automatic task retries, and a finite task timeout.
- OpenRouter key: one dedicated key with its existing $4 monthly provider limit, injected through Secret Manager. Never put the key in the image, command arguments, a GitHub secret, or a tracked file.
- One Cloud Storage bucket holds a manifest, one object per completed case, the final JSONL files, summary, and a snapshot of the local MLflow SQLite database plus artifacts. A retry with the same run ID restores completed cases and checks the dataset, prompt, model list, output limit, code revision, and image digest before calling a model.
- A 20-case smoke run (20 cases per model) comes before the 500-case-per-model run. Use different run IDs for smoke and full runs. Do not execute two jobs with the same run ID simultaneously.
- The image runs as a non-root user. The job service account has access only to its results bucket and the OpenRouter secret. Do not assign project-wide Editor or Owner roles to it.

## Cost gate

Google's current free allowances include [Cloud Run Jobs compute](https://cloud.google.com/run/pricing), [Cloud Storage in eligible US regions](https://cloud.google.com/storage/pricing), [Artifact Registry storage](https://cloud.google.com/artifact-registry/pricing), [Secret Manager](https://cloud.google.com/secret-manager/pricing), and [Cloud Build](https://cloud.google.com/build/pricing). These allowances are shared at the billing-account level and can be exhausted by other projects. Google [spend-cap budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps) are a preview feature; a Cloud Run cap does not cover Storage, Registry, Secret Manager, or Build, and enforcement can overshoot. An alerts-only budget does not stop charges. **Neither the free tier nor a budget is a hard $5 account-wide ceiling.**

Before billing is linked, decide how any possible Google Cloud charge fits the $5 total monthly cash limit. Keep OpenRouter auto top-up off. Verify the key's current monthly limit and remaining balance before every run. The model API spend is separate from Google Cloud charges.

## Deployment steps after the cost gate

These are the reviewed settings for deployment; **they have not been run**.

1. Link an approved billing account and verify that `gcloud billing projects describe evalframe-rithik-2026 --format="value(billingEnabled)"` returns `True`. Configure budget alerts and, if available, a Cloud Run spend cap. Review billing-account usage of the shared free tiers.
2. Enable `run.googleapis.com`, `cloudbuild.googleapis.com`, `artifactregistry.googleapis.com`, and `secretmanager.googleapis.com` on this project. Create a private Standard Cloud Storage bucket in `us-central1` and a Docker Artifact Registry repository in the same region. Choose a globally unique bucket name.
3. Use the existing dedicated service account `evalframe-job`. Grant it `roles/storage.objectAdmin` **on the results bucket only** and `roles/secretmanager.secretAccessor` **on the OpenRouter secret only**. Add the existing OpenRouter key to Secret Manager from a masked local input, never from chat.
4. Build from the repository Dockerfile with Cloud Build. Tag the image with the Git commit, resolve its immutable SHA-256 digest in Artifact Registry, and deploy the Cloud Run Job pinned to that digest. Set `EVALFRAME_CODE_REVISION` and `EVALFRAME_IMAGE_DIGEST` to those exact values. Configure one task, zero retries, 1 CPU, 1 GiB RAM, a 60-minute timeout, and the dedicated service account. Set `OPENROUTER_API_KEY` from the secret.
5. Configure the job arguments below for the smoke run, execute it once, then inspect its execution status, OpenRouter key usage, Cloud Storage objects, and MLflow export. The job's own report must show 20 cases per model and no errors before changing the arguments to the full run.

The deployment commands below are for PowerShell after the cost gate is resolved. Run each stage separately and stop on any error. Set a globally unique bucket name and add the key to `evalframe-openrouter-key` in Secret Manager before deploying. The key value must be entered in Secret Manager, never in a command argument or this file.

```powershell
$projectId = 'evalframe-rithik-2026'
$region = 'us-central1'
$bucketName = 'REPLACE_WITH_UNIQUE_BUCKET_NAME'
$jobIdentity = "evalframe-job@$projectId.iam.gserviceaccount.com"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com --project=$projectId
gcloud storage buckets create "gs://$bucketName" --location=$region --default-storage-class=STANDARD --uniform-bucket-level-access --project=$projectId
gcloud artifacts repositories create evalframe --repository-format=docker --location=$region --project=$projectId
gcloud storage buckets add-iam-policy-binding "gs://$bucketName" --member="serviceAccount:$jobIdentity" --role=roles/storage.objectAdmin
gcloud secrets create evalframe-openrouter-key --replication-policy=automatic --project=$projectId
gcloud secrets add-iam-policy-binding evalframe-openrouter-key --member="serviceAccount:$jobIdentity" --role=roles/secretmanager.secretAccessor --project=$projectId

$revision = (git rev-parse HEAD).Trim()
$imageTag = "$region-docker.pkg.dev/$projectId/evalframe/evalframe:$revision"
gcloud builds submit --region=$region --tag=$imageTag --project=$projectId .
$imageInfo = gcloud artifacts docker images describe $imageTag --format=json --project=$projectId | ConvertFrom-Json
$digest = $imageInfo.image_summary.digest
if ($digest -notmatch '^sha256:[0-9a-f]{64}$') { throw 'Could not verify image digest' }
$pinnedImage = "$region-docker.pkg.dev/$projectId/evalframe/evalframe@$digest"

$jobArgs = "run,--dataset,data/benchmark500.jsonl,--prompt,prompts/baseline.toml,--model,openrouter:openai/gpt-6-luna,--model,openrouter:anthropic/claude-haiku-4.5,--max-cases,20,--max-output-tokens,512,--concurrency,2,--run-id,cloud-smoke-v1,--gcs-bucket,$bucketName"
gcloud run jobs deploy evalframe-benchmark --image=$pinnedImage --region=$region --project=$projectId --service-account=$jobIdentity --tasks=1 --max-retries=0 --task-timeout=60m --cpu=1 --memory=1Gi --set-env-vars="EVALFRAME_CODE_REVISION=$revision,EVALFRAME_IMAGE_DIGEST=$digest" --set-secrets="OPENROUTER_API_KEY=evalframe-openrouter-key:latest" --args=$jobArgs
```

The source build account may need repository write permission in a newly created project; grant it only on the `evalframe` repository if Cloud Build reports an IAM error. Check the deployed job configuration, secret version, OpenRouter key limit, and Google Cloud budget before the separate execution step:

```powershell
gcloud run jobs execute evalframe-benchmark --region=us-central1 --project=evalframe-rithik-2026 --wait
```

A repeat deployment should reuse the bucket and repository rather than recreating them.

```text
run --dataset data/benchmark500.jsonl --prompt prompts/baseline.toml
--model openrouter:openai/gpt-6-luna
--model openrouter:anthropic/claude-haiku-4.5
--max-cases 20 --max-output-tokens 512 --concurrency 2
--run-id cloud-smoke-v1 --gcs-bucket BUCKET_NAME
```

For the full run, remove `--max-cases 20` and use a new run ID such as `cloud-benchmark500-v1`. Recheck current model prices and remaining OpenRouter key balance before execution. A job retry uses the same run ID and the same image digest; after a code or prompt change, use a new run ID.

Each run is stored under `gs://BUCKET_NAME/evalframe/runs/RUN_ID/`. `artifacts/run/summary.json` and the case JSONL files are directly downloadable. `artifacts/mlflow/` holds the SQLite snapshot and MLflow artifacts. The SQLite file records paths from the job container; use the JSON summary and case files for portable review, and restore the bundle under the same `/app` layout when opening it with a local MLflow server.

## Verification before deployment

Run `python -m pytest -q`. The cloud-store tests simulate a fresh container restoring results from object storage. A container build and live Google Cloud smoke test still need to be performed after the billing decision.
