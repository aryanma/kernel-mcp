# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Profile, app, deployment, and invocation tools."""

from __future__ import annotations

import json
from typing import Any

from dedalus_mcp import tool

from client import (
    TIMEOUT_MEDIUM,
    TIMEOUT_SLOW,
    KernelAPIError,
    parse_list_response,
    request,
)


# =============================================================================
# Profiles
# =============================================================================


@tool(description="List all browser profiles")
async def list_profiles(limit: int = 20, offset: int = 0) -> list[dict]:
    """List browser profiles for session state persistence."""
    resp = await request("GET", "/profiles", TIMEOUT_MEDIUM, params={"limit": limit, "offset": offset})
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, "/profiles")
    return parse_list_response(resp.json())


@tool(description="Save browser session state (cookies, localStorage) to a profile. Use to persist logins. Call delete_browser after saving to free resources.")
async def save_profile(session_id: str, name: str | None = None) -> dict:
    """Save browser session state to a new profile."""
    body: dict[str, Any] = {"session_id": session_id}
    if name:
        body["name"] = name

    resp = await request("POST", "/profiles", TIMEOUT_MEDIUM, json_data=body)
    if resp.status_code not in (200, 201):
        raise KernelAPIError(resp.status_code, resp.text, "/profiles")
    return resp.json()


@tool(description="Delete a browser profile. WARNING: This is irreversible and deletes saved login state. Confirm user intent first.")
async def delete_profile(profile_id: str) -> dict:
    """Delete a browser profile."""
    path = f"/profiles/{profile_id}"
    resp = await request("DELETE", path, TIMEOUT_MEDIUM)
    if resp.status_code not in (200, 204):
        raise KernelAPIError(resp.status_code, resp.text, path)
    return {"deleted": True, "profile_id": profile_id}


# =============================================================================
# Apps
# =============================================================================


@tool(description="List apps in your Kernel organization")
async def list_apps(limit: int = 20, offset: int = 0) -> list[dict]:
    """List Kernel apps."""
    resp = await request("GET", "/apps", TIMEOUT_MEDIUM, params={"limit": limit, "offset": offset})
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, "/apps")
    return parse_list_response(resp.json())


# =============================================================================
# Deployments
# =============================================================================


@tool(description="List deployments with optional filtering")
async def list_deployments(
    app_name: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List app deployments."""
    params: dict[str, Any] = {"limit": limit}
    if app_name:
        params["app_name"] = app_name
    if status:
        params["status"] = status

    resp = await request("GET", "/deployments", TIMEOUT_MEDIUM, params=params)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, "/deployments")
    return parse_list_response(resp.json())


@tool(description="Get deployment details and logs")
async def get_deployment(deployment_id: str) -> dict:
    """Get deployment details."""
    path = f"/deployments/{deployment_id}"
    resp = await request("GET", path, TIMEOUT_MEDIUM)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return resp.json()


# =============================================================================
# Invocations
# =============================================================================


@tool(description="Invoke a Kernel app action. Returns invocation ID for tracking. Use async_mode=True for long tasks, then poll with get_invocation.")
async def invoke_action(
    app_name: str,
    action_name: str,
    payload: dict | None = None,
    version: str = "latest",
    async_mode: bool = False,
) -> dict:
    """Invoke an app action."""
    body: dict[str, Any] = {
        "app_name": app_name,
        "action_name": action_name,
        "version": version,
        "async": async_mode,
    }
    if payload:
        body["payload"] = json.dumps(payload)

    resp = await request("POST", "/invocations", TIMEOUT_SLOW, json_data=body)
    if resp.status_code not in (200, 202):
        raise KernelAPIError(resp.status_code, resp.text, "/invocations")
    return resp.json()


@tool(description="List invocations with optional filters")
async def list_invocations(
    app_name: str | None = None,
    action_name: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List invocations. Filter by status: queued, running, succeeded, failed."""
    params: dict[str, Any] = {"limit": limit}
    if app_name:
        params["app_name"] = app_name
    if action_name:
        params["action_name"] = action_name
    if status:
        params["status"] = status

    resp = await request("GET", "/invocations", TIMEOUT_MEDIUM, params=params)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, "/invocations")
    return parse_list_response(resp.json())


@tool(description="Get details of a specific invocation")
async def get_invocation(invocation_id: str) -> dict:
    """Get invocation details."""
    path = f"/invocations/{invocation_id}"
    resp = await request("GET", path, TIMEOUT_MEDIUM)
    if resp.status_code != 200:
        raise KernelAPIError(resp.status_code, resp.text, path)
    return resp.json()


# Export all app tools
app_tools = [
    list_profiles,
    save_profile,
    delete_profile,
    list_apps,
    list_deployments,
    get_deployment,
    invoke_action,
    list_invocations,
    get_invocation,
]
