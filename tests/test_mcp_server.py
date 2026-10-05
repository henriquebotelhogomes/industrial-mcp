"""Unit tests for Model Context Protocol (FastMCP) server tools and resources."""

import json

import pytest

from src.mcp.server import (
    calculate_application_depth,
    diagnose_equipment,
    mcp_server,
    request_emergency_stop,
)


@pytest.mark.asyncio
async def test_mcp_tools_registration():
    tools = await mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    assert "diagnose_equipment" in tool_names
    assert "request_emergency_stop" in tool_names
    assert "calculate_application_depth" in tool_names


@pytest.mark.asyncio
async def test_mcp_diagnose_tool():
    res_raw = await diagnose_equipment(
        pivot_id=14863,
        current_angle=120.0,
        pressure_begin=3.2,
        percent_timer=60.0,
        water_mode="Wet",
    )
    res = json.loads(res_raw)
    assert "is_anomaly" in res
    assert res["is_anomaly"] is False


@pytest.mark.asyncio
async def test_mcp_hitl_emergency_stop_guardrail():
    # Without human confirmation, direct PLC execution must be BLOCKED
    res_blocked_raw = await request_emergency_stop(
        pivot_id=14863,
        reason="Cavitação severa",
        operator_confirmed=False,
    )
    res_blocked = json.loads(res_blocked_raw)
    assert res_blocked["status"] == "PENDING_OPERATOR_APPROVAL"
    assert res_blocked["guardrail_enforced"] == "Human-in-the-Loop (HITL)"
    assert "HITL-STOP-14863" in res_blocked["ticket_id"]


@pytest.mark.asyncio
async def test_mcp_calculate_application_depth():
    res_raw = await calculate_application_depth(
        pivot_radius_meters=380.0,
        flow_rate_m3h=180.0,
        percent_timer=50.0,
    )
    res = json.loads(res_raw)
    assert "gross_application_depth_mm" in res
    assert res["gross_application_depth_mm"] > 0
    assert "irrigated_area_hectares" in res
