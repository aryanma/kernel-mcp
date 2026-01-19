# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Kernel MCP Server.

Browser automation and app invocation tools via Kernel API.
API docs: https://www.kernel.sh/docs/api-reference

Environment Variables:
    KERNEL_API_KEY: Your Kernel API key
    DEDALUS_AS_URL: Optional Dedalus authorization server URL
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from pydantic import BaseModel

from dedalus_mcp import MCPServer, tool
from dedalus_mcp.server import TransportSecuritySettings


KERNEL_API_BASE = "https://api.onkernel.com"
AS_URL = os.getenv("DEDALUS_AS_URL")

server = MCPServer(
    name="kernel",
    version="1.0.0",
    instructions="Kernel MCP server. Browser automation, screenshots, and app invocations.",
    http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    streamable_http_stateless=True,
    authorization_server=AS_URL,
)


def _headers() -> dict[str, str]:
    api_key = os.getenv("KERNEL_API_KEY")
    if not api_key:
        raise ValueError("KERNEL_API_KEY environment variable not set")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


# --- Browser Tools ---

@tool(description="Create a new cloud browser session")
async def create_browser(
    stealth: bool = True,
    headless: bool = False,
    timeout_seconds: int = 300,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
) -> dict:
    """Create a browser session.

    Args:
        stealth: Reduce bot detection (default: True)
        headless: No GUI/VNC (default: False)
        timeout_seconds: Inactivity timeout (default: 300)
        viewport_width: Width (default: 1920)
        viewport_height: Height (default: 1080)

    Allowed viewports: 1024x768, 1920x1080, 2560x1440, 1920x1200, 1440x900, 1200x800

    Returns:
        session_id, cdp_ws_url, browser_live_view_url
    """
    body = {
        "stealth": stealth,
        "headless": headless,
        "timeout_seconds": timeout_seconds,
        "viewport": {"width": viewport_width, "height": viewport_height},
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{KERNEL_API_BASE}/browsers", headers=_headers(), json=body)
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return resp.json()


@tool(description="List active browser sessions")
async def list_browsers(limit: int = 20, offset: int = 0) -> list[dict]:
    """List browser sessions.

    Args:
        limit: Max results 1-100 (default: 20)
        offset: Pagination offset

    Returns:
        List of browser sessions
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{KERNEL_API_BASE}/browsers",
            headers=_headers(),
            params={"limit": limit, "offset": offset},
        )
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) else data


@tool(description="Delete a browser session")
async def delete_browser(session_id: str) -> dict:
    """Delete a browser session.

    Args:
        session_id: The session ID to delete

    Returns:
        Success status
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.delete(f"{KERNEL_API_BASE}/browsers/{session_id}", headers=_headers())
        if resp.status_code not in (200, 204):
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return {"deleted": True, "session_id": session_id}


@tool(description="Take a screenshot of a browser session")
async def screenshot(session_id: str) -> dict:
    """Take a screenshot.

    Args:
        session_id: The browser session ID

    Returns:
        base64 encoded PNG image
    """
    import base64
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{KERNEL_API_BASE}/browsers/{session_id}/computer/screenshot",
            headers=_headers(),
            json={},
        )
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        # API returns raw PNG bytes
        img_base64 = base64.b64encode(resp.content).decode("utf-8")
        return {"image": img_base64, "format": "png", "size_bytes": len(resp.content)}


@tool(description="Execute Playwright/TypeScript code in a browser - navigate, scrape, interact with pages")
async def execute_playwright(session_id: str, code: str) -> dict:
    """Execute Playwright code in the browser. This is the most powerful tool.

    Args:
        session_id: The browser session ID
        code: Playwright/TypeScript code to execute. Use `page` object.

    Example code:
        await page.goto('https://example.com');
        const title = await page.title();
        return title;

    Returns:
        {success: bool, result: any} - the return value of your code
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{KERNEL_API_BASE}/browsers/{session_id}/playwright/execute",
            headers=_headers(),
            json={"code": code},
        )
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return resp.json()


@tool(description="Type text in the browser")
async def type_text(session_id: str, text: str) -> dict:
    """Type text at current cursor position.

    Args:
        session_id: The browser session ID
        text: Text to type

    Returns:
        Success status
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{KERNEL_API_BASE}/browsers/{session_id}/computer/type",
            headers=_headers(),
            json={"text": text},
        )
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return {"success": True, "typed": text}


