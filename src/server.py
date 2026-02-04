# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""MCP server configuration and entry point."""

import os

from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

from browsers import browser_tools
from apps import app_tools
from client import cleanup_client


def create_server() -> MCPServer:
    """Create MCP server with current env config."""
    return MCPServer(
        name="kernel",
        version="1.1.0",
        instructions="Kernel MCP server. Browser automation, screenshots, profiles, and app invocations.",
        http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        streamable_http_stateless=True,
        authorization_server=os.getenv("DEDALUS_AS_URL"),
    )


async def main() -> None:
    """Start MCP server."""
    server = create_server()
    server.collect(*browser_tools, *app_tools)
    try:
        await server.serve(port=8080)
    finally:
        await cleanup_client()
