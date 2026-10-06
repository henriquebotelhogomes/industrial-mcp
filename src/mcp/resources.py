"""Model Context Protocol (MCP) Resources: Read-only audit-friendly telemetry context."""

import json

import duckdb
from mcp.server.mcpserver import MCPServer

from src.config import settings
from src.core.logging import logger
from src.data.state import state_manager


def register_resources(server: MCPServer) -> None:
    """Registers declarative MCP resources onto the MCPServer instance."""

    @server.resource("telemetry://pivot/{pivot_id}/live")
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

    @server.resource("telemetry://pivot/{pivot_id}/specs")
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

    @server.resource("telemetry://fleet/overview")
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
