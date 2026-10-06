param(
    [Parameter(Position=0)]
    [string]$Target = "help"
)

switch ($Target.ToLower()) {
    "install" {
        uv sync --all-extras
    }
    "lint" {
        uv run ruff check .
        uv run mypy src
    }
    "test" {
        uv run pytest -v
    }
    "run" {
        uv run uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload
    }
    "docs" {
        uv run mkdocs serve
    }
    "docker-build" {
        docker build -t industrial-mcp:latest .
    }
    default {
        Write-Host "Industrial-MCP Automation Helper (Windows PowerShell):" -ForegroundColor Cyan
        Write-Host "  .\make run          - Inicia a API FastAPI, SCADA e FastMCP com hot-reload" -ForegroundColor Green
        Write-Host "  .\make test         - Executa a suíte de testes com pytest" -ForegroundColor Green
        Write-Host "  .\make lint         - Executa checagem de tipos (mypy) e linter (ruff)" -ForegroundColor Green
        Write-Host "  .\make docs         - Serve a documentação interativa MkDocs Material" -ForegroundColor Green
        Write-Host "  .\make install      - Instala dependências do pyproject.toml via uv" -ForegroundColor Green
        Write-Host "  .\make docker-build - Constrói a imagem Docker de produção" -ForegroundColor Green
    }
}
