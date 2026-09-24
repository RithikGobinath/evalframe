"""Google Cloud Storage persistence for a single-task Cloud Run Job.

One object per case makes completed cases durable across job retries. A single
job execution must own a run ID at a time; object create preconditions reject
accidental concurrent writers rather than silently overwriting results.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path, PurePosixPath
from typing import Any


class GCSRunStore:
    def __init__(self, bucket_name: str, prefix: str = "evalframe", client: Any = None):
        if not bucket_name or "/" in bucket_name:
            raise ValueError("--gcs-bucket must be a bucket name, not a URL")
        parts = PurePosixPath(prefix).parts
        if not prefix or prefix == "." or prefix.startswith("/") or any(part in {".", ".."} for part in parts):
            raise ValueError("--gcs-prefix must be a relative object prefix")
        if client is None:
            try:
                from google.cloud import storage
            except ImportError as exc:
                raise ValueError("Install evalframe[cloud] to use --gcs-bucket") from exc
            client = storage.Client()
        self.bucket = client.bucket(bucket_name)
        self.prefix = prefix.strip("/")
        self.run_root: str | None = None

    def _key(self, suffix: str) -> str:
        if self.run_root is None:
            raise RuntimeError("Store has not been prepared")
        return f"{self.run_root}/{suffix}"

    @staticmethod
    def _model_hash(spec: str) -> str:
        return hashlib.sha256(spec.encode()).hexdigest()[:12]

    @staticmethod
    def _case_hash(case_id: str) -> str:
        return hashlib.sha256(case_id.encode()).hexdigest()

    def prepare(self, run_dir: Path, manifest: dict) -> None:
        self.run_root = f"{self.prefix}/runs/{manifest['run_id']}"
        blob = self.bucket.blob(self._key("manifest.json"))
        if blob.exists():
            try:
                remote = json.loads(blob.download_as_text())
            except json.JSONDecodeError as exc:
                raise ValueError("Corrupt cloud run manifest") from exc
            if remote != manifest:
                raise ValueError("Cloud run ID already exists with different inputs")
        else:
            blob.upload_from_string(
                json.dumps(manifest, indent=2), content_type="application/json",
                if_generation_match=0,
            )

    def restore_checkpoint(self, checkpoint: Path, spec: str) -> None:
        object_prefix = self._key(f"cases/{self._model_hash(spec)}/")
        rows: dict[str, dict] = {}
        for blob in self.bucket.list_blobs(prefix=object_prefix):
            if not blob.name.endswith(".json"):
                raise ValueError("Unexpected object in cloud checkpoint")
            try:
                row = json.loads(blob.download_as_text())
            except json.JSONDecodeError as exc:
                raise ValueError("Corrupt cloud checkpoint") from exc
            case_id = row.get("case_id")
            if not isinstance(case_id, str) or blob.name != object_prefix + self._case_hash(case_id) + ".json":
                raise ValueError("Cloud checkpoint case ID does not match its object name")
            if case_id in rows:
                raise ValueError("Duplicate case ID in cloud checkpoint")
            rows[case_id] = row
        if checkpoint.exists() and checkpoint.stat().st_size:
            local_ids = {
                json.loads(line)["case_id"] for line in checkpoint.read_text(encoding="utf-8").splitlines()
            }
            if not local_ids <= rows.keys():
                raise ValueError("Local checkpoint has results missing from cloud storage")
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows.values()),
            encoding="utf-8",
        )

    def save_row(self, spec: str, row: dict) -> None:
        case_id = row["case_id"]
        blob = self.bucket.blob(
            self._key(f"cases/{self._model_hash(spec)}/{self._case_hash(case_id)}.json")
        )
        blob.upload_from_string(
            json.dumps(row, ensure_ascii=False), content_type="application/json",
            if_generation_match=0,
        )

    def export(self, run_dir: Path, tracking_db: Path | None, artifact_root: Path | None) -> None:
        for path in run_dir.rglob("*"):
            if path.is_file():
                blob = self.bucket.blob(self._key(f"artifacts/run/{path.relative_to(run_dir).as_posix()}"))
                blob.upload_from_filename(str(path))
        if tracking_db is not None and tracking_db.exists():
            with tempfile.TemporaryDirectory() as temporary:
                snapshot = Path(temporary) / "mlflow.db"
                with closing(sqlite3.connect(tracking_db)) as source, closing(sqlite3.connect(snapshot)) as target:
                    source.backup(target)
                self.bucket.blob(self._key("artifacts/mlflow/mlflow.db")).upload_from_filename(str(snapshot))
        if artifact_root is not None and artifact_root.exists():
            for path in artifact_root.rglob("*"):
                if path.is_file():
                    blob = self.bucket.blob(
                        self._key(f"artifacts/mlflow/mlruns/{path.relative_to(artifact_root).as_posix()}")
                    )
                    blob.upload_from_filename(str(path))
