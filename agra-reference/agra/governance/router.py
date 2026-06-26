"""
AGRA Router Middleware — 路由策略。

对应 AGRA-0004 §6 (Routing)。

支持策略：Round Robin / Weighted / Latency-Aware / Cost-Aware / Fallback / Capability-Aware
"""
from __future__ import annotations

import abc
import logging
import random
from typing import Optional

from agra.context import ProviderCandidate, RequestContext
from agra.governance.middleware import Middleware

logger = logging.getLogger("agra.governance.router")


class RoutingStrategy(abc.ABC):
    """路由策略基类。对应 AGRA-0004 §6.1。"""

    @abc.abstractmethod
    def select(
        self, ctx: RequestContext, candidates: list[ProviderCandidate]
    ) -> ProviderCandidate:
        ...


class RoundRobinStrategy(RoutingStrategy):
    """轮询策略。"""

    def __init__(self) -> None:
        self._index = 0

    def select(self, ctx: RequestContext, candidates: list[ProviderCandidate]) -> ProviderCandidate:
        if not candidates:
            raise ValueError("No candidates")
        candidate = candidates[self._index % len(candidates)]
        self._index += 1
        return candidate


class WeightedStrategy(RoutingStrategy):
    """权重策略。"""

    def select(self, ctx: RequestContext, candidates: list[ProviderCandidate]) -> ProviderCandidate:
        weights = [c.weight for c in candidates]
        return random.choices(candidates, weights=weights)[0]


class LatencyAwareStrategy(RoutingStrategy):
    """延迟感知策略（优先低延迟）。"""

    def __init__(self) -> None:
        self.latency: dict[str, float] = {}  # provider → avg latency ms

    def record(self, provider: str, latency_ms: float) -> None:
        self.latency[provider] = self.latency.get(provider, 1000) * 0.7 + latency_ms * 0.3

    def select(self, ctx: RequestContext, candidates: list[ProviderCandidate]) -> ProviderCandidate:
        return min(candidates, key=lambda c: self.latency.get(c.provider, 9999))


class CostAwareStrategy(RoutingStrategy):
    """成本感知策略。"""

    # 简化的成本表（per 1K tokens, USD）
    COST_TABLE = {
        "gpt-5": 0.01,
        "claude-sonnet-4-5": 0.003,
        "gemini-2.5-pro": 0.00125,
    }

    def select(self, ctx: RequestContext, candidates: list[ProviderCandidate]) -> ProviderCandidate:
        return min(candidates, key=lambda c: self.COST_TABLE.get(c.model, 0.01))


class FallbackStrategy(RoutingStrategy):
    """故障转移策略。"""

    def __init__(self) -> None:
        self.healthy: dict[str, bool] = {}

    def mark_unhealthy(self, provider: str) -> None:
        self.healthy[provider] = False

    def select(self, ctx: RequestContext, candidates: list[ProviderCandidate]) -> ProviderCandidate:
        healthy = [c for c in candidates if self.healthy.get(c.provider, True)]
        if healthy:
            # 按 priority 排序，优先级高的先选
            return sorted(healthy, key=lambda c: c.priority)[0]
        return candidates[0]


class CapabilityAwareStrategy(RoutingStrategy):
    """能力感知策略——根据请求需要的特性选择 Provider。

    对应 AGRA-0004 §6.1: Thinking/Grounding 路由。
    """

    def select(self, ctx: RequestContext, candidates: list[ProviderCandidate]) -> ProviderCandidate:
        # 检查请求体是否包含特定能力字段
        import json
        try:
            body = json.loads(ctx.body_bytes)
            if isinstance(body, dict):
                if "thinking" in body:
                    # 需要 Thinking 能力
                    for c in candidates:
                        if "thinking" in c.capabilities:
                            return c
                if "tools" in body:
                    for tool in body.get("tools", []):
                        if isinstance(tool, dict) and "googleSearch" in tool:
                            # 需要 Grounding 能力
                            for c in candidates:
                                if "grounding" in c.capabilities:
                                    return c
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        # 默认返回第一个
        return candidates[0]


class RouterMiddleware(Middleware):
    """路由 Middleware。

    对应 AGRA-0004 §6。
    """

    name = "router"

    def __init__(
        self,
        strategy: RoutingStrategy | None = None,
        provider_configs: dict[str, dict] | None = None,
    ):
        self.strategy = strategy or RoundRobinStrategy()
        self.provider_configs = provider_configs or {}

    def get_candidates(self, ctx: RequestContext) -> list[ProviderCandidate]:
        """根据协议和模型获取候选 Provider。"""
        candidates = []
        for provider, config in self.provider_configs.items():
            endpoint = config.get("endpoint", "")
            models = config.get("models", [])
            capabilities = set(config.get("capabilities", []))

            # 如果指定了模型，只返回支持该模型的 Provider
            if ctx.target_model and models and ctx.target_model not in models:
                continue

            candidates.append(
                ProviderCandidate(
                    provider=provider,
                    endpoint=endpoint,
                    model=ctx.target_model or (models[0] if models else "unknown"),
                    weight=config.get("weight", 1.0),
                    priority=config.get("priority", 0),
                    capabilities=capabilities,
                )
            )
        return candidates

    async def on_request(self, ctx: RequestContext) -> RequestContext:
        candidates = self.get_candidates(ctx)
        if not candidates:
            logger.warning("No candidates for protocol=%s model=%s", ctx.protocol, ctx.target_model)
            return ctx

        selected = self.strategy.select(ctx, candidates)
        ctx.target_provider = selected.provider
        ctx.target_endpoint = selected.endpoint
        ctx.metadata["route_strategy"] = self.strategy.__class__.__name__

        logger.info(
            "Routed %s → provider=%s endpoint=%s (strategy=%s)",
            ctx.request_id,
            selected.provider,
            selected.endpoint,
            self.strategy.__class__.__name__,
        )
        return ctx
