"""
AGRA Billing & Audit Middleware — 计费与审计。

对应 AGRA-0004 §8 (Billing) 和 §3 (Audit)。
"""
from __future__ import annotations

import json
import logging
import time

from agra.context import RequestContext
from agra.governance.middleware import Middleware, Response

logger = logging.getLogger("agra.governance.billing")


class BillingMiddleware(Middleware):
    """计费 Middleware。

    对应 AGRA-0004 §8。

    两个阶段：
    - on_request: 计费预检（检查余额/配额）
    - on_response: 计费记录（根据 Usage 记录成本）
    """

    name = "billing"

    # 简化的定价表（per 1K tokens, USD）
    PRICING = {
        "gpt-5": {"input": 0.005, "output": 0.015},
        "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
        "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
    }

    def __init__(self) -> None:
        self.records: list[dict] = []

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        price = self.PRICING.get(model, {"input": 0.005, "output": 0.015})
        return (input_tokens / 1000) * price["input"] + (output_tokens / 1000) * price["output"]

    async def on_request(self, ctx: RequestContext) -> RequestContext:
        # 计费预检：检查组织是否有余额（demo 中跳过）
        return ctx

    async def on_response(self, ctx: RequestContext, response: Response) -> Response:
        if response.usage and response.usage.total_tokens > 0:
            cost = self.calculate_cost(
                ctx.target_model or "unknown",
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
            response.usage.cost_usd = cost

            record = {
                "request_id": ctx.request_id,
                "org_id": ctx.client_org_id,
                "provider": ctx.target_provider,
                "model": ctx.target_model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cost_usd": round(cost, 6),
                "timestamp": time.time(),
            }
            self.records.append(record)
            logger.info(
                "Billing: %s org=%s model=%s cost=$%.6f tokens=%d",
                ctx.request_id,
                ctx.client_org_id,
                ctx.target_model,
                cost,
                response.usage.total_tokens,
            )
        return response


class AuditMiddleware(Middleware):
    """审计 Middleware。

    对应 AGRA-0005 §3.3 (审计日志)。
    """

    name = "audit"

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def on_request(self, ctx: RequestContext) -> RequestContext:
        # 记录审计事件
        event = {
            "timestamp": time.time(),
            "event": "request.received",
            "request_id": ctx.request_id,
            "org_id": ctx.client_org_id,
            "user_id": ctx.client_user_id,
            "method": ctx.method,
            "path": ctx.path,
            "protocol": ctx.protocol,
            "model": ctx.target_model,
        }
        self.events.append(event)
        return ctx

    async def on_response(self, ctx: RequestContext, response: Response) -> Response:
        event = {
            "timestamp": time.time(),
            "event": "response.sent",
            "request_id": ctx.request_id,
            "status": response.status,
            "latency_ms": round(ctx.latency_ms, 2),
            "provider": ctx.target_provider,
            "cost_usd": response.usage.cost_usd if response.usage else 0,
        }
        self.events.append(event)
        return response
