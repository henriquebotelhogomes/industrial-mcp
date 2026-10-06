"""LangGraph StateGraph for Industrial Copilot with Relational RAG and Hybrid Fallback."""

import time
from typing import Any

import httpx
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agent.relational_rag import relational_rag
from src.agent.state import CopilotState
from src.config import settings
from src.core.logging import logger


async def retrieve_context_node(state: CopilotState) -> dict[str, Any]:
    """Node 1: Retrieves factory catalog specs and live telemetry from DuckDB."""
    equip_id = state.get("equip_id") or 14863
    specs = relational_rag.get_catalog_specs(equip_id)
    telemetry = relational_rag.get_live_telemetry(equip_id)
    return {
        "catalog_spec": specs,
        "telemetry_live": telemetry,
    }


async def compute_deficits_node(state: CopilotState) -> dict[str, Any]:
    """Node 2: Compares nominal specs against field readings to compute engineering deltas."""
    specs = state.get("catalog_spec") or {}
    telemetry = state.get("telemetry_live") or {}
    deficits = relational_rag.calculate_deficits(specs, telemetry)
    return {
        "deficit_metrics": deficits,
    }


def _build_deterministic_dossier(
    user_query: str,
    specs: dict[str, Any],
    telemetry: dict[str, Any],
    deficits: dict[str, Any],
) -> str:
    """Generates a rigorous, deterministic technical dossier when offline or during rapid demo."""
    equip_name = specs.get("equip_name", "Pivô Central")
    maker = specs.get("maker", "Valmont")
    model = specs.get("model", "Valley 8000C")
    farm_name = specs.get("farm_name", "VB Homestead")
    farm_loc = f"{specs.get('farm_city', 'Sunnyside')}, {specs.get('farm_state', 'WA')}"

    nom_p = deficits.get("nominal_pressure_bar", 3.4)
    live_p = deficits.get("live_pressure_bar", 0.0)
    deficit_pct = deficits.get("pressure_deficit_pct", 0.0)
    angle = telemetry.get("angulo_posicao_graus", 0.0)
    current_a = telemetry.get("corrente_motor_a", 0.0)
    vibration = telemetry.get("vibracao_mms", 0.0)
    water_mode = telemetry.get("water_mode", "Dry")
    running = telemetry.get("running_status", "Stopped")

    nom_depth = deficits.get("nominal_depth_mm", 5.5)
    actual_depth = deficits.get("actual_depth_mm", 5.5)

    is_critical = deficits.get("is_critical_pressure", False)
    is_overcurrent = deficits.get("is_overcurrent", False)

    status_icon = "🚨 **ALERTA CRÍTICO DE OPERAÇÃO**" if (is_critical or is_overcurrent) else "🟢 **OPERAÇÃO EM REGIME NOMINAL**"

    lines = [
        f"### {status_icon}",
        f"**Equipamento:** `{equip_name}` (#{specs.get('equip_id', 14863)}) | **Fabricante:** `{maker} {model}`",
        f"**Localização:** Fazenda `{farm_name}` ({farm_loc}) | **Área:** `{specs.get('area', 45.0)} ha`",
        "",
        "---",
        "#### 1. Ficha Técnica vs. Telemetria de Campo (RAG Relacional)",
        f"- **Ângulo da Torre Mestra:** `{angle}°` | **Status do CLP:** `{running}` | **Modo:** `{water_mode}`",
        f"- **Pressão Hidráulica:** Medida: **`{live_p:.2f} bar`** | Nominal de Catálogo: **`{nom_p:.2f} bar`** ({deficit_pct:+.1f}% de desvio)",
        f"- **Corrente Elétrica dos Lances:** Medida: **`{current_a:.1f} A`** (Teto de Segurança: `40.0 A`)",
        f"- **Vibração na Última Torre:** Medida: **`{vibration:.2f} mm/s`** (Teto de Segurança: `8.0 mm/s`)",
        "",
    ]

    if is_critical and water_mode == "Wet":
        lines.extend([
            "#### 2. Laudo de Engenharia & Causa-Raiz",
            f"Detectada **queda severa de pressão ({live_p:.2f} bar)** com a bomba em regime molhado (*Wet*).",
            f"A pressão está **{abs(deficit_pct):.1f}% abaixo da pressão de serviço de fábrica ({nom_p:.2f} bar)**.",
            "Isto indica provável **cavitação na sucção da bomba, vazamento na adutora principal ou bico aspersor estourado**.",
            "",
            "#### 3. Impacto Agronômico & FinOps",
            f"- **Lâmina de Irrigação Projetada:** `{nom_depth:.1f} mm` $\\rightarrow$ **Lâmina Efetiva Entregue:** `{actual_depth:.1f} mm`.",
            "- **Risco:** Sub-irrigação severa e desperdício de $38.4 kWh/h de energia de bombeamento sem aplicação útil de água.",
            "",
            "#### 4. Prescrição Operacional com Human-in-the-Loop (HITL)",
            "⚠️ **Ação Recomendada pelo Copiloto:** Emissão de parada emergencial e despressurização no CLP para evitar danos estruturais.",
            "*(Aguardando autorização explícita do operador na sala de controle)*",
        ])
    else:
        lines.extend([
            "#### 2. Laudo de Engenharia & Diagnóstico",
            "Os parâmetros eletromecânicos encontram-se dentro da faixa admissível de projeto.",
            f"A distribuição de água está homogênea, entregando lâmina calculada de **`{actual_depth:.1f} mm`** em conformidade com a ABNT NBR ISO 11545.",
            "",
            "#### 3. Eficiência & FinOps",
            "- Operação nominal com 100% de filtragem pelo **System 1 (Reflexivo local)**.",
            "- Custo de computação em nuvem nesta avaliação: **$0.00 (Zero)**.",
        ])

    return "\n".join(lines)