@tool(description="Click mouse at x,y coordinates")
async def click_mouse(session_id: str, x: int, y: int) -> dict:
    """Click at screen coordinates.

    Args:
        session_id: The browser session ID
        x: X coordinate
        y: Y coordinate

    Returns:
        Success status
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{KERNEL_API_BASE}/browsers/{session_id}/computer/click_mouse",
            headers=_headers(),
            json={"x": x, "y": y},
        )
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return {"success": True, "clicked": {"x": x, "y": y}}


@tool(description="Press keyboard keys (Enter, Escape, Ctrl+A, etc)")
async def press_keys(session_id: str, keys: list[str]) -> dict:
    """Press keyboard keys.

    Args:
        session_id: The browser session ID
        keys: List of keys to press (e.g., ["Enter"], ["Control", "a"])

    Returns:
        Success status
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{KERNEL_API_BASE}/browsers/{session_id}/computer/press_key",
            headers=_headers(),
            json={"keys": keys},
        )
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return {"success": True, "pressed": keys}


@tool(description="Scroll the page")
async def scroll(session_id: str, x: int, y: int, delta_x: int = 0, delta_y: int = 100) -> dict:
    """Scroll at a position.

    Args:
        session_id: The browser session ID
        x: X coordinate to scroll at
        y: Y coordinate to scroll at
        delta_x: Horizontal scroll amount (default: 0)
        delta_y: Vertical scroll amount (default: 100, positive = down)

    Returns:
        Success status
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{KERNEL_API_BASE}/browsers/{session_id}/computer/scroll",
            headers=_headers(),
            json={"x": x, "y": y, "delta_x": delta_x, "delta_y": delta_y},
        )
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return {"success": True, "scrolled": {"delta_x": delta_x, "delta_y": delta_y}}


# --- Invocation Tools ---

@tool(description="Invoke an action on a Kernel app")
async def invoke_action(
    app_name: str,
    action_name: str,
    payload: dict | None = None,
    version: str = "latest",
    async_mode: bool = False,
) -> dict:
    """Invoke an app action.

    Args:
        app_name: Application identifier
        action_name: Action to execute
        payload: Input data
        version: App version (default: "latest")
        async_mode: Run asynchronously (default: False)

    Returns:
        Invocation id, status, output
    """
    body: dict[str, Any] = {
        "app_name": app_name,
        "action_name": action_name,
        "version": version,
        "async": async_mode,
    }
    if payload:
        body["payload"] = json.dumps(payload)

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{KERNEL_API_BASE}/invocations", headers=_headers(), json=body)
        if resp.status_code not in (200, 202):
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return resp.json()


@tool(description="List invocations with optional filters")
async def list_invocations(
    app_name: str | None = None,
    action_name: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List invocations.

    Args:
        app_name: Filter by app
        action_name: Filter by action
        status: Filter by status (queued, running, succeeded, failed)
        limit: Max results (default: 20)

    Returns:
        List of invocations
    """
    params: dict[str, Any] = {"limit": limit}
    if app_name:
        params["app_name"] = app_name
    if action_name:
        params["action_name"] = action_name
    if status:
        params["status"] = status

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{KERNEL_API_BASE}/invocations", headers=_headers(), params=params)
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) else data


@tool(description="Get details of a specific invocation")
async def get_invocation(invocation_id: str) -> dict:
    """Get invocation details.

    Args:
        invocation_id: The invocation ID

    Returns:
        Full invocation details with output
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{KERNEL_API_BASE}/invocations/{invocation_id}", headers=_headers())
        if resp.status_code != 200:
            raise Exception(f"Kernel API error ({resp.status_code}): {resp.text}")
        return resp.json()


server.collect(
    # Browser lifecycle
    create_browser,
    list_browsers,
    delete_browser,
    # Browser control
    execute_playwright,
    screenshot,
    type_text,
    click_mouse,
    press_keys,
    scroll,
    # App invocations
    invoke_action,
    list_invocations,
    get_invocation,
)


async def main() -> None:
    await server.serve(port=8080)


if __name__ == "__main__":
    asyncio.run(main())
