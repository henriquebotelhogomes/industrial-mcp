# 🧠 Diretrizes de Engenharia: AI Engineer, Agentes, Automação & MLOps (Tier 2)

> **Regras Normativas Locais (Harness Antigravity)** — Especializado para o Projeto Industrial-MCP, Telemetria de Pivôs/Sensores, Sistemas de Controle (PLC/SCADA), MLOps e Model Context Protocol (MCP).

---

## 1. Stack & Padrões Normativos do Backend (Python)
* **Gerenciador & Ambiente:** Uso obrigatório de **`uv`** com **`pyproject.toml`** (padrão oficial PEP 621) e lockfile determinístico (`uv.lock`). Proibido `setup.py` ou `requirements.txt` solto.
* **Framework Web & Lifespan:** **FastAPI** assíncrono. Clientes de LLM, conexões de streaming e brokers devem ser inicializados e finalizados estritamente via **`@asynccontextmanager lifespan`**. Proibido usar eventos legados `@app.on_event`.
* **Structured Outputs & Schema Enforcement:** Validação estrita via **Pydantic v2**, garantindo validação fail-fast de parâmetros de telemetria e contratos das ferramentas de IA.
* **Armazenamento Analítico & OLAP Local (Zero-Daemon):**
  * **`DuckDB` + `polars`**: Para ingestão e consultas analíticas ultrarrápidas sobre os dados de telemetria particionados em **`.parquet`**.
  * **Arquitetura Medallion**: Bronze (append-only bruto), Silver (limpo e deduplicado) e Gold (métricas operacionais).
* **Documentação de API:** **Scalar obrigatório** servido em `/docs` ou `/api/docs`. Proibido Swagger UI clássico.
* **Logging Estruturado:** **`structlog`** (formato JSON) injetando obrigatoriamente `trace_id`, `timestamp` e `equip_id`.

---

## 2. Arquitetura Model Context Protocol (MCP) & IA Operacional
* **Servidor MCP Oficial:** Construído via interface **FastMCP** em Python (`mcp[cli]>=1.2.0`), operando via transporte SSE/Stream HTTP para comunicação com agentes de IA.
* **A Tríade Canônica do MCP:**
  * **Resources (`telemetry://...`)**: Exposição de dados de leitura auditáveis e limpos dos pivôs e sensores de solo sem gastar tokens de raciocínio da LLM.
  * **Tools (`@mcp.tool`)**: Ferramentas ativas de diagnóstico e inferência de machine learning.
  * **Human-in-the-Loop (HITL)**: Ferramentas com efeito colateral operacional (como comandos de parada ou intervenção na bomba/pivô) exigem aprovação explícita do operador humano antes do envio ao sistema de controle (PLC/SCADA).

---

## 3. MLOps & Detecção de Anomalias em Streaming
* **Prevenção de Data Leakage**: Divisão estritamente temporal da série de dados antes de qualquer ajuste estatístico ou treino.
* **Modelagem Leve & Baixa Latência**: Modelos de detecção de anomalias (Isolation Forest / Z-Score Robusto) com tempo de inferência sub-10ms.
* **Dead Letter Queue (DLQ)**: Dados corrompidos ou com violação física absoluta (ex: temperaturas extremas espúrias) são desviados para `dlq_sensor_events` para auditoria.

---

## 4. Frontend & Observabilidade em Tempo Real
* **Padrão Web Moderno (Proibido Streamlit)**: Dashboard operacional construído como **Single Page Application (HTML5 + Tailwind CSS + WebSockets Nativos)** servida diretamente pelo FastAPI (`StaticFiles`).
* **Gráficos & Visualização Industrial**: Uso de **Highcharts** (Highcharts Core + Highcharts More / Polar) para renderização de séries temporais contínuas e gráficos polares circulares de pivô em tempo real.
* **Evidência de Entrega (Anti-Vibe-Coding)**: Todas as implementações devem ser validadas no terminal antes de serem concluídas (`ruff check`, testes determinísticos com `pytest`).
