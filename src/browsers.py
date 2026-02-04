# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Browser lifecycle and computer control tools."""

from __future__ import annotations

import base64
from typing import Any, Literal

from dedalus_mcp import tool
from dedalus_mcp.types import ImageContent

from client import (
    TIMEOUT_FAST,
    TIMEOUT_MEDIUM,
    TIMEOUT_SLOW,
    KernelAPIError,
    parse_list_response,
    request,
)


# =============================================================================
# Browser Lifecycle
# =============================================================================


@tool(description="Launch a new sandboxed browser in Kernel's cloud. Check list_browsers first to avoid unnecessary sessions. Use stealth=True for scraping, profile_id to maintain auth state across sessions.")
async def create_browser(
    stealth: bool = True,
    headless: bool = False,
    timeout_seconds: int = 300,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    profile_id: str | None = None,
    proxy: str | None = None,
) -> dict:
    """Create a browser session.

    Args:
        stealth: Reduce bot detection (default: True)
        headless: No GUI/VNC (default: False)
        timeout_seconds: Inactivity timeout (default: 300)
        viewport_width: Width (default: 1920)
        viewport_height: Height (default: 1080)
        profile_id: Optional profile ID to load saved session state
        proxy: Optional proxy URL (e.g., "http://user:pass@host:port")

    Allowed viewports: 1024x768, 1920x1080, 2560x1440, 1920x1200, 1440x900, 1200x800
    """
    body: dict[str, Any] = {
        "stealth": stealth,
        "headless": headless,
        "timeout_seconds": timeout_seconds,
        "viewport": {"width": viewport_width, "height": viewport_height},
    }
    if profile_id:
        body["profile_id"] = profile_id
    if proxy:
        body["proxy"] = proxy

    resp = await request("POST", "/browsers", TIMEOUT_SLOW, json_data=body)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, "/browsers")
    return resp.json()


@tool(description="Get details of a specific browser session")
async def get_browser(session_id: str) -> dict:
    """Get browser session details."""
    path = f"/browsers/{session_id}"
    resp = await request("GET", path, TIMEOUT_MEDIUM)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return resp.json()


@tool(description="List active browser sessions. Check this before creating new browsers to reuse existing sessions and avoid resource waste.")
async def list_browsers(limit: int = 20, offset: int = 0) -> list[dict]:
    """List browser sessions."""
    resp = await request("GET", "/browsers", TIMEOUT_MEDIUM, params={"limit": limit, "offset": offset})
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, "/browsers")
    return parse_list_response(resp.json())


@tool(description="Delete a browser session. Always clean up sessions when done to free resources. Call this after save_profile if preserving state.")
async def delete_browser(session_id: str) -> dict:
    """Delete a browser session."""
    path = f"/browsers/{session_id}"
    resp = await request("DELETE", path, TIMEOUT_MEDIUM)
    if resp.status_code not in (200, 204):
        raise KernelAPIError(resp.status_code, resp.text, path)
    return {"deleted": True, "session_id": session_id}


# =============================================================================
# Computer Controls
# =============================================================================


@tool(description="Capture browser page as base64 PNG. Use this instead of page.screenshot() in execute_playwright code.")
async def screenshot(
    session_id: str,
    region_x: int | None = None,
    region_y: int | None = None,
    region_width: int | None = None,
    region_height: int | None = None,
) -> ImageContent:
    """Take a screenshot. Optionally specify a region."""
    path = f"/browsers/{session_id}/computer/screenshot"
    body: dict[str, Any] = {}
    if all(v is not None for v in [region_x, region_y, region_width, region_height]):
        body["region"] = {"x": region_x, "y": region_y, "width": region_width, "height": region_height}

    resp = await request("POST", path, TIMEOUT_MEDIUM, json_data=body)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    img_base64 = base64.b64encode(resp.content).decode("utf-8")
    return ImageContent(type="image", data=img_base64, mimeType="image/png")


@tool(description="Click at x,y pixel coordinates. Prefer execute_playwright with selectors instead - only use this for pixel-precise clicks when selectors fail.")
async def click_mouse(
    session_id: str,
    x: int,
    y: int,
    button: Literal["left", "right", "middle"] = "left",
    click_count: int = 1,
    modifiers: list[str] | None = None,
) -> dict:
    """Click at screen coordinates. Use click_count=2 for double-click."""
    path = f"/browsers/{session_id}/computer/click_mouse"
    body: dict[str, Any] = {"x": x, "y": y, "button": button, "click_count": click_count}
    if modifiers:
        body["modifiers"] = modifiers

    resp = await request("POST", path, TIMEOUT_FAST, json_data=body)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return {"success": True, "clicked": {"x": x, "y": y, "button": button, "click_count": click_count}}


