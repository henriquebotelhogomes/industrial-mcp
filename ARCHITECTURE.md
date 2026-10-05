# 🚜 Industrial-MCP: Copiloto & Watchdog de Telemetria Industrial com IA

> **Projeto Estratégico para Entrevista Técnica — Especialista II em Automação e IA (TODOS Empreendimentos / Cartão de TODOS)**  
> **Autor:** Henrique  
> **Data:** 05/10/2026  
> **Status:** Arquitetura Conceitual & Especificação Técnica Aprovada

---

## 1. Visão Geral do Projeto

Este projeto demonstra a concepção e implementação de uma arquitetura industrial moderna de ponta a ponta, conectando **sistemas de controle em campo (PLC/SCADA)**, **Engenharia de Dados em Streaming**, **Machine Learning (MLOps)** e o protocolo **Model Context Protocol (MCP)** para interação segura com modelos de Inteligência Artificial Generativa.

O sistema utiliza dados reais de telemetria industrial de campo (provenientes de gateways WAGNET, BaseStation e Metos da operação de pivôs centrais e sondas multinível de solo da Valmont), demonstrando o tratamento em tempo real de anomalias físicas e operacionais de alta complexidade.

---

## 2. Aderência aos Requisitos da Vaga (Especialista II)

| Requisito da Vaga | Implementação no Projeto |
| :--- | :--- |
| **Liderança em Automação Industrial & PLC/SCADA** | Ingestão e interpretação de estados de máquina, comandos de bomba (`waterMode`, `pump`), percentímetro de CLP (`PercentTimer`) e grandezas angulares ($0^\circ - 360^\circ$). |
| **Model Context Protocol (MCP)** | Servidor oficial **FastMCP** expondo Resources auditáveis (`telemetry://...`) e Tools de diagnóstico/intervenção para clientes de IA. |
| **Segurança Cibernética & Estabilidade Sistêmica** | Validação estrita via Pydantic v2 contra injeções de payload, isolamento de comandos críticos e padrão **Human-in-the-Loop (HITL)** para ações com efeito colateral em equipamentos físicos. |
| **Machine Learning & MLOps** | Detecção de anomalias com **Isolation Forest**, prevenção estrita de *Data Leakage* por split temporal, telemetria em `.parquet` e Dead Letter Queue (DLQ) para dados corrompidos. |
| **Experiência Sólida em Python** | Backend assíncrono com **FastAPI**, ciclo de vida via `@asynccontextmanager lifespan`, tipagem estrita e empacotamento moderno via **`uv` (PEP 621)**. |
| **Orquestração de APIs Complexas & Streaming** | Pipeline de streaming reativo em tempo real via **WebSockets**, integrando dados heterogêneos de clima, solo e maquinário. |
| **Interface Visual Operacional (Full-Stack)** | Dashboard web moderno (HTML5/Tailwind/WebSockets) simulando o painel supervisório SCADA com visualização polar do pivô e aprovação de comandos. |

---

## 3. O Dataset Real de Campo (`apis_raw_data.sql`)

O projeto consome a base real de 28.2 MB localizada em `D:\apis_raw_data\apis_raw_data.sql`, contendo **15.002 registros reais**:
* **Equipamentos:** 10.360 registros de Pivôs Centrais (`type_equip = 3`), além de gotejamento e carretéis.
* **APIs de Origem:** WAGNET (14.611), BaseStation (375) e Metos (16).
* **Tipos de Dados:** Chuva (Rainfall), Irrigação (Irrigation) e Umidade do Solo (Soil Humidity).
* **Variáveis Industriais Extraídas:**
  - `PivotCurrentPosition`: Posição angular instantânea em graus;
  - `PivotDirection`: Sentido do encoder (`Forward` vs `Reverse`);
  - `PivotRunningStatus`: Estado do motor (`Running`, `Stopped`);
  - `DegreesTravelled` / `PercentTimer`: Velocidade e avanço da última torre;
  - `FlowRateMeter` / `TotalFlowMeter`: Taxas de vazão e hidrometria;
  - `PressureBeginValue` / `PressureEndValue`: Pressão de linha na base e ponta;
  - `s1..s9` & `smtemp1..smtemp9`: Umidade e temperatura do solo em 9 profundidades (AquaTrac / Sentek D&D).

---

## 4. As Regras de Domínio Físico (Herança dos Coletores PHP)

O projeto transpõe e aprimora as regras físicas e filtros determinísticos originalmente implementados nos coletores legados de produção:

1. **Aritmética Polar e Quebra do Ângulo Zero (`Readings_Irrigation.php`):**
   - Resolução da descontinuidade quando o pivô cruza de $359^\circ$ para $1^\circ$, fatiando o movimento em sub-slices e invertendo os ângulos quando no sentido anti-horário (`Reverse`).
