"""Integration tests for FastAPI REST endpoints, Scalar docs, and playback control."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.web.app import app


@pytest.mark.asyncio
async def test_scalar_docs_available():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "@scalar/api-reference" in response.text


@pytest.mark.asyncio
async def test_api_status_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_playing" in data
        assert "speed" in data


@pytest.mark.asyncio
async def test_playback_control():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Pause playback
        res = await client.post("/api/control/playback", json={"is_playing": False, "speed": 2.0})
        assert res.status_code == 200
        assert res.json()["is_playing"] is False
        assert res.json()["speed"] == 2.0

        # Resume playback
        res_resume = await client.post("/api/control/playback", json={"is_playing": True, "speed": 1.0})
        assert res_resume.status_code == 200
        assert res_resume.json()["is_playing"] is True


@pytest.mark.asyncio
async def test_anomaly_injection_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/control/inject-anomaly", json={"anomaly_type": "angle_jump"})
        assert res.status_code == 200
        assert res.json()["injected_anomaly"] == "angle_jump"


@pytest.mark.asyncio
async def test_catalog_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Farms
        res_farms = await client.get("/api/catalog/farms?limit=10")
        assert res_farms.status_code == 200
        farms = res_farms.json()
        assert len(farms) > 0
        assert "farm_name" in farms[0]
        assert "farm_id" in farms[0]

        # Types
        res_types = await client.get("/api/catalog/equipment-types")
        assert res_types.status_code == 200
        types = res_types.json()
        assert len(types) >= 6

        # Equipment
        res_equips = await client.get("/api/catalog/equipment?limit=10")
        assert res_equips.status_code == 200
        equips = res_equips.json()
        assert len(equips) > 0
        assert "equip_name" in equips[0]
        target_equip = equips[0]["equip_id"]

        # Select equipment
        res_select = await client.post("/api/control/select-equipment", json={"equip_id": target_equip})
        assert res_select.status_code == 200
        data = res_select.json()
        assert data["status"] == "SUCCESS"
        assert data["equip_id"] == target_equip
        assert data["telemetry"]["id_equip"] == target_equip
