"""Build a reproducible 500-case benchmark from pinned public datasets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "public500-v1.jsonl"
SOURCE_MANIFEST = ROOT / "data" / "public500-v1.sources.json"
SEED = "evalframe-public500-v1"

SOURCES = {
    "dolly": {
        "name": "Databricks Dolly 15k",
        "revision": "bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a",
        "license": "CC BY-SA 3.0",
        "filename": "databricks-dolly-15k.jsonl",
        "url": "https://huggingface.co/datasets/databricks/databricks-dolly-15k/resolve/bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a/databricks-dolly-15k.jsonl",
        "sha256": "2df9083338b4abd6bceb5635764dab5d833b393b55759dffb0959b6fcbf794ec",
    },
    "ifeval": {
        "name": "Google IFEval",
        "revision": "966cd89545d6b6acfd7638bc708b98261ca58e84",
        "license": "Apache 2.0",
        "filename": "ifeval_input_data.jsonl",
        "url": "https://huggingface.co/datasets/google/IFEval/resolve/966cd89545d6b6acfd7638bc708b98261ca58e84/ifeval_input_data.jsonl",
        "sha256": "6a85310ca8ce15eff755aa08a3a4ff931c7e273e7515ebb3c492ea85fd8288f2",
    },
    "banking_test": {
        "name": "PolyAI BANKING77 test split",
        "revision": "57ec275d8078af65b7731c2a98be812d844a6d6b",
        "license": "CC BY 4.0",
        "filename": "banking77-test.csv",
        "url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data/test.csv",
        "sha256": "d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d",
    },
    "banking_categories": {
        "name": "PolyAI BANKING77 category list",
        "revision": "57ec275d8078af65b7731c2a98be812d844a6d6b",
        "license": "CC BY 4.0",
        "filename": "banking77-categories.json",
        "url": "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data/categories.json",
        "sha256": "53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63",
    },
}

BANKING_LABELS = (
    "card_arrival", "card_delivery_estimate", "card_not_working",
    "card_payment_fee_charged", "card_payment_not_recognised",
    "cash_withdrawal_not_recognised", "declined_card_payment",
    "pending_card_payment", "request_refund", "transaction_charged_twice",
)

IFEVAL_QUOTAS = {
    "punctuation:no_comma": 10,
    "keywords:forbidden_words": 10,
    "startend:end_checker": 10,
    "startend:quotation": 10,
    "change_case:english_lowercase": 10,
    "detectable_format:number_bullet_lists": 10,
    "detectable_format:title": 10,
    "detectable_content:postscript": 10,
    "keywords:frequency": 10,
    "detectable_format:json_format": 8,
    "keywords:existence": 2,
}


def _source_file(name: str, offline: bool) -> Path:
    source = SOURCES[name]
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / source["filename"]
    if not path.exists():
        if offline:
            raise ValueError(f"Missing cached source: {path}")
        with urllib.request.urlopen(source["url"], timeout=120) as response, path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        raise ValueError(f"Source hash mismatch for {path}: {digest}")
    return path


def _rank(source_id: str) -> bytes:
    return hashlib.sha256(f"{SEED}:{source_id}".encode()).digest()


def _words(value: str) -> set[str]:
    return set(re.findall(r"\w+", value.casefold()))


def _overlap(reference: str, context: str) -> float:
    words = _words(reference)
    return len(words & _words(context)) / len(words) if words else 0.0


def _base(task: str, source: str, source_id: str, prompt: str, expected: object, reference: str) -> dict:
    info = SOURCES[source]
    return {
        "task_type": task,
        "input": prompt,
        "expected": expected,
        "reference_output": reference,
        "source": info["name"],
        "source_id": source_id,
        "source_revision": info["revision"],
        "source_license": info["license"],
        "tags": ["public", source],
    }


def _banking_cases(path: Path, categories_path: Path) -> list[dict]:
    categories = json.loads(categories_path.read_text(encoding="utf-8"))
    if not set(BANKING_LABELS) <= set(categories):
        raise ValueError("BANKING77 labels are missing from pinned categories")
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    labels_text = ", ".join(BANKING_LABELS)
    cases: list[dict] = []
    for label in BANKING_LABELS:
        candidates = [
            (f"test:{index}", row) for index, row in enumerate(rows)
            if row["category"] == label and 15 <= len(row["text"].strip()) <= 300
            and "\ufffd" not in row["text"]
        ]
        candidates.sort(key=lambda pair: _rank(f"banking77:{pair[0]}"))
        if len(candidates) < 10:
            raise ValueError(f"Only {len(candidates)} BANKING77 candidates for {label}")
        for source_id, row in candidates[:10]:
            prompt = f"Allowed intent labels: {labels_text}\nCustomer message: {row['text'].strip()}"
            cases.append(_base("classification", "banking_test", source_id, prompt, label, label))
    return sorted(cases, key=lambda case: _rank(f"banking77:{case['source_id']}"))


def _dolly_cases(path: Path, category: str, task: str) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    candidates: list[tuple[str, dict]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, 1):
        if row["category"] != category:
            continue
        instruction, context, response = (
            row["instruction"].strip(), row["context"].strip(), row["response"].strip()
        )
        if any("\ufffd" in value for value in (instruction, context, response)):
            continue
        if not (20 <= len(instruction) <= 280 and 120 <= len(context) <= 1800 and 5 <= len(response) <= 350):
            continue
        if task == "extraction" and (len(response) > 120 or _overlap(response, context) < 0.55):
            continue
        if task == "qa" and (len(response) > 180 or _overlap(response, context) < 0.55):
            continue
        if task == "summarization" and (
            len(response) < 40 or len(response) > 0.7 * len(context) or _overlap(response, context) < 0.40
        ):
            continue
        fingerprint = (instruction.casefold(), context.casefold())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        candidates.append((f"line:{index}", row))
    candidates.sort(key=lambda pair: _rank(f"dolly:{pair[0]}"))
    if len(candidates) < 100:
        raise ValueError(f"Only {len(candidates)} Dolly candidates for {task}")
    cases = []
    for source_id, row in candidates[:100]:
        instruction, context, response = (
            row["instruction"].strip(), row["context"].strip(), row["response"].strip()
        )
        if task == "extraction":
            prompt = f"Extract the answer to the request from the passage. Reply with the answer only.\nRequest: {instruction}\nPassage: {context}"
            expected = {"reference_text": response}
        elif task == "qa":
            prompt = f"Answer using only the passage.\nQuestion: {instruction}\nPassage: {context}"
            expected = response
        else:
            prompt = f"Task: {instruction}\nPassage: {context}"
            expected = {"reference_summary": response}
        cases.append(_base(task, "dolly", source_id, prompt, expected, response))
    return cases


def _ifeval_cases(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    cases: list[dict] = []
    for instruction_id, quota in IFEVAL_QUOTAS.items():
        candidates = [
            row for row in rows
            if row["instruction_id_list"] == [instruction_id]
            and len(row["prompt"]) <= 500
            and not re.search(r"\b(?:300|400|500|1000)\+?\s*words\b", row["prompt"], re.I)
        ]
        candidates.sort(key=lambda row: _rank(f"ifeval:{row['key']}"))
        if len(candidates) < quota:
            raise ValueError(f"Only {len(candidates)} IFEval candidates for {instruction_id}")
        for row in candidates[:quota]:
            expected = {
                "ifeval": {
                    "key": row["key"],
                    "instruction_id_list": row["instruction_id_list"],
                    "kwargs": row["kwargs"],
                }
            }
            cases.append(_base(
                "instruction_following", "ifeval", str(row["key"]),
                row["prompt"], expected, "",
            ))
    return sorted(cases, key=lambda case: _rank(f"ifeval:{case['source_id']}"))


def build(offline: bool = False) -> tuple[Path, Path]:
    paths = {name: _source_file(name, offline) for name in SOURCES}
    groups = [
        _banking_cases(paths["banking_test"], paths["banking_categories"]),
        _dolly_cases(paths["dolly"], "information_extraction", "extraction"),
        _dolly_cases(paths["dolly"], "closed_qa", "qa"),
        _dolly_cases(paths["dolly"], "summarization", "summarization"),
        _ifeval_cases(paths["ifeval"]),
    ]
    if any(len(group) != 100 for group in groups):
        raise ValueError("Each public benchmark task must have exactly 100 cases")
    prefixes = ("cls", "ext", "qa", "sum", "if")
    cases = []
    for index in range(100):
        for prefix, group in zip(prefixes, groups):
            case = dict(group[index])
            case["case_id"] = f"pub-{prefix}-{index + 1:03d}"
            cases.append(case)
    text = "".join(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n" for case in cases)
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    manifest = {
        "dataset_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "cases": len(cases),
        "task_counts": Counter(case["task_type"] for case in cases),
        "selection_seed": SEED,
        "sources": SOURCES,
        "note": "Source labels were screened with deterministic length/overlap filters; the 500 rows have not been individually human-labeled or checked for factual correctness.",
    }
    SOURCE_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return OUTPUT, SOURCE_MANIFEST


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use only cached source files")
    args = parser.parse_args()
    dataset, manifest = build(args.offline)
    print(f"Wrote {dataset} and {manifest}")
