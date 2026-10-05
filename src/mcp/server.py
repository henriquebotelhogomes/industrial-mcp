"""Official Model Context Protocol (FastMCP / MCPServer) implementation for Industrial Telemetry."""

import json

import duckdb
from mcp.server.mcpserver import MCPServer

from src.config import settings
from src.core.logging import logger
from src.data.state import state_manager
from src.ml.anomaly_detector import detector
from src.ml.domain_rules import TelemetryEvent

# Initialize MCPServer
mcp_server = MCPServer(settings.mcp_server_name)


# ---------------------------------------------------------------------------
# MCP Resources: Read-only, audit-friendly, token-efficient telemetry context
# ---------------------------------------------------------------------------

@mcp_server.resource("telemetry://pivot/{pivot_id}/live")
async def get_pivot_live_telemetry(pivot_id: str) -> str:
    """Returns the latest real-time SCADA telemetry for the specified Center Pivot."""
    if state_manager.current_event and str(state_manager.current_event.id_equip) == str(pivot_id):
        event = state_manager.current_event.model_dump()
        return json.dumps(event, indent=2)

    # Query DuckDB if not in active memory
    try:
        con = duckdb.connect(str(settings.duckdb_path), read_only=True)
        res = con.execute(f"""
            SELECT * FROM v_gold_metrics
            WHERE id_equip = {int(pivot_id)}
            ORDER BY timestamp DESC LIMIT 1
        """).pl()
        con.close()
        if not res.is_empty():
            return json.dumps(res.to_dicts()[0], indent=2, default=str)
    except Exception as e:
        logger.error("mcp_resource_read_error", error=str(e), pivot_id=pivot_id)

    return json.dumps({"error": f"Equipamento {pivot_id} não encontrado na base de telemetria."}, indent=2)


@mcp_server.resource("telemetry://pivot/{pivot_id}/specs")
async def get_pivot_specs(pivot_id: str) -> str:
    """Returns engineering and mechanical specifications (radius, maker, nominal pressure)."""
    try:
        con = duckdb.connect(str(settings.duckdb_path), read_only=True)
        res = con.execute(f"""
            SELECT ID, Nome, Modelo, Fabrica, RaioUltimaTorre, PressaoServico, Vazao, Area, Tempo_Volta
            FROM read_parquet('{str(settings.bronze_parquet_dir / "pivocentral.parquet").replace("\\", "/")}')
            WHERE ID = '{pivot_id}' LIMIT 1
        """).pl()
        con.close()
        if not res.is_empty():
            return json.dumps(res.to_dicts()[0], indent=2, default=str)
    except Exception as e:
        logger.error("mcp_resource_specs_error", error=str(e), pivot_id=pivot_id)

    return json.dumps({"error": f"Especificações mecânicas para pivô {pivot_id} indisponíveis."}, indent=2)


@mcp_server.resource("telemetry://fleet/overview")
async def get_fleet_overview() -> str:
    """Returns fleet-wide operating status across all farms and pivots."""
    try:
        con = duckdb.connect(str(settings.duckdb_path), read_only=True)
        summary = con.execute("""
            SELECT
                count(distinct id_farm) as total_farms,
                count(distinct id_equip) as total_pivots,
                count(*) filter (where running_status = 'Running') as active_running,
                count(*) filter (where is_effective_irrigation = true) as irrigating_count,
                count(*) filter (where flag_pressure_anomaly = true) as pressure_anomalies_flagged
            FROM v_gold_metrics
        """).pl()
        con.close()
        return json.dumps(summary.to_dicts()[0], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ---------------------------------------------------------------------------
# MCP Tools: Active diagnostic and control tools with Human-in-the-Loop (HITL)
# ---------------------------------------------------------------------------

@mcp_server.tool()
async def diagnose_equipment(
    pivot_id: int,
    current_angle: float,
    pressure_begin: float,
    percent_timer: float,
    water_mode: str,
    previous_angle: float | None = None,
) -> str:
    """Diagnoses pivot operational state using Valmont physical rules and Isolation Forest ML.

    Evaluates potential encoder slippage, pump cavitation/dry pipe, and statistical anomalies.
    """
    event = TelemetryEvent(
        id_farm=1515,
        id_equip=pivot_id,
        timestamp="NOW",
        current_angle=current_angle,
        direction="Forward",
        running_status="Running",
        water_mode=water_mode,
        percent_timer=percent_timer,
        pressure_begin=pressure_begin,
        pressure_end=pressure_begin * 0.85,
        flow_rate=180.0,
    )

    prev_event = None
    if previous_angle is not None:
        prev_event = TelemetryEvent(
            id_farm=1515,
            id_equip=pivot_id,
            timestamp="PREV",
            current_angle=previous_angle,
            direction="Forward",
            running_status="Running",
            water_mode=water_mode,
            percent_timer=percent_timer,
            pressure_begin=pressure_begin,
            pressure_end=pressure_begin * 0.85,
            flow_rate=180.0,
        )

    report = detector.evaluate(event, prev_event, elapsed_seconds=60.0)
    return json.dumps(report.model_dump(), indent=2)


@mcp_server.tool()
async def request_emergency_stop(
    pivot_id: int,
    reason: str,
    operator_confirmed: bool = False,
) -> str:
    """Requests emergency de-energization of pivot drive and pump motor.

    IMPORTANT SAFETY GUARDRAIL (HITL):
    Direct PLC coil write is strictly blocked until an authorized human operator
    approves the command via the SCADA supervisory interface.
    """
    if not operator_confirmed:
        ticket = {
            "status": "PENDING_OPERATOR_APPROVAL",
            "guardrail_enforced": "Human-in-the-Loop (HITL)",
            "pivot_id": pivot_id,
            "reason": reason,
            "message": "Comando de parada de emergência bloqueado por segurança cibernética e estabilidade sistêmica. Exige confirmação explícita do operador humano na console SCADA.",
            "ticket_id": f"HITL-STOP-{pivot_id}",
        }
        return json.dumps(ticket, indent=2)

    # If operator has confirmed, perform simulated actuation
    res = await state_manager.approve_hitl_action(f"HITL-STOP-{pivot_id}")
    return json.dumps(res, indent=2)


@mcp_server.tool()
async def calculate_application_depth(
    pivot_radius_meters: float,
    flow_rate_m3h: float,
    percent_timer: float,
    efficiency_fraction: float = 0.88,
) -> str:
    """Calculates gross and net water application depth (mm per revolution).

    Formula: Lamina = (Vazao * HorasPorVolta) / Area
    """
    import math

    if percent_timer <= 0.0 or pivot_radius_meters <= 0.0:
        return json.dumps({"error": "Parâmetros físicos inválidos (percentímetro ou raio <= 0)."}, indent=2)

    area_ha = (math.pi * (pivot_radius_meters ** 2)) / 10000.0
    # Baseline: 100% timer does full turn in ~18 hours
    hours_full_turn = 18.0 * (100.0 / percent_timer)
    total_volume_m3 = flow_rate_m3h * hours_full_turn
    gross_depth_mm = (total_volume_m3 / (area_ha * 10000.0)) * 1000.0
    net_depth_mm = gross_depth_mm * efficiency_fraction

    result = {
        "pivot_radius_m": pivot_radius_meters,
        "irrigated_area_hectares": round(area_ha, 2),
        "percent_timer": percent_timer,
        "hours_per_full_revolution": round(hours_full_turn, 2),
        "gross_application_depth_mm": round(gross_depth_mm, 2),
        "net_application_depth_mm": round(net_depth_mm, 2),
        "application_efficiency": efficiency_fraction,
    }
    return json.dumps(result, indent=2)
