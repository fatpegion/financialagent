"""Optional external data endpoint client for FinancialAgent."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from typing import Any

from .analysis import AnalysisResult


async def fetch_external_context(result: AnalysisResult) -> str | None:
    """Fetch optional market/news context from a user-provided endpoint.

    The endpoint is intentionally optional. If it is not configured or fails,
    the main chat API still returns a normal answer.
    """
    endpoint = _env_first(
        "FINANCIAL_AGENT_DATA_ENDPOINT",
        "A_SHARE_DATA_ENDPOINT",
        "A_SHARE_MCP_ENDPOINT",
        "MCP_ENDPOINT",
    )
    if not endpoint:
        return None

    timeout = float(os.getenv("FINANCIAL_AGENT_DATA_TIMEOUT", "8"))
    show_errors = os.getenv("FINANCIAL_AGENT_SHOW_ENDPOINT_ERRORS", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    try:
        return await asyncio.to_thread(_request_endpoint, endpoint, result, timeout)
    except Exception as exc:
        if show_errors:
            return f"External data endpoint failed: {type(exc).__name__}: {exc}"
        return None


def _request_endpoint(endpoint: str, result: AnalysisResult, timeout: float) -> str | None:
    method = os.getenv("FINANCIAL_AGENT_DATA_METHOD", "POST").upper()
    payload = {
        "query": result.query,
        "company_name": result.company_name,
        "stock_code": result.stock_code,
        "market": result.market,
        "analysis_result": asdict(result),
    }
    headers = {
        "Accept": "application/json, text/plain;q=0.9",
        "User-Agent": "FinancialAgent-Bailian/0.1",
    }

    token = _env_first("FINANCIAL_AGENT_DATA_TOKEN", "A_SHARE_DATA_TOKEN", "MCP_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    api_key = _env_first("FINANCIAL_AGENT_DATA_API_KEY", "A_SHARE_DATA_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key

    if method == "GET":
        query = urllib.parse.urlencode({k: v for k, v in payload.items() if isinstance(v, str) and v})
        separator = "&" if "?" in endpoint else "?"
        url = f"{endpoint}{separator}{query}" if query else endpoint
        request = urllib.request.Request(url, headers=headers, method="GET")
    else:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc

    return _extract_context(raw)


def _extract_context(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    try:
        data: Any = json.loads(text)
    except Exception:
        return text[:5000]

    for key in ("context", "data", "result", "response", "text", "content"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, str) and value.strip():
            return value.strip()[:5000]
        if value is not None:
            return json.dumps(value, ensure_ascii=False, indent=2)[:5000]
    return json.dumps(data, ensure_ascii=False, indent=2)[:5000]


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None
