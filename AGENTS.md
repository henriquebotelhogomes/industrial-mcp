# Instruções do Projeto

Leia e siga estritamente o arquivo `GEMINI.md` deste diretório antes de codar. Ele é a fonte normativa canônica (Harness Antigravity).

---

# 🤖 Catálogo de IA, Model Context Protocol (MCP) & Ferramentas Operacionais

Este documento funciona como o contrato canônico de consumo para agentes de IA (Antigravity, Cursor, Claude Code, agentes autônomos) integrados ao ecossistema do **Industrial-MCP**.

## 1. Transporte & Conexão do Servidor MCP
* **Interface:** FastMCP (Protocolo Oficial Model Context Protocol)
* **Transporte:** HTTP Server-Sent Events (SSE)
* **Portal & Diagnóstico Web:** `http://localhost:8000/mcp` (Dashboard visual em HTML e metadados JSON com `Accept: application/json`)
* **Endpoint de Streaming SSE:** `http://localhost:8000/mcp/sse` (Canal unidirecional Server-Sent Events para clientes de IA)
* **Endpoint de Mensageria RPC:** `http://localhost:8000/mcp/messages` (Envio de chamadas de ferramentas e JSON-RPC do cliente)
* **Status da Aplicação:** `http://localhost:8000/api/status`

---

## 2. Catálogo Canônico de MCP Resources
Os *Resources* permitem que modelos de IA leiam o estado atual do parque de irrigação sem gastar tokens com raciocínio ou chamadas de ferramentas:

| URI do Recurso | Tipo MIME | Descrição | Origem dos Dados |
| :--- | :--- | :--- | :--- |
| `telemetry://fleet/overview` | `application/json` | Visão agregada da frota: contagem de fazendas, pivôs ativos e alarmes de pressão. | View DuckDB `v_gold_metrics` |
| `telemetry://pivot/{pivot_id}/live` | `application/json` | Última telemetria higienizada do pivô (pressão, percentímetro, ângulo, vazão). | Cache de memória ou DuckDB `v_gold_metrics` |
| `telemetry://pivot/{pivot_id}/specs` | `application/json` | Ficha técnica de engenharia de fábrica (raio, fabricante, vazão nominal, tempo de volta). | DuckDB `read_parquet(bronze/pivocentral.parquet)` |

---

## 3. Catálogo Canônico de MCP Tools (`@mcp.tool`)
Ferramentas expostas aos agentes de IA para diagnóstico analítico e controle de campo:

### 3.1 `diagnose_equipment`
* **Descrição:** Diagnostica o estado operacional do pivô central usando regras físicas de domínio (Valmont) e modelo estatístico de detecção de anomalias (Isolation Forest / Z-Score).
* **Parâmetros:**
  * `pivot_id` (`int`, obrigatório): Identificador numérico do pivô (ex: `14863`).
  * `current_angle` (`float`, obrigatório): Ângulo azimutal atual do pivô em graus (0° a 360°).
  * `pressure_begin` (`float`, obrigatório): Pressão manométrica no centro em bar.
  * `percent_timer` (`float`, obrigatório): Regulagem do percentímetro de velocidade (0% a 100%).
  * `water_mode` (`str`, obrigatório): Modo operacional (`"Com Agua"` ou `"Sem Agua"`).
  * `previous_angle` (`float`, opcional): Leitura anterior para cálculo de velocidade e salto de encoder.
* **Retorno:** JSON string contendo `is_anomaly`, `anomaly_score`, `flags` e diagnóstico textual.

### 3.2 `request_emergency_stop` ⚠️ (Human-in-the-Loop)
* **Descrição:** Emite solicitação de desenergização e parada de emergência do pivô e desligamento da motobomba.
* **Política de Segurança:** **Exige aprovação humana explícita (HITL)**. Se `operator_confirmed=False`, a ferramenta bloqueia a escrita no PLC, gera um chamado formal de segurança com `ticket_id` e solicita que o agente instrua o operador a confirmar na console SCADA.
* **Parâmetros:**
  * `pivot_id` (`int`, obrigatório): Identificador do pivô.
  * `reason` (`str`, obrigatório): Justificativa técnica da parada de emergência.
  * `operator_confirmed` (`bool`, obrigatório, default=False): Flag de autorização explícita do operador humano.
* **Retorno:** JSON string contendo `status` (`PENDING_OPERATOR_APPROVAL` ou `APPROVED_AND_EXECUTED`), `ticket_id` e rastreamento de auditoria.

### 3.3 `calculate_application_depth`
* **Descrição:** Calcula a lâmina d'água bruta e líquida aplicada ($mm$ por revolução) com base na vazão nominal, percentímetro e geometria do pivô.
* **Parâmetros:**
  * `pivot_radius_meters` (`float`, obrigatório): Raio da última torre em metros.
  * `flow_rate_m3h` (`float`, obrigatório): Vazão volumétrica nominal do pivô em $m^3/h$.
  * `percent_timer` (`float`, obrigatório): Posição do percentímetro (0.1% a 100%).
  * `efficiency_fraction` (`float`, opcional, default=0.88): Eficiência da aspersão (fração entre 0 e 1).
* **Retorno:** JSON string contendo área irrigada em hectares, tempo por volta completa em horas e lâminas aplicadas ($mm$).

---

## 4. Prompts de Sistema & Diretrizes para Agentes de IA
1. **Priorize Resources antes de Tools:** Para consultar métricas ou especificações de engenharia, consulte primeiro `telemetry://fleet/overview` ou `telemetry://pivot/{pivot_id}/specs` antes de acionar ferramentas analíticas.
2. **Nunca Force Paradas Críticas sem Confirmação:** O agente de IA deve sempre expor o diagnóstico para o operador humano e solicitar confirmação inequívoca antes de acionar `request_emergency_stop(operator_confirmed=True)`.
3. **Respeito à LGPD:** Nunca solicite ou gere dados pessoais de operadores nas interações; utilize apenas identificadores técnicos sanitizados.
