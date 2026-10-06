# 🤖 Catálogo de IA, Model Context Protocol (MCP) & Ferramentas Operacionais

Este documento funciona como o contrato canônico de consumo para agentes de IA (Antigravity, Cursor, Claude Code, agentes autônomos) integrados ao ecossistema do **Industrial-MCP**.

---

## 1. Transporte & Conexão do Servidor MCP
* **Interface:** FastMCP (Protocolo Oficial Model Context Protocol)
* **Transporte:** HTTP Server-Sent Events (SSE)
* **Endpoint de Conexão:** `http://localhost:8000/mcp`
* **Healthcheck:** `http://localhost:8000/healthz`

---

## 2. Catálogo Canônico de MCP Resources
Os *Resources* permitem que modelos de IA leiam o estado atual do parque de irrigação sem gastar tokens com raciocínio ou chamadas de ferramentas:

| URI do Recurso | Tipo MIME | Descrição | Origem dos Dados |
| :--- | :--- | :--- | :--- |
| `telemetry://status` | `application/json` | Visão agregada do estado operacional dos pivôs e alarmes ativos. | View DuckDB `v_pivot_gold_metrics` |
| `telemetry://sensors` | `application/json` | Amostra em tempo real das últimas 100 leituras de sensores e telemetria. | View DuckDB `v_pivot_telemetry` |

---

## 3. Catálogo Canônico de MCP Tools (`@mcp.tool`)
Ferramentas expostas aos agentes de IA para diagnóstico analítico e controle de campo:

### 3.1 `get_pivots_list`
* **Descrição:** Retorna a lista completa de pivôs centrais e sistemas de aspersão cadastrados no sistema.
* **Parâmetros:** Nenhum.
* **Retorno:** `List[str]` com identificadores de equipamentos.

### 3.2 `get_pivot_telemetry`
* **Descrição:** Recupera séries temporais de telemetria higienizada (pressão, corrente, vibração, velocidade angular) para um pivô específico.
* **Parâmetros:**
  * `equip_id` (`str`, obrigatório): Identificador do pivô (ex: `"PIVO_01"`).
  * `limit` (`int`, opcional, default=100): Quantidade máxima de registros retornados.
* **Retorno:** `List[Dict[str, Any]]` com telemetrias ordenadas cronologicamente.

### 3.3 `predict_anomalies_batch`
* **Descrição:** Executa inferência em lote com o modelo *Isolation Forest* (System 1) para diagnosticar anomalias eletromecânicas recentes.
* **Parâmetros:**
  * `equip_id` (`str`, obrigatório): Identificador do pivô a diagnosticar.
  * `limit` (`int`, opcional, default=50): Número de eventos recentes para inferência.
* **Retorno:** `Dict[str, Any]` contendo:
  * `total_analyzed`: Quantidade de amostras avaliadas.
  * `anomalies_detected`: Número de anomalias encontradas.
  * `anomaly_rate`: Percentual de anomalia na janela.
  * `details`: Lista de eventos suspeitos com escore e alertas de domínio.

### 3.4 `emergency_stop_pivot` ⚠️ (Human-in-the-Loop)
* **Descrição:** Emite ordem de parada emergencial e despressurização para o PLC do pivô.
* **Política de Segurança:** **Exige aprovação humana explícita (HITL)**. Se `confirm=False`, a ferramenta aborta a execução e solicita que o agente peça confirmação do operador humano.
* **Parâmetros:**
  * `equip_id` (`str`, obrigatório): Identificador do pivô.
  * `reason` (`str`, obrigatório): Motivo técnico da parada (ex: *"Sobrecarga térmica e queda súbita de pressão"*).
  * `confirm` (`bool`, obrigatório, default=False): Flag de autorização explícita do operador humano.
* **Retorno:** `Dict[str, str]` com status da ordem de parada e `audit_trace_id`.

---

## 4. Prompts de Sistema & Diretrizes para Agentes de IA
1. **Priorize Resources antes de Tools:** Para checar status ou leituras gerais, consulte primeiro `telemetry://status` antes de disparar ferramentas analíticas.
2. **Nunca Force Paradas Críticas sem Confirmação:** O agente deve sempre descrever o diagnóstico para o usuário humano e obter consentimento inequívoco antes de chamar `emergency_stop_pivot(confirm=True)`.
3. **Respeito à LGPD:** Nunca solicite ou gere dados pessoais de operadores nas interações; utilize apenas os identificadores técnicos sanitizados.
