"""Global in-memory telemetry state, replay engine, and HITL authorization store."""

import asyncio
from datetime import datetime
from typing import Any

import duckdb

from src.config import settings
from src.core.logging import logger
from src.ml.anomaly_detector import detector
from src.ml.domain_rules import AnomalyReport, TelemetryEvent


class TelemetryStateManager:
    """Manages real-time telemetry stream replay, active pivot status, and HITL approval queue."""

    def __init__(self):
        self.is_playing: bool = True
        self.speed: float = 1.0
        self.current_index: int = 0
        self.telemetry_history: list[dict[str, Any]] = []
        self.current_event: TelemetryEvent | None = None
        self.previous_event: TelemetryEvent | None = None
        self.active_anomaly_report: AnomalyReport | None = None
        self.pending_hitl_ticket: dict[str, Any] | None = None
        self.injected_anomaly: str | None = None
        self.lock = asyncio.Lock()
        self.subscribers: set[asyncio.Queue] = set()

    def load_telemetry_series(self, equip_id: int | None = None) -> int:
        """Loads historical telemetry sequence for replay from DuckDB/Parquet."""
        try:
            con = duckdb.connect(str(settings.duckdb_path), read_only=True)
            filter_clause = f"WHERE id_equip = {equip_id}" if equip_id else ""
            query = f"""
                SELECT
                    id_farm, id_equip, farm_name, pivot_name, pivot_maker, pivot_model,
                    nominal_pressure, pivot_radius, timestamp, current_angle, direction,
                    running_status, water_mode, percent_timer, pressure_begin, pressure_end,
                    flow_rate
                FROM v_gold_metrics
                {filter_clause}
                ORDER BY timestamp ASC
            """
            rows = con.execute(query).fetchall()
            cols = [
                "id_farm", "id_equip", "farm_name", "pivot_name", "pivot_maker", "pivot_model",
                "nominal_pressure", "pivot_radius", "timestamp", "current_angle", "direction",
                "running_status", "water_mode", "percent_timer", "pressure_begin", "pressure_end",
                "flow_rate"
            ]
            con.close()

            self.telemetry_history = [dict(zip(cols, r, strict=False)) for r in rows]
            if not self.telemetry_history:
                self._load_fallback_baseline()
            logger.info("telemetry_series_loaded", total_records=len(self.telemetry_history))
            return len(self.telemetry_history)
        except Exception as e:
            logger.warn("duckdb_load_failed_using_fallback", error=str(e))
            self._load_fallback_baseline()
            return len(self.telemetry_history)

    def _load_fallback_baseline(self) -> None:
        """Generates realistic continuous operational baseline if historical database is cold."""
        baseline = []
        angle = 0.0
        for _i in range(360):
            angle = (angle + 1.0) % 360.0
            baseline.append({
                "id_farm": 1515,
                "id_equip": 14863,
                "farm_name": "VB Homestead",
                "pivot_name": "Haak 1",
                "pivot_maker": "Valmont",
                "pivot_model": "Valley 8000C",
                "nominal_pressure": 3.4,
                "pivot_radius": 380.0,
                "timestamp": datetime.now().isoformat(),
                "current_angle": round(angle, 1),
                "direction": "Forward",
                "running_status": "Running",
                "water_mode": "Wet",
                "percent_timer": 65.0,
                "pressure_begin": 3.4,
                "pressure_end": 2.9,
                "flow_rate": 185.0,
            })
        self.telemetry_history = baseline

    async def advance_tick(self) -> dict[str, Any]:
        """Advances the telemetry stream simulation by one time step."""
        async with self.lock:
            if not self.telemetry_history:
                self.load_telemetry_series()

            raw_item = self.telemetry_history[self.current_index % len(self.telemetry_history)].copy()
            if self.is_playing:
                self.current_index = (self.current_index + 1) % len(self.telemetry_history)

            # Apply live injected anomalies if requested by operator
            if self.injected_anomaly == "angle_jump":
                raw_item["current_angle"] = (raw_item["current_angle"] + 45.0) % 360.0
                logger.warn("anomaly_injected_live", type="angle_jump", new_angle=raw_item["current_angle"])
                self.injected_anomaly = None  # One-shot injection

            elif self.injected_anomaly == "pressure_drop":
                raw_item["water_mode"] = "Wet"
                raw_item["pressure_begin"] = 0.35  # Severe pressure loss below 1.2 bar
                logger.warn("anomaly_injected_live", type="pressure_drop", pressure=0.35)
                # Keep one-shot or until reset

            elif self.injected_anomaly == "sensor_spike":
                raw_item["percent_timer"] = 150.0  # Physically impossible percent timer
                self.injected_anomaly = None

            event = TelemetryEvent(
                id_farm=int(raw_item.get("id_farm") or 1515),
                id_equip=int(raw_item.get("id_equip") or 14863),
                farm_name=raw_item.get("farm_name") or "VB Homestead",
                pivot_name=raw_item.get("pivot_name") or "Haak 1",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                current_angle=float(raw_item.get("current_angle") or 0.0),
                direction=str(raw_item.get("direction") or "Forward"),
                running_status=str(raw_item.get("running_status") or "Running"),
                water_mode=str(raw_item.get("water_mode") or "Wet"),
                percent_timer=float(raw_item.get("percent_timer") or 60.0),
                pressure_begin=float(raw_item.get("pressure_begin") or 3.2),
                pressure_end=float(raw_item.get("pressure_end") or 2.8),
                flow_rate=float(raw_item.get("flow_rate") or 180.0),
                nominal_pressure=float(raw_item.get("nominal_pressure") or 3.4),
                pivot_radius=float(raw_item.get("pivot_radius") or 380.0),
            )

            # Evaluate with hybrid ML (Isolation Forest) and domain physics rules
            elapsed = 60.0 / max(0.1, self.speed)
            report = detector.evaluate(event, self.previous_event, elapsed_seconds=elapsed)

            self.previous_event = self.current_event
            self.current_event = event
            self.active_anomaly_report = report

            # If anomaly requires human intervention and no ticket is open, generate one
            if report.is_anomaly and report.requires_operator_approval and not self.pending_hitl_ticket:
                self.pending_hitl_ticket = {
                    "ticket_id": f"HITL-STOP-{event.id_equip}-{int(datetime.now().timestamp())}",
                    "pivot_id": event.id_equip,
                    "pivot_name": event.pivot_name,
                    "action_required": report.recommended_action,
                    "severity": "CRITICAL" if report.confidence_score > 0.7 else "WARNING",
                    "confidence_score": report.confidence_score,
                    "reasons": report.anomaly_types,
                    "created_at": datetime.now().isoformat(),
                    "status": "AWAITING_OPERATOR_APPROVAL",
                }
                logger.warn("hitl_ticket_generated", ticket=self.pending_hitl_ticket)

            payload = {
                "telemetry": event.model_dump(),
                "anomaly": report.model_dump(),
                "hitl_ticket": self.pending_hitl_ticket,
                "is_playing": self.is_playing,
                "speed": self.speed,
            }

            # Broadcast to connected WebSocket queues
            for queue in list(self.subscribers):
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

            return payload

    async def inject_anomaly(self, anomaly_type: str) -> None:
        """Allows dashboard operator to inject anomaly deterministically during demo."""
        async with self.lock:
            self.injected_anomaly = anomaly_type
            logger.info("operator_requested_anomaly_injection", type=anomaly_type)

    async def approve_hitl_action(self, ticket_id: str, operator_name: str = "Operator_Henrique") -> dict[str, Any]:
        """Operator approves emergency intervention (HITL). Executes PLC simulated stop."""
        async with self.lock:
            if not self.pending_hitl_ticket or self.pending_hitl_ticket.get("ticket_id") != ticket_id:
                return {"status": "ERROR", "message": "Ticket inválido ou expirado."}

            # Emulate physical PLC coil actuation
            if self.current_event:
                self.current_event.running_status = "Stopped"
                self.current_event.water_mode = "Dry"
                self.current_event.pressure_begin = 0.0
                self.current_event.pressure_end = 0.0

            ticket = self.pending_hitl_ticket
            ticket["status"] = "APPROVED_AND_EXECUTED"
            ticket["approved_by"] = operator_name
            ticket["resolved_at"] = datetime.now().isoformat()

            # Clear active anomaly and pending ticket
            self.pending_hitl_ticket = None
            self.injected_anomaly = None
            if self.active_anomaly_report:
                self.active_anomaly_report.is_anomaly = False
                self.active_anomaly_report.requires_operator_approval = False

            logger.info("hitl_action_executed", ticket=ticket)
            return {"status": "SUCCESS", "message": "Comando de parada de emergência transmitido com sucesso ao CLP via SCADA.", "ticket": ticket}

    async def reject_hitl_action(self, ticket_id: str) -> dict[str, Any]:
        """Operator overrides AI diagnostic and rejects intervention."""
        async with self.lock:
            if not self.pending_hitl_ticket or self.pending_hitl_ticket.get("ticket_id") != ticket_id:
                return {"status": "ERROR", "message": "Ticket inválido."}

            self.pending_hitl_ticket = None
            self.injected_anomaly = None
            logger.warn("hitl_action_rejected_by_operator", ticket_id=ticket_id)
            return {"status": "REJECTED", "message": "Intervenção cancelada pelo operador humano."}


state_manager = TelemetryStateManager()