2. **Validação Cruzada de Irrigação (Bomba vs Pressão):**
   - Mitigação de falsos positivos de irrigação: se `WaterMode == 'Wet'` ou `pump == 1`, mas a pressão medida está abaixo da `min_pressure`, o status de irrigação real é forçado para $0$ e um alerta de anomalia mecânica é gerado.
3. **Normalização Sensorial e Rejeição de Ruídos (`Readings_SoilMoisture.php` e `Readings_Weather.php`):**
   - Conversão de temperaturas em Fahrenheit para Celsius: $(T - 32) / 1.8$;
   - Conversão de velocidade de vento de $mph$ para $m/s$;
   - Tratamento de estações meteorológicas com falha transitória (radiação, temperatura e umidade zerados simultaneamente são roteados para a DLQ).

---

## 5. Arquitetura em Camadas do Novo Projeto

```
D:\apis_raw_data\
├── GEMINI.md                    # Diretrizes normativas locais de governança (Harness Antigravity)
├── AGENTS.md                    # Shim universal para portabilidade de agentes
├── ARCHITECTURE.md              # Este documento de especificação técnica e arquitetura
├── pyproject.toml               # Manifesto de dependências PEP 621 gerenciado via uv
├── src/
│   ├── config.py                # Configurações com Pydantic Settings (Fail-Fast)
│   ├── data/
│   │   ├── ingest_sql.py        # Extrator e conversor do dump SQL para Parquet Bronze
│   │   ├── medallion.py         # Pipeline Medallion (Bronze -> Silver -> Gold) com DuckDB/Polars
│   │   └── streamer.py          # Simulador assíncrono de streaming de telemetria em tempo real
│   ├── ml/
│   │   ├── domain_rules.py      # Filtros determinísticos e leis físicas invioláveis
│   │   ├── anomaly_detector.py  # Modelo de detecção de anomalias (Isolation Forest)
│   │   └── drift_monitor.py     # Monitor de Data Drift e integridade de sinal
│   ├── mcp/
│   │   ├── server.py            # Servidor FastMCP oficial (SSE/HTTP)
│   │   ├── tools.py             # Ferramentas (@mcp.tool) com schemas Pydantic e HITL
│   │   └── resources.py         # Recursos (@mcp.resource) com URIs declarativas
│   └── web/
│       ├── app.py               # Aplicação FastAPI assíncrona (WebSockets + REST + Scalar + StaticFiles)
│       └── static/
│           ├── index.html       # Dashboard SCADA Operacional em tempo real
│           ├── app.js           # Cliente WebSocket e renderizador visual Highcharts
│           └── styles.css       # Layout moderno e reativo com Tailwind CSS
```

### 5.1 O Motor de Streaming e o Painel de Controle de Demonstração
* **Replay de Telemetria com Controle Total**: O backend processa os dados reais e emite eventos via WebSocket com controles interativos na UI:
  - Botão `[Play / Pause]`: Permite iniciar e pausar a emissão do stream quando o apresentador desejar.
  - Seletor de Velocidade (`1x`, `2x`, `5x`, `10x`): Aceleração do tempo da série temporal.
  - Botões de Gatilho de Anomalias (`Injetar Salto Angular`, `Forçar Queda de Pressão`): Permite ao apresentador demonstrar a detecção em tempo real e a ativação do servidor MCP exatamente no momento planejado da narrativa.
* **Visualização com Highcharts**:
  - **Highcharts Polar / Gauge**: Renderização do pivô central girando em 360° com arco de setor irrigado.
  - **Highcharts Spline (Time-Series)**: Gráfico contínuo em tempo real com curvas de umidade, temperatura e pressão.

---

## 6. O Roteiro de Demonstração na Entrevista Técnica (3 a 5 minutos)

1. **Abertura e Contexto de Negócio:**
   - Explicar a vivência real com dados industriais da Valmont e como esse protótipo resolve os problemas de telemetria de campo que quebram automações ingênuas.
2. **Execução do Sistema (`uv run python -m src.web.app`):**
   - Abrir o navegador em `http://localhost:8000`;
   - Mostrar os pacotes de telemetria chegando via WebSocket em tempo real e o pivô girando no gráfico polar;
   - Demonstrar a detecção em menos de 5ms das 3 anomalias reais (salto de encoder, falso positivo de bomba e leitura espúria de sensor).
3. **Interação com a Inteligência Artificial via MCP:**
   - Demonstrar o modelo de IA consumindo o `Resource` auditável do MCP;
   - Demonstrar a chamada da `Tool` de diagnóstico com score de anomalia;
   - Demonstrar o **Human-in-the-Loop**: a IA solicita a parada da bomba por segurança, e o painel exibe um pop-up exigindo aprovação manual do operador para confirmar o comando no CLP.
4. **Encerramento Técnico (Inversão da Mesa):**
   - Questionar os entrevistadores sobre como está estruturado o gateway de supervisório e governança de IA hoje na TODOS Empreendimentos.
