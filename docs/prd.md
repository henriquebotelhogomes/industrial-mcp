# 📄 PRD: Industrial-MCP (Telemetria & Copiloto Industrial para Pivôs de Irrigação)

> **Documento de Requisitos de Produto (PRD)**  
> **Status:** Aprovado para Engenharia (Tier 2 Enterprise)  
> **Autor:** Especialista II - Automação e IA  
> **Versão:** 1.0.0  

---

## 1. Visão Executiva & Contexto de Negócio

### 1.1 O Desafio Operacional
A operação contínua de pivôs centrais e sistemas de irrigação pressurizada (aspersores, gotejamento, microaspersão e sistemas lineares) enfrenta três gargalos críticos:
1. **Falhas Eletromecânicas Catastróficas:** Quedas súbitas de pressão de água combinadas com sobrecarga de corrente nos motores dos lances causam travamentos de torre, desagregação estrutural e desperdício massivo de água/energia.
2. **Dados Ruidosos e Desconexão de Campo:** Dados telemétricos de sensores de solo, condutividade e pressostatos sofrem com intermitência de telemetria, valores nulos e corrupção de pacotes.
3. **Isolamento de Modelos de IA:** Modelos preditivos tradicionais operam isolados da sala de controle, exigindo intervenção manual e gerando alta latência de resposta.

### 1.2 A Solução Proposta
O **Industrial-MCP** integra **Automação Industrial (PLC/SCADA)**, **Machine Learning em Streaming (MLOps)** e o **Model Context Protocol (MCP)** em uma arquitetura unificada de dois níveis (*System 1 Reflexivo* sub-10ms e *System 2 Deliberativo* via LLM com Human-in-the-Loop).

---

## 2. Personas & Stakeholders

| Persona | Papel | Dores Principais | Valor Entregue pelo Produto |
| :--- | :--- | :--- | :--- |
| **Carlos Mendes** *(Operador de Campo / SCADA)* | Monitora status dos pivôs e executa paradas preventivas. | Excesso de alarmes falsos e telas lentas sem atualização contínua. | Painel SCADA polar em tempo real com WebSockets e alarmes com índice de severidade claro. |
| **Mariana Souza** *(Engenheira de Confiabilidade & Automação)* | Investiga quebras de equipamentos e gerencia rotinas de manutenção. | Falta de rastreabilidade temporal e histórico fragmentado em SQLs legados. | Arquitetura Medallion em DuckDB/Parquet e DLQ segregada para análise forense imediata. |
| **Roberto Antunes** *(Diretor de Operações & FinOps)* | Responsável por custos de energia, água e uptime da fazenda. | Custos astronômicos de chamadas de LLM em nuvem e downtime não planejado. | Detecção reflexiva local a custo zero ($0.00/inferência) e projeção clara de FinOps via `POC_VERDICT.md`. |

---

## 3. Requisitos Funcionais (RF)

* **RF-01 (Ingestão & Lakehouse Medallion):** O sistema deve ingerir históricos brutos de sistemas de irrigação (Bronze), deduplicar e padronizar séries temporais (Silver) e computar agregados horários/diários (Gold) em DuckDB e Parquet.
* **RF-02 (Tratamento de Dados Corrompidos via DLQ):** Eventos com corrupção de schema, pressões negativas ou temperaturas fisicamente impossíveis devem ser desviados para `dlq_sensor_events.parquet` com registro da violação.
* **RF-03 (Detecção de Anomalias sub-10ms em Streaming):** O pipeline analítico deve avaliar cada leitura de telemetria (pressão, corrente, vibração, velocidade angular) contra um modelo *Isolation Forest* treinado com *Temporal Split*, calculando score de anomalia contínuo.
* **RF-04 (Servidor MCP SSE / FastMCP):** O sistema deve expor recursos (`telemetry://status`, `telemetry://sensors`) e ferramentas operacionais (`get_pivots_list`, `get_pivot_telemetry`, `predict_anomalies_batch`, `emergency_stop_pivot`) no endpoint padronizado `/mcp`.
* **RF-05 (Human-in-the-Loop para Ações de Risco):** Ferramentas com impacto físico (ex: `emergency_stop_pivot`) exigem confirmação explícita do operador humano (`confirm=True`) antes de emitir a ordem para o controlador.
* **RF-06 (SCADA Dashboard em Tempo Real):** Interface web moderna (HTML5 + Tailwind CSS + Highcharts + WebSockets) com renderização polar de pivôs e gráficos de séries temporais contínuas.

---

## 4. Requisitos Não-Funcionais (RNF)

* **RNF-01 (Latência de Inferência):** A inferência do modelo de anomalia deve processar em tempo de execução $p95 < 10\text{ms}$ por evento.
* **RNF-02 (Disponibilidade & Confiabilidade):** O serviço deve manter disponibilidade $\ge 99.5\%$ (conforme estipulado no SLO de SRE).
* **RNF-03 (Segurança & LGPD):** Identificadores de operadores, fazendas e dados sensíveis devem ser pseudonimizados de forma determinística (`ANON_...`) antes de serem expostos a agentes de IA ou logs.
* **RNF-04 (Observabilidade Estruturada):** Logs estruturados em formato JSON via `structlog`, injetando obrigatoriamente `trace_id` e `equip_id`.
* **RNF-05 (Arquitetura Zero-Daemon):** Persistência e processamento OLAP utilizando DuckDB e Parquet colunar sem necessidade de banco de dados cliente-servidor pesado.

---

## 5. Indicadores-Chave de Desempenho (KPIs de Negócio)

1. **Redução de Paradas Não Programadas:** Redução projetada de **35%** nas falhas catastróficas por sobrecarga ou despressurização.
2. **Taxa de Falsos Positivos em Alarmes:** Manutenção de alarme falso abaixo de **4.2%** através da combinação de regras físicas de domínio + Isolation Forest.
3. **Eficiência de Recursos Hídricos e Elétricos:** Economia estimada de **18%** de energia elétrica por otimização do bombeamento fora de horário de ponta.
4. **Custo de IA (FinOps):** Redução de **92%** no custo de tokens ao utilizar o modelo reflexivo System 1 para triagem local antes de acionar modelos de linguagem.
