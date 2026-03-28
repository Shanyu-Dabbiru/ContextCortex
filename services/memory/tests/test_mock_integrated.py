import pytest
from fastapi.testclient import TestClient
import os

# Set dummy env vars for testing
os.environ["HYDRADB_API_KEY"] = "hdb_test"
os.environ["HYDRADB_BASE_URL"] = "https://test.hydradb.com/v1"
os.environ["MEMORY_SERVICE_API_KEY"] = "msk_test"

from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "connected", "embedding_service": "connected"}

def test_unauthorized():
    response = client.post("/api/v1/nodes", json={})
    assert response.status_code == 403 # HTTPBearer returns 403 if no header

def test_authorized_upsert_node():
    headers = {"Authorization": "Bearer msk_test"}
    node_data = {
        "type": "decision",
        "id": "test-decision-1",
        "data": {"title": "Test Decision", "description": "This is a test"}
    }
    response = client.post("/api/v1/nodes", json=node_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["node_id"] == "test-decision-1"

def test_authorized_ingest_triple():
    headers = {"Authorization": "Bearer msk_test"}
    triple_data = {
        "subject": {"type": "decision", "id": "test-decision-1"},
        "predicate": "MADE_BY",
        "object": {"type": "user", "id": "shanyu"},
        "metadata": {
            "source": "test",
            "timestamp": "2026-03-28T12:00:00Z",
            "confidence": 0.9
        }
    }
    response = client.post("/api/v1/ingest", json=triple_data, headers=headers)
    assert response.status_code == 200
    assert "triple_id" in response.json()

def test_authorized_recall():
    headers = {"Authorization": "Bearer msk_test"}
    recall_data = {
        "query": "Why JWT?",
        "scope": {"types": ["decision"], "depth": 2}
    }
    response = client.post("/api/v1/recall", json=recall_data, headers=headers)
    assert response.status_code == 200
    assert "triples" in response.json()
    assert "nodes" in response.json()

def test_authorized_check_conflict():
    headers = {"Authorization": "Bearer msk_test"}
    check_data = {
        "code_diff": "- import jwt\n+ import express-session",
        "file_paths": ["src/auth.ts"]
    }
    response = client.post("/api/v1/check", json=check_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "conflict"
    assert len(response.json()["violations"]) > 0

def test_authorized_check_clean():
    headers = {"Authorization": "Bearer msk_test"}
    check_data = {
        "code_diff": "no change",
        "file_paths": ["src/other.ts"]
    }
    response = client.post("/api/v1/check", json=check_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "clean"
