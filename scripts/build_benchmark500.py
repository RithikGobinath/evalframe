"""Build the deterministic, synthetic 500-case throughput benchmark.

This dataset exercises the harness. It is not a measure of production quality.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "benchmark500.jsonl"
NAMES = ("Ava", "Ben", "Cora", "Dev", "Eli", "Faye", "Gus", "Hana", "Iris", "Jules")
CITIES = ("Austin", "Boston", "Chicago", "Denver", "Eugene", "Fresno", "Galveston", "Helena", "Ithaca", "Juneau")
ITEMS = ("folders", "pens", "mugs", "lamps", "notebooks", "chargers", "headsets", "posters", "markers", "calendars")


def _case(case_id: str, task_type: str, prompt: str, expected: object, reference: str, *tags: str) -> dict:
    return {
        "case_id": case_id,
        "task_type": task_type,
        "input": prompt,
        "expected": expected,
        "reference_output": reference,
        "source": "evalframe-synthetic-v1",
        "tags": ["synthetic", *tags],
    }


def build() -> list[dict]:
    cases: list[dict] = []
    for i in range(100):
        number = i + 1
        name = NAMES[i % len(NAMES)]
        city = CITIES[(i // 10) % len(CITIES)]
        item = ITEMS[(i * 3) % len(ITEMS)]
        order_id = f"EF-{number:04d}"
        amount = f"${12 + i}.50"
        date = f"2026-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}"
        common_tags = (f"template-{i % 5}",)

        label = ("billing", "technical", "account")[i % 3]
        issue = {
            "billing": (
                f"{name} says order {order_id} was charged twice, though sign-in works.",
                f"The invoice for {order_id} lists {amount} twice; the app otherwise works for {name}.",
            ),
            "technical": (
                f"{name} can sign in and pay, but the upload button freezes on order {order_id}.",
                f"The billing page opens, but the download button crashes for {name} on {order_id}.",
            ),
            "account": (
                f"{name} can pay and upload, but needs to change the email on account {order_id}.",
                f"The app works for {name}; they need to reset the password for account {order_id}.",
            ),
        }[label][(i // 3) % 2]
        cases.append(_case(
            f"cls-{number:03d}", "classification",
            f"Categories: billing, technical, account. Ticket: {issue}", label, label, *common_tags,
        ))

        record = (
            f"Shipping note {order_id}: {name} ordered {i % 5 + 1} {item} for {amount}. "
            f"Destination: {city}. Dispatch date: {date}."
        )
        extract_variants = (
            ({"name": name, "order_id": order_id}, "name and order_id"),
            ({"city": city, "date": date}, "city and date"),
            ({"item": item, "total": amount}, "item and total"),
            ({"name": name, "city": city, "total": amount}, "name, city, and total"),
        )
        fields, field_names = extract_variants[i % len(extract_variants)]
        cases.append(_case(
            f"ext-{number:03d}", "extraction",
            f"Return only a JSON object with keys {field_names}. Use strings for all values. Text: {record}",
            fields, json.dumps(fields, separators=(",", ":")), *common_tags,
        ))

        context = (
            f"Order {order_id} belongs to {name}. It contains {i % 5 + 1} {item}. "
            f"It ships to {city} on {date} and costs {amount}."
        )
        qa_variants = (
            ("Who owns the order?", name),
            ("Which city will receive the order?", city),
            ("What is the order ID?", order_id),
            ("When does it ship?", date),
            ("What is its total cost?", amount),
        )
        question, answer = qa_variants[i % len(qa_variants)]
        cases.append(_case(
            f"qa-{number:03d}", "qa", f"Context: {context} Question: {question}",
            answer, answer, *common_tags,
        ))

        event = (
            f"Operations update: order {order_id} for {item} will ship to {city} on {date}. "
            f"The earlier draft listed a different date, but this update is final."
        )
        summary = f"Order {order_id} for {item} will ship to {city} on {date}."
        cases.append(_case(
            f"sum-{number:03d}", "summarization",
            f"Summarize the final operations update in one sentence. Include the exact order ID, city, and date. {event}",
            {"required_phrases": [order_id, city, date], "forbidden_phrases": ["cancelled"]},
            summary, *common_tags,
        ))

        code = f"Q-{number:03d}"
        instruction_variants = (
            (
                f"Reply in at most four words. Include READY and {code}. Do not use PENDING.",
                {"contains_all": ["READY", code], "contains_none": ["PENDING"], "max_words": 4},
                f"READY {code}",
            ),
            (
                f"Return only a valid JSON object containing status READY and code {code}. Do not write prose.",
                {"contains_all": ["READY", code], "valid_json": True},
                json.dumps({"status": "READY", "code": code}, separators=(",", ":")),
            ),
            (
                f"Write exactly the words CONFIRMED and {code}, in that order. Do not use CANCELLED.",
                {"contains_all": ["CONFIRMED", code], "contains_none": ["CANCELLED"], "max_words": 2},
                f"CONFIRMED {code}",
            ),
            (
                f"Acknowledge ticket {code} in at most five words. Include RECEIVED; do not use REJECTED.",
                {"contains_all": ["RECEIVED", code], "contains_none": ["REJECTED"], "max_words": 5},
                f"RECEIVED {code}",
            ),
        )
        instruction, constraints, reference = instruction_variants[i % len(instruction_variants)]
        cases.append(_case(
            f"if-{number:03d}", "instruction_following",
            instruction, constraints, reference, *common_tags,
        ))
    return cases


def main() -> None:
    cases = build()
    OUTPUT.write_text(
        "".join(json.dumps(case, ensure_ascii=True, separators=(",", ":")) + "\n" for case in cases),
        encoding="utf-8",
    )
    print(f"Wrote {len(cases)} cases to {OUTPUT}")


if __name__ == "__main__":
    main()
