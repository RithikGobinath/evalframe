import asyncio
import json
import sqlite3
from contextlib import closing

import pytest

from evalframe.cloud_store import GCSRunStore
from evalframe.providers import ProviderResponse
from evalframe.runner import run_evaluation


class MemoryBlob:
    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name

    def exists(self):
        return self.name in self.bucket.objects

    def download_as_text(self):
        return self.bucket.objects[self.name].decode()

    def upload_from_string(self, value, *, if_generation_match=None, **_):
        if if_generation_match == 0 and self.exists():
            raise ValueError("object already exists")
        self.bucket.objects[self.name] = value.encode()

    def upload_from_filename(self, filename):
        with open(filename, "rb") as stream:
            self.bucket.objects[self.name] = stream.read()


class MemoryBucket:
    def __init__(self):
        self.objects = {}

    def blob(self, name):
        return MemoryBlob(self, name)

    def list_blobs(self, *, prefix):
        return [self.blob(name) for name in self.objects if name.startswith(prefix)]


class MemoryClient:
    def __init__(self):
        self.storage = MemoryBucket()

    def bucket(self, _):
        return self.storage


class FakeProvider:
    def __init__(self):
        self.calls = 0

    async def generate(self, model, system, user, max_output_tokens):
        self.calls += 1
        return ProviderResponse("billing", 3, 1, "fake-request", "stop")

    async def close(self):
        pass


def test_cloud_checkpoint_survives_fresh_local_job(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps({"case_id": "case/1", "task_type": "classification", "input": "Ticket", "expected": "billing"}) + "\n",
        encoding="utf-8",
    )
    prompt = tmp_path / "prompt.toml"
    prompt.write_text(
        'version = "v1"\n' + "\n".join(
            f'[tasks.{task}]\nsystem = "Answer briefly"'
            for task in ("classification", "extraction", "qa", "summarization", "instruction_following")
        ),
        encoding="utf-8",
    )
    client = MemoryClient()
    provider = FakeProvider()
    kwargs = dict(
        dataset=dataset,
        prompt_file=prompt,
        model_specs=["openrouter:test"],
        run_id="cloud-test",
        provider_factory=lambda _: provider,
        log_mlflow=False,
    )
    first_dir, first = asyncio.run(run_evaluation(
        **kwargs, output_root=tmp_path / "first",
        run_store=GCSRunStore("test-bucket", client=client),
    ))
    second_dir, second = asyncio.run(run_evaluation(
        **kwargs, output_root=tmp_path / "second",
        run_store=GCSRunStore("test-bucket", client=client),
    ))
    assert first == second
    assert first_dir != second_dir
    assert provider.calls == 1
    assert len([key for key in client.storage.objects if "/cases/" in key]) == 1
    assert "evalframe/runs/cloud-test/artifacts/run/summary.json" in client.storage.objects

    prompt.write_text(prompt.read_text(encoding="utf-8").replace("v1", "v2"), encoding="utf-8")
    with pytest.raises(ValueError, match="different inputs"):
        asyncio.run(run_evaluation(
            **kwargs, output_root=tmp_path / "third",
            run_store=GCSRunStore("test-bucket", client=client),
        ))


@pytest.mark.parametrize("prefix", ["../other", "/absolute", "."])
def test_cloud_store_rejects_unsafe_prefix(prefix):
    with pytest.raises(ValueError, match="relative object prefix"):
        GCSRunStore("test-bucket", prefix=prefix, client=MemoryClient())


def test_cloud_export_includes_usable_mlflow_snapshot(tmp_path):
    client = MemoryClient()
    store = GCSRunStore("test-bucket", client=client)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "summary.json").write_text("{}", encoding="utf-8")
    tracking_db = tmp_path / "mlflow.db"
    with closing(sqlite3.connect(tracking_db)) as connection:
        connection.execute("create table marker (value text)")
        connection.execute("insert into marker values ('saved')")
        connection.commit()
    artifact_root = tmp_path / "mlruns"
    artifact_root.mkdir()
    (artifact_root / "artifact.txt").write_text("saved", encoding="utf-8")

    store.prepare(run_dir, {"run_id": "snapshot"})
    store.export(run_dir, tracking_db, artifact_root)

    root = "evalframe/runs/snapshot/artifacts/mlflow/"
    restored_db = tmp_path / "restored.db"
    restored_db.write_bytes(client.storage.objects[root + "mlflow.db"])
    with closing(sqlite3.connect(restored_db)) as connection:
        assert connection.execute("select value from marker").fetchone()[0] == "saved"
    assert client.storage.objects[root + "mlruns/artifact.txt"] == b"saved"
