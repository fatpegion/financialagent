"""FastAPI app for Alibaba Cloud Bailian high-code deployment."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .analysis import analyze_query, build_report, extract_text, maybe_generate_with_llm, session_id_from_payload
from .endpoint_client import fetch_external_context
from .mcp_client import fetch_mcp_context


app = FastAPI(title="FinancialAgent Bailian Adapter", version="0.1.6")


@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    text = (
        "FinancialAgent request failed inside the cloud runtime.\n"
        f"Error type: {type(exc).__name__}\n"
        "Please check the request body and Bailian deployment logs."
    )
    return JSONResponse(_agent_response(text=text, session_id=f"sess_{uuid.uuid4().hex}"), status_code=200)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "FinancialAgent Bailian Adapter",
        "health": "/health",
        "process": "/process",
        "chat": "/chat",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process")
async def process(request: Request) -> JSONResponse:
    session_id = f"sess_{uuid.uuid4().hex}"
    try:
        payload = await _read_payload(request)
        user_text = extract_text(payload)
        session_id = session_id_from_payload(payload) or session_id

        if not user_text:
            text = "请在 message、query、prompt、text 或 input 字段中提供要分析的金融问题。"
        else:
            result = analyze_query(user_text)
            context_parts = [
                await _safe_context(fetch_mcp_context, result),
                await _safe_context(fetch_external_context, result),
            ]
            external_context = "\n\n".join(part for part in context_parts if part)
            fallback_report = build_report(result)
            if external_context:
                fallback_report = f"{fallback_report}\n\n外部数据接口补充：\n{external_context}"
            text = await maybe_generate_with_llm(result, external_context) or fallback_report
    except Exception as exc:
        text = (
            "FinancialAgent 处理请求时遇到内部错误。"
            f"\n错误类型：{type(exc).__name__}"
            "\n请检查 /process 请求体、模型环境变量和云端构建日志。"
        )

    return JSONResponse(_agent_response(text=text, session_id=session_id))


@app.get("/chat")
async def chat_get(q: str = "") -> dict[str, str]:
    result = analyze_query(q)
    text = build_report(result) if q else "请通过 q 参数或 POST /process 提交金融分析问题。"
    return {"response": text, "text": text}


@app.post("/chat")
async def chat_post(request: Request) -> JSONResponse:
    return await process(request)


async def _safe_context(func: Any, result: Any) -> str | None:
    try:
        return await func(result)
    except Exception:
        return None


async def _read_payload(request: Request) -> Any:
    body = await request.body()
    if not body:
        return {}
    try:
        return await request.json()
    except Exception:
        return body.decode("utf-8", errors="ignore")


def _agent_response(text: str, session_id: str) -> dict[str, Any]:
    now = int(time.time())
    response_id = f"resp_{uuid.uuid4().hex}"
    message_id = f"msg_{uuid.uuid4().hex}"
    return {
        "id": response_id,
        "object": "response",
        "created_at": now,
        "completed_at": now,
        "status": "completed",
        "session_id": session_id,
        "response": text,
        "text": text,
        "output": [
            {
                "id": message_id,
                "object": "message",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "object": "content",
                        "type": "text",
                        "text": text,
                    }
                ],
            }
        ],
    }


def run_app() -> None:
    import os

    import uvicorn

    port = int(os.getenv("FINANCIAL_AGENT_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_app()
