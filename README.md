# EvalFrame

EvalFrame runs versioned JSONL datasets against OpenAI and Claude models, directly or through OpenRouter, applies transparent task-specific scorers, and records each comparison in MLflow. The repository contains a **20-case pilot** and a **500-case synthetic throughput dataset**. The synthetic dataset has been run locally and on Cloud Run; a curated public-source benchmark is still planned.

## What works now

- Five task types: classification, structured extraction, grounded question answering, summarization, and instruction following.
- Async OpenAI Responses API, Anthropic Messages API, and OpenRouter Chat Completions adapters.
- Case-level results, token usage, latency, errors, and resumable local checkpoints.
- MLflow parent comparison run with one child run per model.
- Dataset and prompt hashes to guard against accidentally resuming with changed inputs.
- A Docker image suitable for a Cloud Run Job.

The pilot's summarization score checks required and forbidden phrases. It is a **phrase-coverage proxy**, not a general measure of summary quality. The pilot examples are synthetic and intentionally easy; they must be replaced or supplemented with representative, reviewed cases before model claims are made.

The [500-case run guide](docs/500-case-run.md) explains the synthetic dataset, cost estimate, $4 monthly OpenRouter key cap, and local run sequence. The dataset has 100 cases per task and passes an offline end-to-end harness check. The [live results](results/benchmark500-v1/README.md) cover 500 cases each for GPT-6 Luna and Claude Haiku 4.5, with no API errors.

For the full 500-case run, the selected candidate sources are [Databricks Dolly 15k and Google IFEval](docs/benchmark-sources.md). Source-specific scoring and case review are the next dataset milestone.

`docs/ci-workflow.yml` is the GitHub Actions template. It can be moved to `.github/workflows/ci.yml` after the GitHub authorization used for pushing has `workflow` permission.

## Local setup

Use Python 3.11 or newer:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
evalframe validate --dataset data/pilot.jsonl --prompt prompts/baseline.toml
pytest
```

Set `OPENROUTER_API_KEY` for OpenRouter, or the native `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` for direct calls. Do not commit keys or paste them into issues.

For one key that can route to both model families, create a key in the [OpenRouter key dashboard](https://openrouter.ai/settings/keys). For a strict total spend below $5, use free model IDs and do not purchase credits yet. Paid model access may require OpenRouter's minimum $5 credit purchase. If you already have credits and choose to run paid models, turn off auto recharge and give this key a monthly spending limit below your remaining budget. See [the OpenRouter setup guide](docs/openrouter-under-5.md).

In PowerShell, enter the key into a masked prompt for the current terminal session:

```powershell
$routerSecret = Read-Host "OpenRouter API key" -AsSecureString
$env:OPENROUTER_API_KEY = [System.Net.NetworkCredential]::new("", $routerSecret).Password
```

In **Git Bash**, use the Bash prompt and run the executable inside the existing virtual environment directly; no activation is needed:

```bash
read -r -s -p "OpenRouter API key: " OPENROUTER_API_KEY; echo
export OPENROUTER_API_KEY
./.venv/Scripts/evalframe.exe validate --dataset data/pilot.jsonl --prompt prompts/baseline.toml
./.venv/Scripts/evalframe.exe run --dataset data/pilot.jsonl --prompt prompts/baseline.toml \
  --model openrouter:google/gemma-4-31b-it:free \
  --max-cases 2 --max-output-tokens 128 --concurrency 1 --run-id smoke-gemma
```

Run a small diagnostic using the currently free [Gemma 4 31B endpoint](https://openrouter.ai/google/gemma-4-31b-it:free). Check that the model still shows **Free** before running, since availability and pricing can change:

```powershell
evalframe run --dataset data/pilot.jsonl --prompt prompts/baseline.toml `
  --model openrouter:google/gemma-4-31b-it:free --max-cases 2 `
  --max-output-tokens 128 --concurrency 1 --run-id smoke-gemma
