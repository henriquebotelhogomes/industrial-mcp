# 🧠 MLOps: Detecção de Anomalias & Monitoramento de Data Drift

> **Pipeline de Aprendizado de Máquina em Streaming Industrial**  
> **Camada:** System 1 (Reflexivo, sub-10ms, $0.00 de custo operacional)  

---

## 1. Princípios de MLOps Industrial

No contexto de sistemas de controle PLC/SCADA e telemetria de pivôs, o pipeline de MLOps do **Industrial-MCP** foi projetado seguindo quatro diretrizes invioláveis:
1. **Prevenção Estrita de Data Leakage (Temporal Split):** Séries temporais não podem ser embaralhadas aleatoriamente (`shuffle=False`). O conjunto de treino utiliza os primeiros 80% do tempo cronológico e o conjunto de teste os 20% finais.
2. **Tempo de Inferência Ultrarrápido ($p95 < 10\text{ms}$):** A decisão de anomalia deve ocorrer na escala do ciclo de varredura do controlador.
3. **Casamento de Regras Físicas com Aprendizado Estatístico:** Regras determinísticas de domínio (pressão crítica $< 1.0\text{ bar}$, sobrecorrente $> 40.0\text{ A}$) operam em conjunto com o *Isolation Forest*.
4. **Monitoramento Ativo de Data Drift:** Verificação contínua de desvio distributivo de sensores para alertar necessidade de retreinamento.

---

## 2. Arquitetura do Modelo Isolation Forest

* **Algoritmo:** `sklearn.ensemble.IsolationForest`
* **Contaminação Estimada:** 5% (`contamination=0.05`)
* **Pré-Processador:** `RobustScaler` (resistente a outliers severos e spikes de pressão)
* **Features de Entrada:**
  * `pressao_bar`: Pressão hidráulica na base do pivô.
  * `corrente_motor_a`: Corrente elétrica dos motores redutores.
  * `vibracao_mms`: Vibração mecânica no último lance.
  * `velocidade_angular_rads`: Velocidade angular de deslocamento do pivô.

---

## 3. Monitor de Data Drift (Deriva de Dados)

O módulo `src/ml/drift_monitor.py` realiza o teste bicaudal **Kolmogorov-Smirnov (KS-Test)** comparando a distribuição da janela de produção mais recente com a distribuição de referência de treino:

* **P-Valor de Corte ($\alpha$):** 0.05
* **Population Stability Index (PSI):**
  * $\text{PSI} < 0.1$: Estável (Sem Drift)
  * $0.1 \le \text{PSI} < 0.25$: Alerta de Deriva Moderada
  * $\text{PSI} \ge 0.25$: Deriva Severa $\to$ Gatilho de Retreino Automatizado

---

## 4. Reprodutibilidade & Retreino

O treinamento é determinístico e acionado via CLI ou pipeline de automação:
```bash
# Execução do pipeline de treino com validação temporal
uv run python -m src.ml.train
```
Artefatos gerados:
* `models/isolation_forest.joblib` (Modelo serializado)
* Registro de métricas em `structlog` com hash de versão.
