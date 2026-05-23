"""DashScope MCP client integration for FinancialAgent."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any

from .analysis import AnalysisResult


DEFAULT_A_SHARE_MCP_URL = (
    "https://dashscope.aliyuncs.com/api/v1/mcps/"
    "mcp-MTcwNjllNjVmYmEy/mcp"
)


async def fetch_mcp_context(result: AnalysisResult) -> str | None:
    """Fetch A-share context through Bailian's MCP endpoint."""
    if os.getenv("FINANCIAL_AGENT_USE_MCP", "1").lower() in {"0", "false", "no", "off"}:
        return None

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key or api_key.lower().startswith("your "):
        return _maybe_error("DASHSCOPE_API_KEY is not configured.")

    mcp_url = _env_first(
        "FINANCIAL_AGENT_MCP_URL",
        "A_SHARE_MCP_URL",
        "DASHSCOPE_MCP_URL",
    ) or DEFAULT_A_SHARE_MCP_URL

    code = _format_a_share_code(result)
    if not code:
        return None

    timeout = float(os.getenv("FINANCIAL_AGENT_MCP_TIMEOUT", "20"))
    now = datetime.now()
    code_label = result.company_name or code
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=120)).strftime("%Y-%m-%d")
    report_year = str(now.year - 1)

    tool_calls: list[tuple[str, dict[str, Any]]] = [
        ("get_latest_trading_date", {}),
        ("get_stock_basic_info", {"code": code, "fields": []}),
        (
            "get_historical_k_data",
            {
                "code": code,
                "start_date": start_date,
                "end_date": end_date,
                "frequency": "d",
                "adjust_flag": "3",
                "fields": [],
            },
        ),
        ("get_profit_data", {"code": code, "year": report_year, "quarter": 4}),
        ("crawl_news", {"query": code_label, "top_k": 5}),
    ]

    try:
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport
    except Exception:
        try:
            return await asyncio.to_thread(
                _fetch_with_raw_streamable_http,
                mcp_url,
                api_key,
                tool_calls,
                timeout,
            )
        except Exception as exc:
            return _maybe_error(f"MCP raw HTTP failed: {type(exc).__name__}: {exc}")

    try:
        transport = _build_streamable_http_transport(
            StreamableHttpTransport,
            mcp_url=mcp_url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
    except Exception as exc:
        return _maybe_error(f"MCP transport failed: {type(exc).__name__}: {exc}")

    sections: list[str] = []
    try:
        async with Client(transport=transport) as client:
            for tool_name, arguments in tool_calls:
                text = await _safe_call_tool(client, tool_name, arguments, timeout)
                if text:
                    sections.append(
                        f"### MCP tool: {tool_name}\n"
                        f"arguments: {arguments}\n"
                        f"{_truncate(text)}"
                    )
    except Exception as exc:
        return _maybe_error(f"MCP client failed: {type(exc).__name__}: {exc}")

    if not sections:
        return None

    return "# A-share MCP data\n\n" + "\n\n".join(sections)


def _fetch_with_raw_streamable_http(
    mcp_url: str,
    api_key: str,
    tool_calls: list[tuple[str, dict[str, Any]]],
    timeout: float,
) -> str | None:
    """Minimal Streamable HTTP MCP client used when fastmcp is unavailable."""
    request_id = 1
    headers = {"Authorization": f"Bearer {api_key}"}
    protocol_version = os.getenv("FINANCIAL_AGENT_MCP_PROTOCOL_VERSION", "2025-03-26")

    initialize_payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {
                "name": "financialagent-bailian",
                "version": "0.1.6",
            },
        },
    }
    data, session_id = _post_mcp_json(mcp_url, headers, initialize_payload, None, timeout)
    if data and data.get("error"):
        return _maybe_error(f"initialize failed: {data['error']}")

    initialized_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    _post_mcp_json(mcp_url, headers, initialized_payload, session_id, timeout)

    sections: list[str] = []
    for tool_name, arguments in tool_calls:
        request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        try:
            data, session_id = _post_mcp_json(
                mcp_url,
                headers,
                payload,
                session_id,
                timeout,
            )
            text = _extract_tool_text(data)
        except Exception as exc:
            text = _maybe_error(
                f"Tool {tool_name} failed: {type(exc).__name__}: {exc}",
                tool_name=tool_name,
            )
        if text:
            sections.append(
                f"### MCP tool: {tool_name}\n"
                f"arguments: {arguments}\n"
                f"{_truncate(text)}"
            )

    if not sections:
        return None
    return "# A-share MCP data\n\n" + "\n\n".join(sections)


def _post_mcp_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    session_id: str | None,
    timeout: float,
) -> tuple[dict[str, Any] | None, str | None]:
    request_headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        **headers,
    }
    if session_id:
        request_headers["Mcp-Session-Id"] = session_id

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_text = response.read().decode("utf-8", errors="replace")
            next_session_id = response.headers.get("Mcp-Session-Id") or session_id
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc

    if not response_text.strip():
        return None, next_session_id
    return _parse_mcp_response(response_text), next_session_id


def _parse_mcp_response(response_text: str) -> dict[str, Any] | None:
    text = response_text.strip()
    if not text:
        return None
    if text.startswith("{"):
        return json.loads(text)

    data_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            value = line[len("data:"):].strip()
            if value and value != "[DONE]":
                data_lines.append(value)
    if not data_lines:
        return None
    return json.loads(data_lines[-1])


def _extract_tool_text(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None
    if data.get("error"):
        return _maybe_error(f"tool returned error: {data['error']}")
    result = data.get("result") or {}
    content = result.get("content") or []
    blocks: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("text"):
            blocks.append(str(block["text"]))
    return "\n".join(blocks).strip() or None


def _build_streamable_http_transport(
    transport_cls: Any,
    *,
    mcp_url: str,
    headers: dict[str, str],
) -> Any:
    try:
        return transport_cls(_MCP_URL=mcp_url, headers=headers)
    except TypeError:
        return transport_cls(url=mcp_url, headers=headers)


async def _safe_call_tool(
    client: Any,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: float,
) -> str | None:
    try:
        result = await asyncio.wait_for(
            client.call_tool(tool_name, arguments),
            timeout=timeout,
        )
    except Exception as exc:
        return _maybe_error(
            f"Tool {tool_name} failed: {type(exc).__name__}: {exc}",
            tool_name=tool_name,
        )

    if not result or not getattr(result, "content", None):
        return None

    blocks: list[str] = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            blocks.append(str(text))
    return "\n".join(blocks).strip() or None


def _format_a_share_code(result: AnalysisResult) -> str | None:
    code = result.stock_code
    if not code or not code.isdigit() or len(code) != 6:
        return None
    if result.market in {"sh", "sz"}:
        return f"{result.market}.{code}"
    if code.startswith("6"):
        return f"sh.{code}"
    return f"sz.{code}"


def _truncate(text: str, limit: int = 3500) -> str:
    value = text.strip()
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]"


def _maybe_error(message: str, tool_name: str | None = None) -> str | None:
    if os.getenv("FINANCIAL_AGENT_SHOW_MCP_ERRORS", "0").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return None
    prefix = f"MCP {tool_name} error" if tool_name else "MCP error"
    return f"{prefix}: {message}"


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None
