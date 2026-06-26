"""
AGRA Policy Engine — 声明式规则引擎。

对应 AGRA-0004 §9 (Policy Engine) / AGRA-0001 §2.4。
声明式规则，不编写代码。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from agra.context import RequestContext

logger = logging.getLogger("agra.policy")


@dataclass
class PolicyMatch:
    """策略匹配条件。"""

    model: list[str] | None = None
    protocol: str | None = None
    source_ip: list[str] | None = None
    headers: dict[str, str] | None = None
    body_contains: list[str] | None = None

    def matches(self, ctx: RequestContext) -> bool:
        if self.model and ctx.target_model and ctx.target_model not in self.model:
            return False
        if self.protocol and ctx.protocol != self.protocol:
            return False
        if self.headers:
            for key, val in self.headers.items():
                if ctx.headers.get(key) != val:
                    return False
        if self.body_contains:
            body_str = ctx.body_bytes.decode("utf-8", errors="ignore")
            for field_name in self.body_contains:
                if field_name not in body_str:
                    return False
        return True


@dataclass
class PolicyAction:
    """策略动作。"""

    rate_limit: dict | None = None
    route: dict | None = None
    bypass: list[str] | None = None  # 要跳过的 Middleware 名称列表


@dataclass
class Policy:
    """一条策略。对应 AGRA-0004 §9.3。"""

    name: str
    description: str = ""
    match: PolicyMatch = field(default_factory=PolicyMatch)
    action: PolicyAction = field(default_factory=PolicyAction)


class PolicyEngine:
    """策略引擎。

    对应 AGRA-0004 §9。

    加载声明式 YAML 规则，在请求阶段匹配并应用。
    """

    def __init__(self) -> None:
        self.policies: list[Policy] = []

    def load(self, config: list[dict]) -> None:
        """从配置加载策略。

        示例配置:
        [
            {
                "name": "high-cost-model-rate-limit",
                "description": "限制高成本模型",
                "match": {"model": ["gpt-5", "claude-opus-5"]},
                "action": {"rate_limit": {"requests_per_minute": 10}}
            },
            {
                "name": "thinking-capability-routing",
                "match": {"body_contains": ["thinking"]},
                "action": {"route": {"require_capability": "thinking"}}
            }
        ]
        """
        for item in config:
            match = PolicyMatch(**item.get("match", {}))
            action = PolicyAction(**item.get("action", {}))
            self.policies.append(
                Policy(
                    name=item["name"],
                    description=item.get("description", ""),
                    match=match,
                    action=action,
                )
            )
        logger.info("Loaded %d policies", len(self.policies))

    def evaluate(self, ctx: RequestContext) -> list[PolicyAction]:
        """评估请求匹配的策略，返回所有匹配的动作。"""
        matched = []
        for policy in self.policies:
            if policy.match.matches(ctx):
                logger.debug("Policy matched: %s for %s", policy.name, ctx.request_id)
                matched.append(policy.action)
        return matched

    def get_bypass_middlewares(self, ctx: RequestContext) -> set[str]:
        """获取应跳过的 Middleware 名称。"""
        bypass = set()
        for action in self.evaluate(ctx):
            if action.bypass:
                bypass.update(action.bypass)
        return bypass
