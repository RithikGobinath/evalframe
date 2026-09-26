"""Offline checks for both published EvalFrame experiments."""

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
    print("Verified: 500 public cases per model, 40 injection cases per model and prompt, hashes, summaries, and paired comparisons.")


if __name__ == "__main__":
    main()
