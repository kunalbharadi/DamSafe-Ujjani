import os
import re
from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def put(self, key: str, source: Path) -> None: ...
    def delete(self, key: str) -> None: ...


def safe_key(key):
    if not re.fullmatch(r"[a-f0-9-]{36}/[a-f0-9-]{36}\.(csv|tif|tiff|geojson|gpkg)", key):
        raise ValueError("Invalid object key")
    return key


class LocalStorage:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key):
        path = (self.root / safe_key(key)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Storage path escapes root")
        return path

    def put(self, key, source):
        import shutil

        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as out, source.open("rb") as inp:
            shutil.copyfileobj(inp, out)

    def delete(self, key):
        self.path(key).unlink(missing_ok=True)


class S3Storage:
    def __init__(self):
        import boto3

        self.client = boto3.client("s3", endpoint_url=os.environ.get("DAMSAFE_S3_ENDPOINT"))
        self.bucket = os.environ["DAMSAFE_S3_BUCKET"]

    def put(self, key, source):
        self.client.upload_file(str(source), self.bucket, safe_key(key))

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=safe_key(key))


def storage_for():
    if os.environ.get("DAMSAFE_STORAGE", "local") == "s3":
        return S3Storage()
    return LocalStorage(os.environ.get("DAMSAFE_STORAGE_ROOT", ".local/objects"))
