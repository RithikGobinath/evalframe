# OpenRouter setup with a strict $5 total limit

1. Leave Google Cloud billing disabled. Local Python, local MLflow, and the existing pilot dataset cost nothing in cloud fees.
2. Sign in to [OpenRouter](https://openrouter.ai/), visit [Keys](https://openrouter.ai/settings/keys), and create a dedicated `evalframe-local` key. Never put the key in a dataset, `.env` file committed to Git, issue, or chat.
3. For **less than $5 total cash spent this month**, select a model marked free in the [current free catalog](https://openrouter.ai/collections/free-models/) and do not buy credits or enable auto recharge. The free plan lists 50 requests per day and does not offer budget controls. Free models generally will not give a direct Claude-versus-GPT benchmark.
4. In a PowerShell terminal in the repository, install the project if needed and set the key only for that terminal:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -e ".[dev]"
   $routerSecret = Read-Host "OpenRouter API key" -AsSecureString
   $env:OPENROUTER_API_KEY = [System.Net.NetworkCredential]::new("", $routerSecret).Password
   ```

5. Check that the [Gemma 4 31B endpoint](https://openrouter.ai/google/gemma-4-31b-it:free) still shows **Free**, then run two cases first. The `--no-mlflow` flag is unnecessary: local MLflow works without a hosted service.

   ```powershell
   evalframe validate --dataset data/pilot.jsonl --prompt prompts/baseline.toml
   evalframe run --dataset data/pilot.jsonl --prompt prompts/baseline.toml `
     --model openrouter:google/gemma-4-31b-it:free --max-cases 2 `
     --max-output-tokens 128 --concurrency 1 --run-id smoke-gemma
   ```

6. Inspect `runs/smoke-gemma/summary.json` and the [OpenRouter activity page](https://openrouter.ai/activity). Advance to 20 pilot cases only after the first run succeeds. The full 500-case benchmark dataset and durable Cloud Run workflow still need to be built.

The first live smoke run with `nvidia/nemotron-3.5-lightning:free` reached OpenRouter successfully but produced long reasoning text. Both classification outputs hit the 128-token limit and scored zero. A follow-up with `google/gemma-4-31b-it:free` returned HTTP 429 for both cases, so its output quality has not yet been measured. Check [OpenRouter activity](https://openrouter.ai/activity) and your account's free-model limits before retrying; a 429 can reflect account or provider capacity, and the case files do not identify which. The harness now makes no automatic OpenRouter retries and stops queued cases on a 429.

### Git Bash on Windows

If your prompt says `MINGW64`, use these commands from the repository folder. The virtual environment's executable can run directly, so activation is unnecessary. The `read` command hides the key as you type it; do not paste the key into the command itself.

```bash
read -r -s -p "OpenRouter API key: " OPENROUTER_API_KEY; echo
export OPENROUTER_API_KEY
./.venv/Scripts/evalframe.exe validate --dataset data/pilot.jsonl --prompt prompts/baseline.toml
./.venv/Scripts/evalframe.exe run --dataset data/pilot.jsonl --prompt prompts/baseline.toml \
  --model openrouter:google/gemma-4-31b-it:free \
  --max-cases 2 --max-output-tokens 128 --concurrency 1 --run-id smoke-gemma
```

## If you already have paid OpenRouter credits

Use a dedicated API key with a **monthly limit** below the part of the $5 budget still available, and switch off auto recharge. The management API supports monthly key limits; check the dashboard's current controls when creating your key. Start with two cases and check actual usage before increasing case count. OpenRouter's Standard plan lists a 5.5% platform fee. Recheck exact model prices and available balance before a full benchmark.

For two-model comparison, supply two exact model slugs in one run, for example `openrouter:openai/MODEL_SLUG` and `openrouter:anthropic/MODEL_SLUG`. A `--max-cases 2` run with two models can make up to four model requests. The OpenRouter adapter has no automatic retries, and HTTP 429 stops further queued cases. The runner itself does not enforce a dollar cap; the provider account/key limit is essential for paid use.

ChatGPT and Claude chat subscriptions are billed separately from their API products. They cannot be entered as an API key or used to pay OpenRouter API charges.

Sources: [OpenRouter quickstart](https://openrouter.ai/docs/quickstart), [pricing](https://openrouter.ai/pricing), [credit terms](https://openrouter.ai/terms), [API key monthly limits](https://openrouter.ai/docs/api/api-reference/api-keys/create-a-new-api-key), [OpenAI billing separation](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform), and [Claude billing separation](https://support.claude.com/en/articles/9876003-i-have-a-paid-claude-subscription-pro-max-team-or-enterprise-plans-why-do-i-have-to-pay-separately-to-use-the-claude-api-and-console).
