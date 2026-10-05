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