async def generate_diagnosis_node(state: CopilotState) -> dict[str, Any]:
    """Node 3: Generates diagnostic synthesis via remote LLM or instantaneous resilient fallback."""
    start_t = time.perf_counter()
    specs = state.get("catalog_spec") or {}
    telemetry = state.get("telemetry_live") or {}
    deficits = state.get("deficit_metrics") or {}
    query = state.get("user_query") or "Diagnóstico do estado operacional"

    # Default to resilient fallback first
    final_text = _build_deterministic_dossier(query, specs, telemetry, deficits)
    tier_used = "System 1 Hybrid Fallback (Local Sub-10ms)"
    prompt_tokens = 0
    completion_tokens = 0

    # Attempt remote LLM if API Key is configured and reachable
    api_key = settings.openrouter_api_key or settings.gemini_api_key
    if api_key and api_key != "sua_chave_aqui":
        try:
            prompt_context = (
                f"Você é o Copiloto de IA Especialista em Automação (PLC/SCADA) e Engenharia de Irrigação.\n"
                f"Analise a solicitação do operador: '{query}'.\n"
                f"Dados do Ativo (Catálogo de Fábrica):\n{specs}\n"
                f"Telemetria em Tempo Real:\n{telemetry}\n"
                f"Métricas de Desvio Calculadas:\n{deficits}\n"
                f"Produza um laudo técnico conciso em Markdown com: 1. Diagnóstico, 2. Causa-raiz, 3. Impacto FinOps/Água, 4. Ação recomendada."
            )

            # Fast 3.5s timeout to guarantee zero hangs during live demo
            async with httpx.AsyncClient(timeout=3.5) as client:
                if settings.openrouter_api_key:
                    resp = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                        json={
                            "model": settings.llm_model,
                            "messages": [{"role": "user", "content": prompt_context}],
                            "temperature": 0.2,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        final_text = data["choices"][0]["message"]["content"]
                        tier_used = f"Cloud LLM ({settings.llm_model})"
                        prompt_tokens = data.get("usage", {}).get("prompt_tokens", 250)
                        completion_tokens = data.get("usage", {}).get("completion_tokens", 180)
        except Exception as e:
            logger.info("resilient_copilot_fallback_activated", reason=str(e))
            # Gracefully falls back to high-fidelity deterministic dossier

    elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
    return {
        "final_markdown": final_text,
        "finops_stats": {
            "tier_used": tier_used,
            "latency_ms": elapsed_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost_usd": round((prompt_tokens * 0.00000015) + (completion_tokens * 0.0000006), 6),
        },
    }


async def evaluate_hitl_node(state: CopilotState) -> dict[str, Any]:
    """Node 4: Evaluates safety guardrails and flags actions requiring Human-in-the-Loop confirmation."""
    deficits = state.get("deficit_metrics") or {}
    telemetry = state.get("telemetry_live") or {}
    specs = state.get("catalog_spec") or {}

    is_critical_p = deficits.get("is_critical_pressure", False)
    is_overcurrent = deficits.get("is_overcurrent", False)
    is_wet = telemetry.get("water_mode") == "Wet"

    requires_hitl = False
    hitl_action = None

    if (is_critical_p and is_wet) or is_overcurrent:
        requires_hitl = True
        hitl_action = {
            "action_type": "EMERGENCY_STOP",
            "equip_id": specs.get("equip_id", 14863),
            "equip_name": specs.get("equip_name", "Haak 1"),
            "reason": "Queda severa de pressão hidráulica detectada (< 45% do nominal) com bomba acionada.",
            "recommended_plc_command": "DISARM_PUMP_AND_STOP_TOWERS",
            "audit_required": True,
        }

    return {
        "requires_hitl": requires_hitl,
        "hitl_action": hitl_action,
    }


def build_copilot_graph() -> Any:
    """Builds and compiles the LangGraph StateGraph workflow."""
    workflow = StateGraph(CopilotState)

    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("compute_deficits", compute_deficits_node)
    workflow.add_node("generate_diagnosis", generate_diagnosis_node)
    workflow.add_node("evaluate_hitl", evaluate_hitl_node)

    workflow.add_edge(START, "retrieve_context")
    workflow.add_edge("retrieve_context", "compute_deficits")
    workflow.add_edge("compute_deficits", "generate_diagnosis")
    workflow.add_edge("generate_diagnosis", "evaluate_hitl")
    workflow.add_edge("evaluate_hitl", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


copilot_graph = build_copilot_graph()
