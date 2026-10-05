"""Root entrypoint to run the Industrial-MCP SCADA Dashboard & API."""

import sys

import uvicorn

from src.config import settings

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    print(f"\n[Industrial-MCP] Iniciando servidor na porta {settings.port}...")
    print(f"-> Painel SCADA: http://{settings.host}:{settings.port}")
    print(f"-> Scalar API Docs: http://{settings.host}:{settings.port}/docs\n")
    uvicorn.run("src.web.app:app", host=settings.host, port=settings.port, reload=False)
