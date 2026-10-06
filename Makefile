.PHONY: install lint test run docs docker-build clean help

help:
	@echo "Industrial-MCP Automation Commands:"
	@echo "  make install      - Instala dependências e ambiente virtual com uv"
	@echo "  make lint         - Executa ruff check e mypy para checagem estática"
	@echo "  make test         - Executa a suíte de testes automatizados com pytest"
	@echo "  make run          - Inicia a API FastAPI e servidor MCP com hot-reload"
	@echo "  make docs         - Compila e serve a documentação MkDocs Material"
	@echo "  make docker-build - Constrói a imagem Docker multi-stage de produção"

install:
	uv sync --all-extras

lint:
	uv run ruff check .
	uv run mypy src

test:
	uv run pytest -v

run:
	uv run uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload

docs:
	uv run mkdocs serve

docker-build:
	docker build -t industrial-mcp:latest .

clean:
	rm -rf __pycache__ .pytest_cache site dist