@tool(description="Move mouse to x,y coordinates without clicking")
async def move_mouse(
    session_id: str,
    x: int,
    y: int,
    modifiers: list[str] | None = None,
) -> dict:
    """Move cursor to screen coordinates."""
    path = f"/browsers/{session_id}/computer/move_mouse"
    body: dict[str, Any] = {"x": x, "y": y}
    if modifiers:
        body["modifiers"] = modifiers

    resp = await request("POST", path, TIMEOUT_FAST, json_data=body)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return {"success": True, "moved_to": {"x": x, "y": y}}


@tool(description="Drag mouse along a path of points")
async def drag_mouse(
    session_id: str,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: Literal["left", "right", "middle"] = "left",
    modifiers: list[str] | None = None,
) -> dict:
    """Drag mouse from start point to end point."""
    path = f"/browsers/{session_id}/computer/drag_mouse"
    coords = [[start_x, start_y], [end_x, end_y]]
    body: dict[str, Any] = {"path": coords, "button": button}
    if modifiers:
        body["modifiers"] = modifiers

    resp = await request("POST", path, TIMEOUT_FAST, json_data=body)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return {"success": True, "dragged": {"from": [start_x, start_y], "to": [end_x, end_y]}}


@tool(description="Type text at cursor position. Prefer execute_playwright with page.fill() instead - only use this when you need raw keystroke simulation.")
async def type_text(
    session_id: str,
    text: str,
    delay_ms: int | None = None,
) -> dict:
    """Type text at current cursor position."""
    path = f"/browsers/{session_id}/computer/type"
    body: dict[str, Any] = {"text": text}
    if delay_ms is not None:
        body["delay_ms"] = delay_ms

    resp = await request("POST", path, TIMEOUT_FAST, json_data=body)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return {"success": True, "typed": text}


@tool(description="Press keyboard keys (Enter, Escape, Ctrl+A, etc)")
async def press_keys(
    session_id: str,
    keys: list[str],
    modifiers: list[str] | None = None,
) -> dict:
    """Press keyboard keys."""
    path = f"/browsers/{session_id}/computer/press_key"
    body: dict[str, Any] = {"keys": keys}
    if modifiers:
        body["modifiers"] = modifiers

    resp = await request("POST", path, TIMEOUT_FAST, json_data=body)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return {"success": True, "pressed": keys}


@tool(description="Scroll at x,y position. Positive delta_y scrolls down. Can also use execute_playwright with page.mouse.wheel() for more control.")
async def scroll(
    session_id: str,
    x: int,
    y: int,
    delta_x: int = 0,
    delta_y: int = 100,
) -> dict:
    """Scroll at a position. Positive delta_y scrolls down."""
    path = f"/browsers/{session_id}/computer/scroll"
    resp = await request("POST", path, TIMEOUT_FAST, json_data={"x": x, "y": y, "delta_x": delta_x, "delta_y": delta_y})
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return {"success": True, "scrolled": {"delta_x": delta_x, "delta_y": delta_y}}


@tool(description="Run Playwright code in browser. PREFERRED for all interactions - clicking, typing, searching, scraping. Consolidate operations into single calls. Avoid page.screenshot() here; use the screenshot tool instead.")
async def execute_playwright(session_id: str, code: str) -> dict:
    """Execute Playwright/TypeScript code directly in the browser VM.

    Args:
        session_id: The browser session ID
        code: Playwright code using `page` object. Must return a value.

    Example:
        await page.goto('https://example.com');
        return await page.title();
    """
    path = f"/browsers/{session_id}/playwright/execute"
    resp = await request("POST", path, TIMEOUT_SLOW, json_data={"code": code})
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return resp.json()


# Export all browser tools
browser_tools = [
    create_browser,
    get_browser,
    list_browsers,
    delete_browser,
    screenshot,
    click_mouse,
    move_mouse,
    drag_mouse,
    type_text,
    press_keys,
    scroll,
    execute_playwright,
]