```

To compare Claude and GPT with an existing paid credit balance, use exact model IDs from the OpenRouter catalog and repeat `--model`, keeping `--max-cases 2` for the first test. A ChatGPT or Claude chat subscription does not fund these API calls.

### Direct provider keys

Create an OpenAI API key in the [OpenAI API dashboard](https://platform.openai.com/api-keys) and a Claude key in [Claude Console → Settings → API keys](https://console.anthropic.com/). In PowerShell, the following prompts mask what you type and set the keys for the current terminal session:

```powershell
$openaiSecret = Read-Host "OpenAI API key" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new("", $openaiSecret).Password
$claudeSecret = Read-Host "Claude API key" -AsSecureString
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new("", $claudeSecret).Password
```

Set provider hard spend limits before any paid call; see [budget and cloud status](docs/budget-and-cloud.md). Then a small live diagnostic run is:

```powershell
evalframe run --dataset data/pilot.jsonl --prompt prompts/baseline.toml `
  --model openai:YOUR_MODEL_ID --max-cases 2 --run-id smoke-openai
```

Run both providers on the same cases by repeating `--model`:

```powershell
evalframe run --dataset data/pilot.jsonl --prompt prompts/baseline.toml `
  --model openai:YOUR_OPENAI_MODEL_ID `
  --model anthropic:YOUR_CLAUDE_MODEL_ID `
  --run-id pilot-v1
```

By default, MLflow writes metadata to a local `mlflow.db` SQLite database for development. Set `MLFLOW_TRACKING_URI` or pass `--tracking-uri` for a remote server. `--no-mlflow` is for diagnostic runs only. Results are saved under `runs/<run-id>/`; rerunning with the same ID and unchanged inputs skips completed cases. Errors are recorded with score zero and included in the completion rate. Failed cases also remain in the checkpoint so that an explicit new run ID is needed to retry them.

## Dataset format

Each line is a JSON object. IDs must be unique. Task-specific `expected` values are validated before any model calls.

```json
{"case_id":"cls-001","task_type":"classification","input":"Categories: billing, technical. Ticket: I was charged twice.","expected":"billing","tags":["easy"]}
```

For extraction, `expected` is a JSON object. For summarization, it contains `required_phrases` and optional `forbidden_phrases`. For instruction following, it can contain `contains_all`, `contains_none`, `max_words`, and `valid_json`. See `data/pilot.jsonl` for examples. Avoid storing personal or confidential data in datasets until the MLflow server and artifact store access controls have been configured.

## Scoring and comparison

- Classification: case-insensitive exact category match.
- Extraction: valid JSON plus matching fields, with extra fields reducing the score.
- Q&A: normalized token F1, with exact match also recorded.
- Summarization: required phrase coverage; any forbidden phrase makes the score zero.
- Instruction following: pass only if every specified constraint passes.

`mean_score` includes errors as zero. Always inspect per-task scores and case-level failures; the pilot's overall mean is not a calibrated quality index. API settings are currently limited to model ID and maximum output tokens. Provider-specific settings and cost estimates are future work.

## Deployment path

The evaluator image's entrypoint is `evalframe`. Google Cloud project `evalframe-rithik-2026` has a finite **Cloud Run Job** that exports case results and MLflow data to Cloud Storage. The `--gcs-bucket` option saves each completed case for job retries. The 20-case-per-model smoke test and [500-case-per-model cloud benchmark](results/cloud-benchmark500-v1/README.md) both completed with zero request errors. A separate $5/month Google Cloud budget **alerts** on spending but does not cap it. See [Cloud Run operations](docs/cloud-run.md), [budget status](docs/budget-and-cloud.md), and [project roadmap](docs/roadmap.md).

## Security notes

The code reads keys only from environment variables and never writes them to MLflow or results. Provider exception messages are excluded from case records because they can contain prompt text. MLflow artifacts include the dataset, prompt file, and model responses, so restrict access and review datasets before running them. Use separate service accounts and least-privilege access for the evaluator and tracking server.
