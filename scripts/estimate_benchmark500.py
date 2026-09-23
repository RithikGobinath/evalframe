"""Offline planning estimate for the pinned 500-case model comparison.

Prices are dated assumptions, not a live quote or a dollar enforcement mechanism.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from evalframe.cases import load_cases
from evalframe.prompts import load_prompts


ROOT = Path(__file__).resolve().parents[1]
PRICES_PER_MILLION = {
    "openai/gpt-6-luna": (0.10, 0.50),
    "anthropic/claude-haiku-4.5": (1.00, 5.00),
}


def estimate(dataset: Path, prompt_file: Path, input_reserve: int, output_cap: int) -> dict[str, float]:
    cases, _ = load_cases(dataset)
    prompts = load_prompts(prompt_file)
    if input_reserve < 1 or output_cap < 1:
        raise ValueError("token limits must be positive")
    if any(not (case.input + prompts.systems[case.task_type]).isascii() for case in cases):
        raise ValueError("this byte-based planning estimate requires ASCII prompts")
    max_prompt_bytes = max(
        len(case.input.encode("ascii")) + len(prompts.systems[case.task_type].encode("ascii"))
        for case in cases
    )
    if max_prompt_bytes + 256 > input_reserve:
        raise ValueError("input reserve is too small for the longest prompt plus protocol headroom")
    estimates = {
        model: len(cases) * (input_reserve * input_price + output_cap * output_price) / 1_000_000
        for model, (input_price, output_price) in PRICES_PER_MILLION.items()
    }
    estimates["combined"] = sum(estimates.values())
    estimates["combined_with_2x_margin"] = 2 * estimates["combined"]
    return estimates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "benchmark500.jsonl")
    parser.add_argument("--prompt", type=Path, default=ROOT / "prompts" / "baseline.toml")
    parser.add_argument("--input-reserve", type=int, default=1024)
    parser.add_argument("--output-cap", type=int, default=512)
    parser.add_argument("--credit-balance", type=float)
    args = parser.parse_args()
    estimates = estimate(args.dataset, args.prompt, args.input_reserve, args.output_cap)
    for model, cost in estimates.items():
        print(f"{model}: ${cost:.4f}")
    if args.credit_balance is not None:
        print(f"credit_balance: ${args.credit_balance:.2f}")
        if estimates["combined_with_2x_margin"] > args.credit_balance:
            raise SystemExit("Planning margin exceeds the supplied credit balance; do not start the run.")
    print("Planning only. Verify current model prices and the OpenRouter key limit before paid calls.")


if __name__ == "__main__":
    main()
