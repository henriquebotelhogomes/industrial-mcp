# 🏭 Industrial-MCP: Telemetria de Pivôs & Copiloto Industrial

Bem-vindo ao portal de engenharia e documentação do projeto **Industrial-MCP**.

Este projeto implementa uma solução corporativa para monitoramento em tempo real de pivôs centrais e sistemas de irrigação pressurizada, combinando **Automação Industrial (PLC/SCADA)**, **Machine Learning em Streaming (MLOps)** e o **Model Context Protocol (FastMCP)** com salvaguardas **Human-in-the-Loop (HITL)**.

---

## 🧭 Guia Rápido de Navegação

* [📄 Requisitos de Produto (PRD)](prd.md): Personas, regras de negócio e metas operacionais.
* [🛠️ Especificação Técnica (Spec)](spec.md): Arquitetura detalhada, diagramas C4/Mermaid, ADRs e contratos Pydantic v2.
* [🤖 Catálogo MCP & Agentes](agents_mcp.md): Resources (`telemetry://...`) e Tools (`@mcp.tool`) disponíveis.
* [🧠 MLOps & Detecção de Anomalias](mlops.md): Pipeline com Temporal Split, Isolation Forest e monitor de Data Drift.
* [🛡️ Confiabilidade & SRE](SLO_SRE.md): Tabela de SLI/SLO, política de Error Budget e Deploy Freeze.
* [🚨 Postmortem de Incidentes](postmortem.md): Relatório pós-incidente blameless de contenção.
* [📊 Veredito da PoC & FinOps](poc_verdict.md): Projeção de custos e avaliação multi-modelo.

---

## ⚡ Comandos Rápidos de Execução (DX)

```bash
# Instalação com uv
make install

# Validação e testes
make lint
make test

# Iniciar servidor local
make run

# Compilar este portal de documentação
make docs
```
