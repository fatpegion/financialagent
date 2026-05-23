"""Lightweight financial analysis helpers for the cloud API.

The training scripts in this repository depend on large local models.  This
module keeps the deployable API small and fast, while preserving the same
financial sentiment/risk workflow shape.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


POSITIVE_TERMS = {
    "beat",
    "beats",
    "growth",
    "record",
    "profit",
    "profits",
    "approval",
    "partnership",
    "increase",
    "increases",
    "surge",
    "soar",
    "strong",
    "dividend",
    "buyback",
    "上涨",
    "增长",
    "盈利",
    "利润",
    "超预期",
    "创新高",
    "利好",
    "获批",
    "合作",
    "回购",
    "分红",
}

NEGATIVE_TERMS = {
    "miss",
    "misses",
    "decline",
    "decrease",
    "decreased",
    "loss",
    "losses",
    "delay",
    "lawsuit",
    "investigation",
    "probe",
    "recall",
    "bankruptcy",
    "fraud",
    "layoff",
    "layoffs",
    "halt",
    "regulatory",
    "下跌",
    "下降",
    "亏损",
    "延期",
    "诉讼",
    "调查",
    "召回",
    "破产",
    "欺诈",
    "裁员",
    "监管",
    "处罚",
    "停产",
}

RISK_TERMS = {
    "debt",
    "default",
    "volatility",
    "regulatory",
    "lawsuit",
    "investigation",
    "recall",
    "bankruptcy",
    "fraud",
    "supply chain",
    "cash flow",
    "债务",
    "违约",
    "波动",
    "监管",
    "诉讼",
    "调查",
    "召回",
    "破产",
    "欺诈",
    "供应链",
    "现金流",
    "退市",
}


@dataclass(frozen=True)
class AnalysisResult:
    query: str
    company_name: str | None
    stock_code: str | None
    market: str | None
    sentiment_score: int
    risk_score: int
    matched_positive: list[str]
    matched_negative: list[str]
    matched_risk: list[str]
    llm_used: bool = False


def extract_text(payload: Any) -> str:
    """Extract the user's text from common Bailian/OpenAI-style payloads."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload.strip()
    if not isinstance(payload, dict):
        return str(payload).strip()

    for key in ("message", "query", "prompt", "text", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    input_value = payload.get("input")
    extracted = _extract_from_input(input_value)
    if extracted:
        return extracted

    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            extracted = _extract_from_input(item)
            if extracted:
                return extracted

    return ""


def session_id_from_payload(payload: Any) -> str | None:
    if isinstance(payload, dict):
        value = payload.get("session_id") or payload.get("sessionId")
        if value:
            return str(value)
    return None


def analyze_query(query: str) -> AnalysisResult:
    normalized = query.strip()
    lower = normalized.lower()
    stock_code, market = _extract_stock_code(normalized)
    company_name = _extract_company_name(normalized, stock_code)

    positive = _matched_terms(lower, POSITIVE_TERMS)
    negative = _matched_terms(lower, NEGATIVE_TERMS)
    risk = _matched_terms(lower, RISK_TERMS)

    sentiment_score = _bounded_score(3 + len(positive) - len(negative))
    risk_score = _bounded_score(3 + len(risk) + max(0, len(negative) - len(positive) - 1))

    return AnalysisResult(
        query=normalized,
        company_name=company_name,
        stock_code=stock_code,
        market=market,
        sentiment_score=sentiment_score,
        risk_score=risk_score,
        matched_positive=positive,
        matched_negative=negative,
        matched_risk=risk,
    )


def build_report(result: AnalysisResult) -> str:
    target = _target_label(result)
    sentiment_label = {
        1: "明显负面",
        2: "偏负面",
        3: "中性",
        4: "偏正面",
        5: "明显正面",
    }[result.sentiment_score]
    risk_label = {
        1: "极低风险",
        2: "低风险",
        3: "中等风险",
        4: "高风险",
        5: "极高风险",
    }[result.risk_score]

    positives = _format_matches(result.matched_positive)
    negatives = _format_matches(result.matched_negative)
    risks = _format_matches(result.matched_risk)
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""FinancialAgent 云端入口已就绪。

用户问题：{result.query or "未提供"}
识别对象：{target}
分析时间：{today}

快速判断：
1. 新闻/文本情感评分：{result.sentiment_score}/5（{sentiment_label}）
2. 风险评分：{result.risk_score}/5（{risk_label}）
3. 正面触发词：{positives}
4. 负面触发词：{negatives}
5. 风险触发词：{risks}

分析框架：
- 基本面：关注收入增长、毛利率、净利率、ROE、现金流、负债率和行业地位。
- 技术面：关注趋势、成交量、均线、支撑阻力位和波动率。
- 估值面：关注 PE、PB、PS、股息率，以及与行业均值和历史区间的对比。
- 新闻面：结合事件性质做情感与风险评分，避免只看单条新闻下结论。

说明：当前云端包默认不携带本地 Qwen 权重和训练数据；如果配置了 OPENAI_COMPATIBLE_API_KEY，系统会优先调用兼容 OpenAI 的模型生成更完整的报告。以上内容不构成投资建议。"""


async def maybe_generate_with_llm(result: AnalysisResult, external_context: str | None = None) -> str | None:
    api_key = _env_first(
        "OPENAI_COMPATIBLE_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY",
    )
    if not api_key:
        return None

    if os.getenv("FINANCIAL_AGENT_USE_LLM", "0").lower() not in {"1", "true", "yes", "on"}:
        return None

    try:
        from openai import AsyncOpenAI
    except Exception:
        return None

    base_url = _env_first("OPENAI_COMPATIBLE_BASE_URL", "OPENAI_BASE_URL") or "https://api.deepseek.com"
    model = _env_first("OPENAI_COMPATIBLE_MODEL", "OPENAI_MODEL") or "deepseek-v4-flash"
    try:
        timeout = float(os.getenv("FINANCIAL_AGENT_LLM_TIMEOUT", "30"))
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        rule_report = build_report(result)
        endpoint_context = external_context or "未配置或未获取到外部数据。"
        rule_report = f"{rule_report}\n\n外部数据接口补充：\n{endpoint_context}"
    except Exception:
        return None

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个谨慎的金融分析智能体。请基于用户问题和规则引擎的初步判断，"
                "输出中文 Markdown 分析。不要编造实时行情、财报或新闻；没有数据时明确说明限制。"
                "结尾必须声明不构成投资建议。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{result.query}\n\n"
                f"规则引擎初步判断：\n{rule_report}\n\n"
                "请生成一份结构化金融分析，包含：识别对象、情感与风险判断、基本面、技术面、估值面、新闻面、风险因素、后续需要补充的数据。"
            ),
        },
    ]
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=1800,
        )
    except Exception:
        return None

    content = response.choices[0].message.content if response.choices else None
    return content.strip() if content else None


def _extract_from_input(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("content", "text", "message", "query"):
            extracted = _extract_from_input(value.get(key))
            if extracted:
                return extracted
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            extracted = _extract_from_input(item)
            if extracted:
                parts.append(extracted)
        return "\n".join(parts).strip()
    return ""


def _extract_stock_code(text: str) -> tuple[str | None, str | None]:
    cn_match = re.search(r"\b(?:(sh|sz)[.]?)?(\d{6})\b", text, flags=re.IGNORECASE)
    if cn_match:
        code = cn_match.group(2)
        prefix = (cn_match.group(1) or "").lower()
        if not prefix:
            if code.startswith("6"):
                prefix = "sh"
            elif code.startswith(("0", "3")):
                prefix = "sz"
        return code, prefix or None

    us_match = re.search(r"\b[A-Z]{1,5}\b", text)
    if us_match:
        return us_match.group(0), "us"

    return None, None


def _extract_company_name(text: str, stock_code: str | None) -> str | None:
    if stock_code and stock_code.isdigit():
        patterns = [
            rf"([\u4e00-\u9fa5A-Za-z0-9]+)[（(]?(?:sh\.|sz\.)?{re.escape(stock_code)}[）)]?",
            rf"(?:sh\.|sz\.)?{re.escape(stock_code)}[）)]?\s*([\u4e00-\u9fa5A-Za-z0-9]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                name = _clean_company_name(match.group(1))
                if name:
                    return name

    match = re.search(r"(?:分析|看看|了解|评估|研究)\s*([\u4e00-\u9fa5A-Za-z0-9]{2,20})", text)
    if match:
        return _clean_company_name(match.group(1))
    return None


def _clean_company_name(value: str) -> str | None:
    value = re.sub(r"[的这只这个股票投资价值风险新闻情感分析情况\s]+$", "", value.strip())
    return value if len(value) >= 2 else None


def _matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    return sorted({term for term in terms if term.lower() in text})


def _bounded_score(value: int) -> int:
    return max(1, min(5, value))


def _target_label(result: AnalysisResult) -> str:
    parts: list[str] = []
    if result.company_name:
        parts.append(result.company_name)
    if result.stock_code:
        code = f"{result.market}.{result.stock_code}" if result.market in {"sh", "sz"} else result.stock_code
        parts.append(code)
    return " / ".join(parts) if parts else "未识别到明确股票代码或公司名"


def _format_matches(values: list[str]) -> str:
    return "、".join(values) if values else "暂无明显触发词"


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None
