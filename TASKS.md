# 📋 Backlog de Engenharia: Industrial-MCP (TASKS.md)

> **Quadro de Tarefas & Evolução Contínua**  
> **Status Geral:** Fase 1 a 5 Concluídas (100% Verde) | Fase 6 em Planejamento  
> **Padrão:** Tier 2 Enterprise (Antigravity Harness v1.5.2)  

---

## 🟢 Fase 1: Ingestão de Dados & Lakehouse Medallion
- [x] Extração e parseamento dos 7 arquivos legados de bancos SQL (`OLD_DB/*.sql`).
- [x] Criação da camada **Bronze** em formato colunar `.parquet` particionado.
- [x] Implementação do motor de higienização e validação de schema Pydantic v2.
- [x] Criação da camada **Silver** com séries temporais deduplicadas e padronizadas (`pivot_telemetry.parquet`).
- [x] Criação da camada **Gold** com métricas analíticas agregadas por hora/equipamento (`pivot_gold_metrics.parquet`).
- [x] Isolamento de dados corrompidos na **Dead Letter Queue (DLQ)** em `dlq_sensor_events.parquet`.
- [x] Catálogo e views no **DuckDB** local (`v_pivot_telemetry`, `v_pivot_gold_metrics`, `v_dlq_sensor_events`).

---

## 🟢 Fase 2: Inteligência Artificial, MLOps & Streaming Reflexivo (System 1)
- [x] Implementação de regras físicas de domínio (pressão crítica, sobrecorrente, vibração excessiva).
- [x] Pipeline de treinamento com **Divisão Temporal Estrita (Temporal Split 80/20)** para evitar vazamento de dados.
- [x] Modelo *Isolation Forest* com pré-processador robusto para detecção de anomalias com tempo de inferência $< 10\text{ms}$.
- [x] Monitor de **Data Drift** utilizando testes estatísticos Kolmogorov-Smirnov (KS-Test) e PSI.
- [x] Persistência segura do modelo treinado (`models/isolation_forest.joblib`).

---

## 🟢 Fase 3: Model Context Protocol (MCP) & Human-in-the-Loop
- [x] Servidor **FastMCP** oficial configurado com transporte SSE montado em `/mcp`.
- [x] MCP Resources (`telemetry://status`, `telemetry://sensors`) para leitura sem custo de tokens da LLM.
- [x] MCP Tools (`get_pivots_list`, `get_pivot_telemetry`, `predict_anomalies_batch`).
- [x] Implementação do protocolo **Human-in-the-Loop (HITL)** na ferramenta crítica `emergency_stop_pivot` (bloqueio sem confirmação explícita).

---

## 🟢 Fase 4: Governança, SRE, Observabilidade & Qualidade
- [x] Implementação de logging estruturado JSON via `structlog` com injeção automática de `trace_id` e `equip_id`.
- [x] Conformidade **LGPD**: Módulo de pseudonimização determinística (`ANON_...`) e K-anonymity.
- [x] Definição de métricas de SRE e política de Error Budget em [`docs/SLO_SRE.md`](file:///d:/apis_raw_data/docs/SLO_SRE.md).
- [x] Elaboração do runbook de postmortem blameless em [`INCIDENT_POSTMORTEM.md`](file:///d:/apis_raw_data/INCIDENT_POSTMORTEM.md).
- [x] Elaboração do veredito executivo e projeção de FinOps em [`POC_VERDICT.md`](file:///d:/apis_raw_data/POC_VERDICT.md).
- [x] Pipeline de CI/CD no GitHub Actions (`.github/workflows/ci.yml`) com scan de segurança Trivy e SBOM via Syft.
- [x] Suíte de testes automatizados com `pytest` (22 testes unitários e de integração passando).

---

## 🟢 Fase 5: Suíte de Governança Documental & DX (Harness v1.5.2)
- [x] Criação do documento de requisitos de produto [`PRD.md`](file:///d:/apis_raw_data/PRD.md).
- [x] Criação da especificação técnica unificada [`PROJECT_SPEC.md`](file:///d:/apis_raw_data/PROJECT_SPEC.md).
- [x] Criação do quadro de tarefas [`TASKS.md`](file:///d:/apis_raw_data/TASKS.md).
- [x] Criação do handover de sessão [`NEXT_STEPS.md`](file:///d:/apis_raw_data/NEXT_STEPS.md).
- [x] Expansão do [`AGENTS.md`](file:///d:/apis_raw_data/AGENTS.md) com catálogo formal de Tools e Resources do MCP.
- [x] Automação de DX com [`Makefile`](file:///d:/apis_raw_data/Makefile) na raiz.
- [x] Configuração do portal de manuais via MkDocs Material ([`mkdocs.yml`](file:///d:/apis_raw_data/mkdocs.yml) e pasta `docs/`).

---

## 🟢 Fase 6: Copiloto Deliberativo System 2 & Expansão SCADA (Concluída)
- [x] Implementação do agente deliberativo LangGraph (`src/agent/graph.py`) com checkpointer de memória multi-turno.
- [x] RAG Relacional estruturado sobre a base DuckDB (`src/agent/relational_rag.py`) com catálogo de especificações de fábrica.
- [x] Expansão do SCADA para interface de 2 abas (Aba 1: Supervisório Polar Highcharts; Aba 2: Chat Copiloto Operacional com atalhos).
- [x] Cards de FinOps e Ficha Técnica em tempo real no dashboard exibindo economia de 99.85% de tokens.
- [x] Modo Híbrido Resiliente garantindo zero travamentos na apresentação da entrevista ao vivo.
- [x] Suíte de testes automatizados com `pytest` expandida para 27 testes verdes (100% aprovados).
