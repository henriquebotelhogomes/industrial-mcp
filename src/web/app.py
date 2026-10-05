"""FastAPI application with native WebSockets, Scalar docs, and SCADA static files."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import settings
from src.core.logging import logger, setup_logging
from src.data.state import state_manager
from src.mcp.server import mcp_server

# ---------------------------------------------------------------------------
# Pydantic Schemas for Request/Response Contracts
# ---------------------------------------------------------------------------

class PlaybackControlRequest(BaseModel):
    is_playing: bool | None = None
    speed: float | None = Field(default=None, ge=0.1, le=20.0)


class AnomalyInjectionRequest(BaseModel):
    anomaly_type: str = Field(description="angle_jump, pressure_drop, or sensor_spike")


class HitlDecisionRequest(BaseModel):
    ticket_id: str
    operator_name: str = "Operator_Henrique"


class McpToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Background Telemetry Replay Worker
# ---------------------------------------------------------------------------

sim_task: asyncio.Task | None = None


async def telemetry_playback_loop() -> None:
    """Simulates real-time telemetry streaming at configurable clock rate."""
    logger.info("telemetry_playback_loop_started")
    try:
        while True:
            # Advance tick according to speed
            await state_manager.advance_tick()
            base_interval = settings.stream_tick_rate_ms / 1000.0
            sleep_time = max(0.1, base_interval / max(0.1, state_manager.speed))
            await asyncio.sleep(sleep_time)
    except asyncio.CancelledError:
        logger.info("telemetry_playback_loop_cancelled")
    except Exception as e:
        logger.error("telemetry_playback_loop_crashed", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan management for startup and graceful shutdown."""
    setup_logging(settings.log_level)
    logger.info("application_startup", app_name="Industrial-MCP", host=settings.host, port=settings.port)

    # Initialize telemetry replay state
    state_manager.load_telemetry_series()

    # Launch background simulation
    global sim_task
    sim_task = asyncio.create_task(telemetry_playback_loop())

    yield

    # Shutdown
    if sim_task:
        sim_task.cancel()
        try:
            await sim_task
        except asyncio.CancelledError:
            pass
    logger.info("application_shutdown_complete")


# ---------------------------------------------------------------------------
# FastAPI Application Declaration (No Classic Swagger per GEMINI.md)
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Industrial-MCP: Telemetria & IA Watchdog",
    description="Supervisório SCADA, Detecção de Anomalias (Isolation Forest) e Model Context Protocol (MCP).",
    version="1.0.0",
    docs_url=None,  # Disabled Swagger UI
    redoc_url=None,  # Disabled ReDoc
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Scalar API Documentation (Mandatory per GEMINI.md)
# ---------------------------------------------------------------------------

@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
@app.get("/api/docs", response_class=HTMLResponse, include_in_schema=False)
async def scalar_docs() -> HTMLResponse:
    """Serves high-density modern Scalar API documentation."""
    html_content = """
    <!doctype html>
    <html>
      <head>
        <title>Industrial-MCP // Scalar API Reference</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚜</text></svg>">
        <style>
          body { margin: 0; background-color: #0f172a; color: #f8fafc; }
        </style>
      </head>
      <body>
        <script
          id="api-reference"
          data-url="/openapi.json"
          data-configuration='{"theme": "deepSpace", "layout": "modern"}'
        ></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
      </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def get_current_status():
    """Returns the latest active pivot telemetry event and anomaly state."""
    return {
        "is_playing": state_manager.is_playing,
        "speed": state_manager.speed,
        "current_telemetry": state_manager.current_event.model_dump() if state_manager.current_event else None,
        "active_anomaly": state_manager.active_anomaly_report.model_dump() if state_manager.active_anomaly_report else None,
        "pending_hitl_ticket": state_manager.pending_hitl_ticket,
    }


@app.post("/api/control/playback")
async def control_playback(req: PlaybackControlRequest):
    """Controls simulation replay (play/pause and speed)."""
    if req.is_playing is not None:
        state_manager.is_playing = req.is_playing
    if req.speed is not None:
        state_manager.speed = req.speed
    return {"status": "SUCCESS", "is_playing": state_manager.is_playing, "speed": state_manager.speed}


@app.post("/api/control/inject-anomaly")
async def inject_anomaly(req: AnomalyInjectionRequest):
    """Allows operator to trigger simulated anomalies during technical demo."""
    await state_manager.inject_anomaly(req.anomaly_type)
    return {"status": "SUCCESS", "injected_anomaly": req.anomaly_type}


@app.post("/api/hitl/approve")
async def approve_hitl(req: HitlDecisionRequest):
    """Operator confirms emergency intervention (HITL) for PLC execution."""
    res = await state_manager.approve_hitl_action(req.ticket_id, req.operator_name)
    return res


@app.post("/api/hitl/reject")
async def reject_hitl(req: HitlDecisionRequest):
    """Operator rejects suggested intervention."""
    res = await state_manager.reject_hitl_action(req.ticket_id)
    return res


@app.get("/api/mcp/tools")
async def list_mcp_tools():
    """Lists registered Model Context Protocol tools and schemas."""
    tools = await mcp_server.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema,
        }
        for t in tools
    ]


@app.post("/api/mcp/tools/call")
async def call_mcp_tool(req: McpToolCallRequest):
    """Executes an MCP tool call."""
    try:
        result = await mcp_server.call_tool(req.tool_name, req.arguments)
        return {"status": "SUCCESS", "result": result}
    except Exception as e:
        logger.error("mcp_tool_execution_failed", error=str(e), tool=req.tool_name)
        raise HTTPException(status_code=400, detail=str(e)) from e


# ---------------------------------------------------------------------------
# WebSocket Endpoint: Real-time Reactive Streaming
# ---------------------------------------------------------------------------

@app.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    """Full-duplex WebSocket stream for live SCADA dashboard updates."""
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    state_manager.subscribers.add(queue)
    logger.info("websocket_client_connected", total_clients=len(state_manager.subscribers))

    # Send initial snapshot immediately
    if state_manager.current_event:
        await websocket.send_json({
            "telemetry": state_manager.current_event.model_dump(),
            "anomaly": state_manager.active_anomaly_report.model_dump() if state_manager.active_anomaly_report else None,
            "hitl_ticket": state_manager.pending_hitl_ticket,
            "is_playing": state_manager.is_playing,
            "speed": state_manager.speed,
        })

    async def receive_client_commands():
        try:
            while True:
                msg = await websocket.receive_json()
                action = msg.get("action")
                if action == "toggle_play":
                    state_manager.is_playing = not state_manager.is_playing
                elif action == "set_speed":
                    state_manager.speed = float(msg.get("speed", 1.0))
                elif action == "inject_anomaly":
                    await state_manager.inject_anomaly(msg.get("type", "angle_jump"))
                elif action == "approve_hitl":
                    await state_manager.approve_hitl_action(msg.get("ticket_id"))
                elif action == "reject_hitl":
                    await state_manager.reject_hitl_action(msg.get("ticket_id"))
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    receiver_task = asyncio.create_task(receive_client_commands())

    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except (WebSocketDisconnect, Exception):
        logger.info("websocket_client_disconnected")
    finally:
        state_manager.subscribers.discard(queue)
        receiver_task.cancel()


# ---------------------------------------------------------------------------
# Static Files & Dashboard Mounting
# ---------------------------------------------------------------------------

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>SCADA Dashboard inicializando...</h1>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.web.app:app", host=settings.host, port=settings.port, reload=True)
