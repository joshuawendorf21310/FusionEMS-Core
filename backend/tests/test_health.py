from fastapi.testclient import TestClient

from core_app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health", headers={"X-Tenant-ID": "test"})
    assert response.status_code == 200
