"""Automated tests for LangGraph Cognitive Copilot, Relational RAG, and HITL Guardrails."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.agent.graph import copilot_graph
from src.agent.relational_rag import relational_rag
from src.web.app import app


def test_relational_rag_catalog_retrieval():
    """Validates structured retrieval of asset specifications from DuckDB."""
    specs = relational_rag.get_catalog_specs(14863)
    assert specs is not None
    assert "nominal_pressure" in specs
    assert "maker" in specs
    assert specs["nominal_pressure"] > 0.0


def test_relational_rag_deficit_calculations():
    """Tests calculation of hydraulic deficits between factory specs and live telemetry."""
    specs = {"nominal_pressure": 3.4, "area": 45.0, "flow_rate": 180.0}
    nominal_telemetry = {"pressao_bar": 3.4, "water_mode": "Wet", "percent_timer": 70.0}
    nominal_deficits = relational_rag.calculate_deficits(specs, nominal_telemetry)

    assert nominal_deficits["is_critical_pressure"] is False
    assert nominal_deficits["pressure_deficit_pct"] == 0.0

    critical_telemetry = {"pressao_bar": 0.8, "water_mode": "Wet", "percent_timer": 70.0}
    critical_deficits = relational_rag.calculate_deficits(specs, critical_telemetry)

    assert critical_deficits["is_critical_pressure"] is True
    assert critical_deficits["pressure_deficit_pct"] > 50.0


@pytest.mark.asyncio
async def test_copilot_graph_execution():
    """Validates end-to-end execution of the LangGraph StateGraph with resilient synthesis."""
    state_input = {
        "user_query": "Qual o estado operacional do pivô Haak 1?",
        "equip_id": 14863,
        "session_id": "test_session_1",
    }
    config = {"configurable": {"thread_id": "test_session_1"}}

    result = await copilot_graph.ainvoke(state_input, config)

    assert result is not None
    assert "final_markdown" in result
    assert len(result["final_markdown"]) > 50
    assert "finops_stats" in result
    assert result["catalog_spec"]["equip_id"] == 14863


@pytest.mark.asyncio
async def test_copilot_web_chat_endpoint():
    """Validates POST /api/copilot/chat endpoint response contract."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/copilot/chat",
            json={
                "query": "Comparar pressão medida com a pressão de projeto",
                "equip_id": 14863,
                "session_id": "test_web_session",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response_markdown" in data
        assert "catalog_spec" in data
        assert "deficit_metrics" in data
        assert "requires_hitl" in data


@pytest.mark.asyncio
async def test_copilot_web_hitl_approval_endpoint():
    """Validates operator approval of critical action via FastMCP tool."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/copilot/hitl/approve",
            json={
                "ticket_id": "TICKET-TEST-100",
                "operator_name": "Eng_Henrique",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPROVED_AND_EXECUTED"
        assert "mcp_result" in data
        assert data["operator"] == "Eng_Henrique"
