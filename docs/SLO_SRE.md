# 📊 Especificação de SLOs, SLIs & Error Budget (SRE Tier 2)

> **Projeto:** Industrial-MCP  
> **Serviço:** Telemetria SCADA, API FastAPI e Servidor FastMCP/MCPServer

---

## 1. Service Level Indicators (SLIs) e Service Level Objectives (SLOs)

| Indicador (SLI) | Métrica | Objetivo (SLO) | Janela de Aferição |
| :--- | :--- | :--- | :--- |
| **Disponibilidade da API REST & MCP** | Proporção de requisições HTTP 2xx/3xx sobre total (excluindo 4xx de cliente). | $\ge 99.5\%$ | Janela móvel de 30 dias |
| **Latência de Inferência de Anomalias** | Duração do ciclo de avaliação `detector.evaluate(...)`. | $\text{p95} < 10\text{ ms}$ | Janela móvel de 7 dias |
| **Latência do Stream WebSocket** | Tempo de envio de tick para todos os assinantes conectados. | $\text{p99} < 50\text{ ms}$ | Janela móvel de 7 dias |
| **Integridade de Ingestão Medallion** | Proporção de eventos válidos processados ou roteados para DLQ sem perda silenciosa. | $100\%$ | Diária |

---

## 2. Política de Error Budget & Deploy Freeze

* **Orçamento Mensal de Erro:** $0.5\%$ de indisponibilidade permitida ($\approx 3.6$ horas/mês).
* **Política de Consumo de Error Budget:**
  - **Queima $\le 20\%$ em 24h:** Operação nominal; deploys e releases contínuos permitidos.
  - **Queima entre $20\%$ e $50\%$ em 24h:** Alerta amarelo; deploys restritos a correções de bugs.
  - **Queima $> 50\%$ em 24h:** **DEPLOY FREEZE IMEDIATO**. Todo o esforço de engenharia é direcionado para estabilização, confiabilidade e análise de causa-raiz.
