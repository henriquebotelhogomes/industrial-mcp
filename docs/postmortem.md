# 🚨 Template Canônico de Postmortem Blameless (SRE Tier 2)

> **Projeto:** Industrial-MCP  
> **Status:** Modelo Normativo para Resolução de Incidentes Operacionais  
> **Filosofia:** Postmortem 100% blameless focado em resiliência estrutural de engenharia.

---

## 1. Resumo Executivo do Incidente

| Campo | Detalhes |
| :--- | :--- |
| **Identificador:** | INC-YYYYMMDD-001 |
| **Severidade:** | SEV-1 (Crítico) / SEV-2 (Alto) / SEV-3 (Médio) |
| **Equipamento(s) Afetado(s):** | Pivô Central ID / Farm ID |
| **Duração do Incidente:** | HH:MM às HH:MM UTC (Total: X min) |
| **Impacto no Negócio:** | Descontinuidade de irrigação / perda de sinal / atuação espúria |
| **Líder do Incidente (IC):** | Nome do Especialista de Confiabilidade / SRE |

---

## 2. Linha do Tempo dos Fatos (Timeline)

* **HH:MM** — Detecção do sintoma via alarme Datadog ou Watchdog de telemetria.
* **HH:MM** — Acionamento do operador de plantão (on-call).
* **HH:MM** — Isolamento do equipamento no SCADA e ativação de modo manual seguro.
* **HH:MM** — Identificação da causa-raiz no sinal analógico / pipeline de dados.
* **HH:MM** — Aplicação do fix / bypass seguro.
* **HH:MM** — Retorno à operação nominal e encerramento do incidente.

---

## 3. Análise da Causa-Raiz (Os 5 Porquês)

1. **Por que o pivô parou inesperadamente?**  
   Porque o watchdog gerou ticket HITL de queda severa de pressão.
2. **Por que o sinal de pressão caiu?**  
   Porque o sensor piezoelétrico de cabeceira enviou leitura $0.2\text{ bar}$.
3. **Por que a pressão física real não havia caído?**  
   Porque houve ruído transiente no transmissor 4-20mA durante oscilação elétrica.
4. **Por que o filtro determinístico não suprimiu o ruído?**  
   Porque a janela de persistência temporal estava configurada em $1$ ciclo ao invés de $3$ amostras consecutivas.
5. **Por que não havia debounce no pipeline de telemetria?**  
   Ausência de regra de validação de persistência no pré-processamento.

---

## 4. O que Funcionou Bem

* O guardrail **Human-in-the-Loop (HITL)** impediu que o sistema autônomo desligasse o inversor de frequência sem autorização humana direta.
* O canal WebSocket manteve latência sub-segundo informando o operador instantaneamente.

---

## 5. O que Precisa Melhorar

* Implementar janela de debounce (mínimo de 3 leituras espúrias consecutivas) antes de disparar alarme crítico.
* Rotear leituras pontuais espúrias para a Dead Letter Queue (`dlq_sensor_events`) com motivo `TRANSIENT_SPIKE`.

---

## 6. Ações Corretivas & Prevenção (Action Items)

| Ação Corretiva | Tipo | Responsável | Prazo | Ticket / PR |
| :--- | :--- | :--- | :--- | :--- |
| Adicionar filtro de debounce na camada Silver | Engenharia | Henrique | 3 dias | PR #42 |
| Configurar monitor Datadog para ruído em 4-20mA | SRE | SRE Team | 5 dias | JIRA-102 |
