"""State definition for the LangGraph Cognitive Copilot."""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class CopilotState(TypedDict):
    """LangGraph typed state for industrial asset diagnostics and HITL workflows."""

    messages: Annotated[list[dict[str, Any]], add_messages]
    user_query: str
    equip_id: int
    session_id: str
    catalog_spec: dict[str, Any] | None
    telemetry_live: dict[str, Any] | None
    deficit_metrics: dict[str, Any] | None
    requires_hitl: bool
    hitl_action: dict[str, Any] | None
    finops_stats: dict[str, Any]
    final_markdown: str
