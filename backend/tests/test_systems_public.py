from fastapi.testclient import TestClient

from core_app.main import app

client = TestClient(app)


def test_systems_list_is_public():
    res = client.get("/api/v1/systems", headers={"X-Tenant-ID": "test"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "system_key" in first
    assert "name" in first
    assert "status" in first


def test_systems_detail_is_public():
    res = client.get("/api/v1/systems/fusionbilling", headers={"X-Tenant-ID": "test"})
    assert res.status_code == 200
    data = res.json()
    assert data["system_key"] == "fusionbilling"
    assert data["status"] in {
        "ACTIVE",
        "CERTIFICATION_ACTIVATION_REQUIRED",
        "ARCHITECTURE_COMPLETE",
        "ACTIVE_CORE_LAYER",
        "IN_DEVELOPMENT",
        "INFRASTRUCTURE_LAYER",
    }
