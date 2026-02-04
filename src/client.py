# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""HTTP client utilities for Kernel API."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx


KERNEL_API_BASE = "https://api.onkernel.com"

# Timeout configurations (seconds)
TIMEOUT_FAST = 15.0      # click, scroll, type, press_keys, move, drag
TIMEOUT_MEDIUM = 30.0    # screenshot, list operations, delete
TIMEOUT_SLOW = 120.0     # create_browser, execute_playwright, invoke_action

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5

# Shared HTTP client
_client: httpx.AsyncClient | None = None


class KernelAPIError(Exception):
    """Raised when Kernel API returns an error."""

    def __init__(self, status_code: int, message: str, endpoint: str):
        self.status_code = status_code
        self.message = message
        self.endpoint = endpoint
        super().__init__(f"Kernel API error ({status_code}) at {endpoint}: {message}")


def get_headers() -> dict[str, str]:
    """Get request headers with authentication."""
    api_key = os.getenv("KERNEL_API_KEY")
    if not api_key:
        raise ValueError("KERNEL_API_KEY environment variable not set")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


async def get_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client with connection pooling."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(TIMEOUT_SLOW, connect=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0,
            ),
            http2=True,
        )
    return _client


async def cleanup_client() -> None:
    """Clean up the shared HTTP client."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None


async def request(
    method: str,
    path: str,
    timeout: float = TIMEOUT_MEDIUM,
    *,
    json_data: dict | None = None,
    params: dict | None = None,
) -> httpx.Response:
    """Make an HTTP request with retry logic for transient failures."""
    client = await get_client()
    headers = get_headers()
    url = f"{KERNEL_API_BASE}{path}"
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            if method == "GET":
                resp = await client.get(url, headers=headers, params=params, timeout=timeout)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=json_data or {}, timeout=timeout)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers, timeout=timeout)
            elif method == "PATCH":
                resp = await client.patch(url, headers=headers, json=json_data or {}, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if resp.status_code < 500:
                return resp

            last_error = KernelAPIError(resp.status_code, resp.text, url)

        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            last_error = e

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_BACKOFF * (2 ** attempt))

    if isinstance(last_error, KernelAPIError):
        raise last_error
    raise KernelAPIError(0, str(last_error), url)


def parse_list_response(data: Any) -> list[dict]:
    """Parse list API response, handling None and nested data."""
    if isinstance(data, dict):
        result = data.get("data", data)
        return result if result is not None else []
    return data if data is not None else []
