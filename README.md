# EvalFrame

EvalFrame runs a versioned JSONL dataset against OpenAI and Claude models, applies transparent task-specific scorers, and records each comparison in MLflow. This repository currently contains a **20-case pilot**. The planned 500-case benchmark and Cloud Run deployment are not yet complete.

## What works now

- Five task types: classification, structured extraction, grounded question answering, summarization, and instruction following.
- Async OpenAI Responses API and Anthropic Messages API adapters.
- Case-level results, token usage, latency, errors, and resumable local checkpoints.
- MLflow parent comparison run with one child run per model.
- Dataset and prompt hashes to guard against accidentally resuming with changed inputs.
- A Docker image suitable for a Cloud Run Job.

The pilot's summarization score checks required and forbidden phrases. It is a **phrase-coverage proxy**, not a general measure of summary quality. The pilot examples are synthetic and intentionally easy; they must be replaced or supplemented with representative, reviewed cases before model claims are made.

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

Set `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` in your environment. Do not commit keys or paste them into issues.

Create an OpenAI API key in the [OpenAI API dashboard](https://platform.openai.com/api-keys) and a Claude key in [Claude Console → Settings → API keys](https://console.anthropic.com/). In PowerShell, the following prompts mask what you type and set the keys for the current terminal session:

```powershell
$openaiSecret = Read-Host "OpenAI API key" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new("", $openaiSecret).Password
$claudeSecret = Read-Host "Claude API key" -AsSecureString
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new("", $claudeSecret).Password
```

Then a small live diagnostic run is:

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

The evaluator image's entrypoint is `evalframe`. Build it and deploy it as a **Cloud Run Job** with a single task initially. Pass the `run` command arguments to the job. Store provider API keys in Secret Manager and supply them to the job's service account. Use a remote MLflow server with a persistent PostgreSQL backend and Cloud Storage artifact store. Local `runs/` checkpoints are ephemeral on Cloud Run; durable Cloud Storage checkpoints must be added before relying on automatic job retries. See [the project roadmap](docs/roadmap.md).

## Security notes

The code reads keys only from environment variables and never writes them to MLflow or results. Provider exception messages are excluded from case records because they can contain prompt text. MLflow artifacts include the dataset, prompt file, and model responses, so restrict access and review datasets before running them. Use separate service accounts and least-privilege access for the evaluator and tracking server.
