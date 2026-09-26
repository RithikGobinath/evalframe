"""Offline checks for all published EvalFrame experiments."""

from __future__ import annotations

import json
import math
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_injection import compare
from scripts.analyze_public_benchmark import analyze
from scripts.analyze_retrieval_injection_v2 import analyze as analyze_retrieval_v2
from evalframe.runner import summarize


def main() -> None:
    public_dir = ROOT / "results" / "public-benchmark500-v1"
    actual_public = analyze(
        ROOT / "data" / "public500-v1.jsonl",
        ROOT / "prompts" / "public-v1.toml",
        public_dir,
    )
    expected_public = json.loads((public_dir / "paired-analysis.json").read_text(encoding="utf-8"))
    if actual_public != expected_public:
        raise ValueError("Public paired analysis differs from published artifact")
    injection_dir = ROOT / "results" / "prompt-injection-40-v1"
    actual_injection = compare(ROOT / "data" / "injection40-v1.jsonl", injection_dir, injection_dir)
    expected_injection = json.loads((injection_dir / "comparison.json").read_text(encoding="utf-8"))
    if actual_injection != expected_injection:
        raise ValueError("Injection comparison differs from published artifact")
    for phase in ("baseline", "mitigated"):
        prompt = ROOT / "prompts" / f"injection-{phase}-v1.toml"
        manifest = json.loads((injection_dir / f"{phase}-manifest.json").read_text(encoding="utf-8"))
        if hashlib.sha256(prompt.read_bytes()).hexdigest() != manifest["prompt_sha256"]:
            raise ValueError(f"{phase} prompt differs from published manifest")
    usage = json.loads((injection_dir / "key-usage.json").read_text(encoding="utf-8"))
    if not math.isclose(usage["after_usd"] - usage["before_usd"], usage["delta_usd"], abs_tol=1e-9):
        raise ValueError("Published OpenRouter usage delta does not reconcile")
    retrieval_dir = ROOT / "results" / "retrieval-injection-v2"
    actual_retrieval = analyze_retrieval_v2(
        ROOT / "data" / "retrieval-injection-v2.jsonl",
        retrieval_dir,
        retrieval_dir,
        ROOT / "prompts" / "retrieval-v2-baseline.toml",
        ROOT / "prompts" / "retrieval-v2-mitigated.toml",
    )
    expected_retrieval = json.loads((retrieval_dir / "comparison.json").read_text(encoding="utf-8"))
    if actual_retrieval != expected_retrieval:
        raise ValueError("Second injection comparison differs from published artifact")
    for phase in ("baseline", "mitigated"):
        manifest = json.loads((retrieval_dir / f"{phase}-manifest.json").read_text(encoding="utf-8"))
        saved_summary = json.loads((retrieval_dir / f"{phase}-summary.json").read_text(encoding="utf-8"))
        if set(saved_summary) != set(manifest["models"]):
            raise ValueError(f"Second injection {phase} summary has different models")
        for model in manifest["models"]:
            filename = f"{phase}-{model.split('/')[-1]}.jsonl"
            rows = [json.loads(line) for line in (retrieval_dir / filename).read_text(encoding="utf-8").splitlines()]
            computed = summarize(rows)
            for metric, value in saved_summary[model].items():
                if metric not in computed or not math.isclose(computed[metric], value, rel_tol=1e-12, abs_tol=1e-9):
                    raise ValueError(f"Second injection {phase} summary mismatch: {model} {metric}")
    retrieval_usage = json.loads((retrieval_dir / "key-usage.json").read_text(encoding="utf-8"))
    if not math.isclose(
        retrieval_usage["after_usd"] - retrieval_usage["before_usd"],
        retrieval_usage["delta_usd"], abs_tol=1e-9,
    ):
        raise ValueError("Second injection OpenRouter usage delta does not reconcile")
    print("Verified: 500 public cases per model, both 40-case injection experiments, hashes, summaries, and paired comparisons.")


if __name__ == "__main__":
    main()
