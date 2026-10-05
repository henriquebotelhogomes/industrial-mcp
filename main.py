"""Root entrypoint to run the Industrial-MCP SCADA Dashboard & API."""

import uvicorn

from src.config import settings

if __name__ == "__main__":
    print(f"\n🚜 Iniciando Industrial-MCP na porta {settings.port}...")
    print(f"👉 Painel SCADA: http://{settings.host}:{settings.port}")
    print(f"👉 Scalar API Docs: http://{settings.host}:{settings.port}/docs\n")
    uvicorn.run("src.web.app:app", host=settings.host, port=settings.port, reload=False)
