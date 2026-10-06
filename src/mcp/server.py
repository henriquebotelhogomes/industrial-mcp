"""Official Model Context Protocol (FastMCP / MCPServer) Server Core.

Provides unified registry and exports for MCP tools, resources, and SSE streaming.
"""

from mcp.server.mcpserver import MCPServer

from src.config import settings
from src.mcp.resources import register_resources
from src.mcp.tools import (
    calculate_application_depth,
    diagnose_equipment,
    register_tools,
    request_emergency_stop,
)

# Initialize canonical MCPServer instance
mcp_server = MCPServer(settings.mcp_server_name)

# Register modular resources and tools
register_resources(mcp_server)
register_tools(mcp_server)

__all__ = [
    "mcp_server",
    "diagnose_equipment",
    "request_emergency_stop",
    "calculate_application_depth",
]
