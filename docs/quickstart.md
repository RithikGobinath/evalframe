# Run EvalFrame locally

EvalFrame needs Python 3.11 or newer. Validation and published-result verification make **no API calls**. A live run needs an OpenRouter key or direct OpenAI/Anthropic API keys; ChatGPT and Claude chat subscriptions do not pay for API usage.

## Install and inspect without spending

From the repository root in **PowerShell**:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\evalframe.exe validate --dataset data/public500-v1.jsonl --prompt prompts/public-v1.toml
.\.venv\Scripts\python.exe scripts/verify_published_results.py
.\.venv\Scripts\python.exe -m pytest -q
```

In **Git Bash on Windows**, use the executables in `.venv/Scripts/` directly; `Activate.ps1` is a PowerShell script and will not activate a Bash shell:

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e '.[dev]'
./.venv/Scripts/evalframe.exe validate --dataset data/public500-v1.jsonl --prompt prompts/public-v1.toml
./.venv/Scripts/python.exe scripts/verify_published_results.py
```

On macOS or Linux, create a venv with `python3.11 -m venv .venv` and use `.venv/bin/python` and `.venv/bin/evalframe` in the same commands.

## Make a small live call

Check the [current key limit and model prices](budget-and-cloud.md) first. For OpenRouter, enter the key into a masked PowerShell prompt for this terminal session:

```powershell
$routerSecret = Read-Host "OpenRouter API key" -AsSecureString
$env:OPENROUTER_API_KEY = [System.Net.NetworkCredential]::new("", $routerSecret).Password
.\.venv\Scripts\evalframe.exe run --dataset data/pilot.jsonl --prompt prompts/baseline.toml `
  --model openrouter:openai/gpt-6-luna --max-cases 2 `
  --max-output-tokens 128 --concurrency 1 --run-id my-smoke-test
Remove-Item Env:OPENROUTER_API_KEY
```

This example uses a **paid** model and calls only two cases. Choose an available model ID from the [OpenRouter catalog](https://openrouter.ai/models); availability and prices can change. Give each changed dataset, prompt, model, or output limit a new run ID. Rerunning an unchanged run ID resumes its saved cases.

In Git Bash, set the key without displaying it, run the venv executable, then clear the variable:

```bash
read -r -s -p "OpenRouter API key: " OPENROUTER_API_KEY; echo
export OPENROUTER_API_KEY
./.venv/Scripts/evalframe.exe run --dataset data/pilot.jsonl --prompt prompts/baseline.toml \
  --model openrouter:openai/gpt-6-luna --max-cases 2 \
  --max-output-tokens 128 --concurrency 1 --run-id my-smoke-test
unset OPENROUTER_API_KEY
```

For direct providers, set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` and use `--model openai:MODEL_ID` or `--model anthropic:MODEL_ID`. Repeat `--model` to compare models on identical cases. Keep API keys out of source files and issue comments.

## Where results go

Each run writes `runs/<run-id>/manifest.json`, `summary.json`, and one case JSONL file per model. MLflow records a parent comparison run and a child run for each model in the local `mlflow.db`. Dataset and prompt hashes protect a run ID from being reused with changed inputs. Cloud Run adds per-case Cloud Storage checkpoints and exports its MLflow artifacts; see [Cloud Run operations](cloud-run.md).

The case schema and scoring rules are described in the [main README](../README.md) and [public benchmark methods](public-benchmark.md). For the prompt-injection experiment, use its [frozen protocol](prompt-injection-40.md) and [published report](../results/prompt-injection-40-v1/README.md).
