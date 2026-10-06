"""Global in-memory telemetry state, replay engine, and HITL authorization store."""

import asyncio
from datetime import datetime
from typing import Any

import duckdb

from src.config import settings
from src.core.logging import logger
from src.data.catalog import asset_catalog
from src.ml.anomaly_detector import detector
from src.ml.domain_rules import AnomalyReport, TelemetryEvent
from src.ml.drift_monitor import drift_monitor


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

    def load_telemetry_series(self, equip_id: int | None = 14863) -> int:
        """Loads smooth continuous operational telemetry sequence based on real equipment specs."""
        target_id = equip_id or 14863
        farm_id = 1515
        farm_name = "VB Homestead"
        farm_city = "Sunnyside"
        farm_state = "WA"
        pivot_name = "Haak 1"
        maker = "Valmont"
        model = "Valley 8000C"
        nom_pressure = 3.4
        radius = 380.0
        flow = 185.0
        area = 45.0

        try:
            catalog_spec = asset_catalog.get_equipment_by_id(target_id)
            if catalog_spec:
                farm_id = catalog_spec.get("farm_id", farm_id)
                farm_name = catalog_spec.get("farm_name", farm_name)
                farm_city = catalog_spec.get("farm_city", farm_city)
                farm_state = catalog_spec.get("farm_state", farm_state)
                pivot_name = catalog_spec.get("equip_name", pivot_name)
                maker = catalog_spec.get("maker", maker)
                model = catalog_spec.get("model", model)
                nom_pressure = float(catalog_spec.get("nominal_pressure") or nom_pressure)
                radius = float(catalog_spec.get("radius") or radius)
                flow = float(catalog_spec.get("flow_rate") or flow)
                area = float(catalog_spec.get("area") or area)
            else:
                con = duckdb.connect(str(settings.duckdb_path), read_only=True)
                specs = con.execute(f"""
                    SELECT farm_name, pivot_name, pivot_maker, pivot_model, nominal_pressure, pivot_radius, flow_rate
                    FROM v_gold_metrics
                    WHERE id_equip = {target_id}
                    LIMIT 1
                """).fetchone()
                con.close()
                if specs:
                    farm_name = specs[0] or farm_name
                    pivot_name = specs[1] or pivot_name
                    maker = specs[2] or maker
                    model = specs[3] or model
                    nom_pressure = float(specs[4]) if specs[4] else nom_pressure
                    if nom_pressure > 10.0:
                        nom_pressure = round(nom_pressure / 10.0, 2)
                    radius = float(specs[5]) if specs[5] else radius
                    flow = float(specs[6]) if specs[6] else flow
        except Exception as e:
            logger.warn("catalog_spec_query_fallback", error=str(e))

        baseline = []
        angle = 0.0
        for _i in range(360):
            baseline.append({
                "id_farm": farm_id,
                "id_equip": target_id,
                "farm_name": farm_name,
                "farm_city": farm_city,
                "farm_state": farm_state,
                "pivot_name": pivot_name,
                "pivot_maker": maker,
                "pivot_model": model,
                "nominal_pressure": nom_pressure,
                "pivot_radius": radius,
                "area": area,
                "timestamp": datetime.now().isoformat(),
                "current_angle": round(angle, 1),
                "direction": "Forward",
                "running_status": "Running",
                "water_mode": "Wet",
                "percent_timer": 65.0,
                "pressure_begin": round(nom_pressure - 0.1, 2),
                "pressure_end": round(nom_pressure * 0.82, 2),
                "flow_rate": flow,
            })
            angle = (angle + 1.0) % 360.0

        self.telemetry_history = baseline
        self.current_index = 0
        logger.info(
            "telemetry_series_loaded",
            equip_id=target_id,
            pivot_name=pivot_name,
            farm_name=farm_name,
            total_records=len(baseline),
        )
        return len(baseline)

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
                # Keep active until operator clears or approves

            elif self.injected_anomaly == "sensor_spike":
                raw_item["percent_timer"] = 150.0  # Physically impossible percent timer
                self.injected_anomaly = None

            event = TelemetryEvent(
                id_farm=int(raw_item.get("id_farm") or 1515),
                id_equip=int(raw_item.get("id_equip") or 14863),
                farm_name=raw_item.get("farm_name") or "VB Homestead",
                farm_city=raw_item.get("farm_city") or "Sunnyside",
                farm_state=raw_item.get("farm_state") or "WA",
                pivot_name=raw_item.get("pivot_name") or "Haak 1",
                pivot_maker=raw_item.get("pivot_maker") or "Valmont",
                pivot_model=raw_item.get("pivot_model") or "Valley 8000C",
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
                area=float(raw_item.get("area") or 45.0),
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

            # Record event in drift monitor
            drift_monitor.record_event(event)

            payload = {
                "telemetry": event.model_dump(),
                "anomaly": report.model_dump(),
                "drift": drift_monitor.evaluate_drift(),
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
            if self.active_anomaly_report:
                self.active_anomaly_report.is_anomaly = False
                self.active_anomaly_report.requires_operator_approval = False
                self.active_anomaly_report.anomaly_types = []
            logger.warn("hitl_action_rejected_by_operator", ticket_id=ticket_id)
            return {"status": "REJECTED", "message": "Intervenção cancelada pelo operador humano."}

    async def switch_equipment(self, equip_id: int) -> dict[str, Any]:
        """Switches the actively monitored equipment dynamically across the entire fleet."""
        async with self.lock:
            self.load_telemetry_series(equip_id=equip_id)
            self.previous_event = None
            self.current_event = None
            self.active_anomaly_report = None
            self.pending_hitl_ticket = None
            self.injected_anomaly = None

        # Advance one tick to populate current_event and broadcast to WebSockets
        payload = await self.advance_tick()
        catalog_spec = asset_catalog.get_equipment_by_id(equip_id)
        logger.info("equipment_switched_successfully", equip_id=equip_id)
        return {
            "status": "SUCCESS",
            "equip_id": equip_id,
            "catalog_spec": catalog_spec,
            "telemetry": payload.get("telemetry"),
            "anomaly": payload.get("anomaly"),
        }


state_manager = TelemetryStateManager()
