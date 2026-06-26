"""
local_api.py (Python Utility)
==============================

Purpose:
    Authenticated HTTP client for the local Express backend (localhost:3001).
    Reads the bearer token from .runtime/api-token once and injects it into
    every request — callers never touch the token file directly.

    All /api/* routes require `Authorization: Bearer <token>`. Missing this
    header returns 401. /health is exempt and uses plain requests.get().

Layer: Backend / Python Services / Utilities

Usage:
    from utils.local_api import api_get, api_post

    data = api_get("/api/projections/NVDA")   # raises on 401/4xx/5xx
    api_post("/api/projections", payload)
"""

import json
from pathlib import Path
from typing import Any

import requests

BASE_URL = "http://localhost:3001"
_TOKEN_FILE = Path(__file__).parents[4] / ".runtime" / "api-token"


def _load_token() -> str:
    """Read the bearer token from .runtime/api-token.

    Returns:
        Token string.

    Raises:
        FileNotFoundError: If the token file does not exist (backend not started yet).
    """
    if not _TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"Local API token not found at {_TOKEN_FILE}. "
            "Start the backend with `python3 run_investment_toolkit.py` first."
        )
    return _TOKEN_FILE.read_text().strip()


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_load_token()}"}


def api_get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Authenticated GET to the local backend.

    Args:
        path: URL path, e.g. "/api/projections/NVDA".
        params: Optional query parameters.

    Returns:
        Parsed JSON response body.

    Raises:
        requests.HTTPError: On 4xx/5xx responses.
    """
    resp = requests.get(f"{BASE_URL}{path}", headers=_auth_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, body: dict[str, Any]) -> Any:
    """Authenticated POST to the local backend.

    Args:
        path: URL path, e.g. "/api/projections".
        body: Request body (serialized as JSON).

    Returns:
        Parsed JSON response body.

    Raises:
        requests.HTTPError: On 4xx/5xx responses.
    """
    resp = requests.post(
        f"{BASE_URL}{path}",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def health_check() -> bool:
    """Check if the backend is reachable. No auth required.

    Returns:
        True if backend responds with status ok.
    """
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False
