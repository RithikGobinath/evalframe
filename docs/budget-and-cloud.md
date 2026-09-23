# Budget and cloud status

The project `evalframe-rithik-2026` has been created in Google Cloud. **Billing is not linked**, and no Cloud Run job, Cloud SQL instance, storage bucket, model API call, or other paid resource has been created for this project.

The requested operating limit is $5 per month. Treat it as a combined limit across Google Cloud and model APIs, including OpenRouter, unless the owner specifies otherwise. Keep Google Cloud billing unlinked. Free OpenRouter models may be used locally within their rate limits; paid models need an explicit check of credits and limits before use.

## Spending controls before live runs

1. In the OpenAI API project settings, set a monthly **hard spend limit**, with enforcement enabled. A spend alert alone does not stop requests. Leave headroom because OpenAI says enforcement is not instantaneous.
2. In Claude Console → Settings → Billing, set a monthly spend limit below the desired Claude allocation. Use a dedicated workspace and workspace limit if available for this account.
3. In Google Cloud Billing, check whether the Preview **spend cap budget** is available for this project and Cloud Run. Its cap is per eligible service, not across all Google Cloud charges, and ongoing storage can continue accruing charges. An alerts-only budget is not a cap.
4. Run only a two-case API smoke test first. Record observed token use and billed cost before sizing a 500-case run. Choose models based on a current price check, and do not start the full benchmark if its projected maximum would breach the remaining monthly budget.

For OpenRouter specifically, use a dedicated key with a monthly limit below the remaining budget, disable auto recharge, and check the model's current price. Its free plan has API access and free models, but no budget controls. OpenRouter's terms state a $5 minimum credit purchase. With a strict **under $5 total cash outlay**, stay on free models unless credits already exist; a new paid top-up does not meet that strict ceiling. See [OpenRouter setup](openrouter-under-5.md).

An exact $5 ceiling across all three vendors cannot be guaranteed by Google Cloud budget alerts or by this application alone. With a strict no-overage requirement, keep Google Cloud billing unlinked and perform only local/offline validation until the owner accepts the available controls.

## Cloud architecture under a small budget

The earlier proposal to host a permanent MLflow service backed by Cloud SQL is deferred. It would introduce continuously running database costs. The lower-cost design is one Cloud Run Job per benchmark, with local MLflow SQLite tracking during the job and a final export of its database, artifacts, and case-level results to Cloud Storage. The job should have no minimum instances and should exit after processing. Cloud Storage checkpointing and export have not been implemented yet; do not deploy the current image for a production benchmark.

Once billing and spend controls are in place, configure Secret Manager, a dedicated service account, a small Cloud Storage bucket in an eligible US region, Artifact Registry, and a Cloud Run Job. Use one job task and conservative concurrency at first. Re-evaluate fixed costs and free-tier terms before creating any resource.

## Source documentation

- [OpenAI spend limits](https://developers.openai.com/api/docs/guides/spend-limits)
- [Claude API spend limits](https://platform.claude.com/docs/en/api/rate-limits)
- [Google Cloud spend cap budgets and limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)
- [Google Cloud Storage pricing and free tier](https://cloud.google.com/storage/pricing)
- [OpenRouter pricing and free plan](https://openrouter.ai/pricing)
- [OpenRouter credit purchase terms](https://openrouter.ai/terms)
