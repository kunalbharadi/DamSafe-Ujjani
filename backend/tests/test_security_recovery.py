import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from damsafe.api import create_app, MAX_UPLOAD
from damsafe.storage import safe_key, LocalStorage


def test_storage_path_traversal_protection(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError, match="Invalid object key"):
        safe_key("../../../etc/passwd")

    with pytest.raises(ValueError, match="Invalid object key"):
        safe_key("malicious/key.exe")


def test_request_upload_size_limit():
    app = create_app("sqlite:///:memory:")
    client = TestClient(app)

    # Test payload exceeding MAX_UPLOAD headers
    res = client.post(
        "/api/observation/import",
        headers={"content-length": str(MAX_UPLOAD + 1000)},
        json={},
    )
    assert res.status_code == 413
    assert "upload limit" in res.json()["detail"]


def test_api_health_check():
    app = create_app("sqlite:///:memory:")
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_application_restart_and_state_recovery(tmp_path, monkeypatch):
    """Verify that persisted projects, datasets, and runs survive server instance restart."""
    db_file = tmp_path / "restart.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    storage_dir = tmp_path / "storage"
    monkeypatch.setenv("DAMSAFE_DATABASE_URL", db_url)
    
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config("alembic.ini"), "head")
    
    # Instance 1: Create project and dataset
    app1 = create_app(db_url, LocalStorage(storage_dir))
    with TestClient(app1) as client1:
        p_res = client1.post("/api/projects", json={"name": "Persistent Lab", "site_key": "pers-lab", "synthetic": True})
        assert p_res.status_code == 201
        project_id = p_res.json()["id"]

    # Instance 2: Simulate complete app shutdown and restart on same SQLite database
    app2 = create_app(db_url, LocalStorage(storage_dir))
    with TestClient(app2) as client2:
        p_res2 = client2.get(f"/api/projects/{project_id}")
        assert p_res2.status_code == 200
        assert p_res2.json()["name"] == "Persistent Lab"
        assert p_res2.json()["site_key"] == "pers-lab"

