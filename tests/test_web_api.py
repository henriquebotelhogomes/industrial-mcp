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

        # Farms with include_farm_id guarantee (farm 1515 has only 22 equips, would normally be omitted with limit=5)
        res_farms_inc = await client.get("/api/catalog/farms?limit=5&include_farm_id=1515")
        assert res_farms_inc.status_code == 200
        farms_inc = res_farms_inc.json()
        assert any(f["farm_id"] == 1515 for f in farms_inc)
        assert any(f["farm_name"] == "VB Homestead" for f in farms_inc)

        # Types
        res_types = await client.get("/api/catalog/equipment-types")
        assert res_types.status_code == 200
        types = res_types.json()
        assert len(types) >= 6

        # Equipment with include_equip_id guarantee
        res_equips = await client.get("/api/catalog/equipment?limit=5&include_equip_id=14863")
        assert res_equips.status_code == 200
        equips = res_equips.json()
        assert len(equips) > 0
        assert any(e["equip_id"] == 14863 for e in equips)
        assert "equip_name" in equips[0]
        target_equip = equips[0]["equip_id"]

        # Select equipment
        res_select = await client.post("/api/control/select-equipment", json={"equip_id": target_equip})
        assert res_select.status_code == 200
        data = res_select.json()
        assert data["status"] == "SUCCESS"
        assert data["equip_id"] == target_equip
        assert data["telemetry"]["id_equip"] == target_equip
        assert "catalog_spec" in data
        assert data["catalog_spec"]["equip_id"] == target_equip


@pytest.mark.asyncio
async def test_cross_tab_equipment_synchronization():
    """Verifies that switching equipment updates telemetry, catalog spec, and copilot consistency."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Switch to equip 19566 (ARES.01 - 2020 on ÁguaSanta.Perdizes.MG)
        res = await client.post("/api/control/select-equipment", json={"equip_id": 19566})
        assert res.status_code == 200
        payload = res.json()
        assert payload["status"] == "SUCCESS"
        assert payload["equip_id"] == 19566

        spec = payload["catalog_spec"]
        assert spec is not None
        assert spec["equip_id"] == 19566
        assert "Perdizes" in spec["farm_name"]
        assert spec["maker"] == "AsBrasil"
        assert spec["model"] == "Valmatic"

        # Check telemetry event consistency
        tel = payload["telemetry"]
        assert tel["id_equip"] == 19566
        assert tel["pivot_maker"] == "AsBrasil"
        assert tel["pivot_model"] == "Valmatic"
        assert "Perdizes" in tel["farm_name"]

        # Check API status
        st_res = await client.get("/api/status")
        assert st_res.status_code == 200
        current_tel = st_res.json()["current_telemetry"]
        assert current_tel["id_equip"] == 19566
        assert current_tel["pivot_maker"] == "AsBrasil"

        # Check Copilot chat retrieves same catalog spec
        chat_res = await client.post(
            "/api/copilot/chat",
            json={"query": "Qual o fabricante e modelo deste pivô?", "equip_id": 19566},
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert chat_data["catalog_spec"]["maker"] == "AsBrasil"
        assert chat_data["catalog_spec"]["model"] == "Valmatic"
        assert "Perdizes" in chat_data["catalog_spec"]["farm_name"]


@pytest.mark.asyncio
async def test_farm_selection_equipment_isolation():
    """Verifies that selecting equipment scoped to a farm never pollutes with equipment from another farm."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Farm 822 (Igarashi) requested with include_equip_id=14863 (which belongs to Farm 1515 VB Homestead)
        res = await client.get("/api/catalog/equipment?farm_id=822&include_equip_id=14863&limit=10")
        assert res.status_code == 200
        equips = res.json()
        assert len(equips) > 0
        # ALL returned equipment must belong strictly to farm 822
        for eq in equips:
            assert eq["farm_id"] == 822
        # Equip 14863 from farm 1515 must NOT be in the results
        assert not any(eq["equip_id"] == 14863 for eq in equips)

