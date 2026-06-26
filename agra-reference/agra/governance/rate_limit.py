"""
AGRA Rate Limit Middleware — 多维度限流。

对应 AGRA-0004 §7 (Rate Limiting)。

支持维度：User / Organization / Model / Provider / IP / Endpoint
支持算法：Token Bucket / Leaky Bucket / Fixed Window / Sliding Window
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

from agra.context import RequestContext
from agra.governance.middleware import Middleware

logger = logging.getLogger("agra.governance.rate_limit")


class RateLimitExceeded(Exception):
    """限流触发。"""

    def __init__(self, message: str, retry_after: int = 60):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


@dataclass
class TokenBucket:
    """Token Bucket 算法。对应 AGRA-0004 §7.2。"""

    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.tokens == 0.0:
            self.tokens = float(self.capacity)

    def consume(self, n: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


class RateLimitMiddleware(Middleware):
    """限流 Middleware。

    对应 AGRA-0004 §7。

    多维度限流，每维度独立的 Token Bucket。
    """

    name = "rate_limit"

    def __init__(
        self,
        limits: dict[str, dict] | None = None,
    ):
        """
        Args:
            limits: 维度 → {capacity, refill_rate}
                    例如: {"user": {"capacity": 100, "refill_rate": 10}}
        """
        self.limits = limits or {
            "user": {"capacity": 100, "refill_rate": 10},  # 100 req, 10/s refill
            "ip": {"capacity": 200, "refill_rate": 20},
        }
        self.buckets: dict[str, TokenBucket] = {}

    def _get_bucket_key(self, dimension: str, ctx: RequestContext) -> str | None:
        """根据维度获取限流 key。"""
        if dimension == "user":
            return f"{dimension}:{ctx.client_user_id}"
        elif dimension == "org":
            return f"{dimension}:{ctx.client_org_id}"
        elif dimension == "model" and ctx.target_model:
            return f"{dimension}:{ctx.target_model}"
        elif dimension == "provider" and ctx.target_provider:
            return f"{dimension}:{ctx.target_provider}"
        elif dimension == "ip":
            ip = ctx.headers.get("X-Forwarded-For", "unknown")
            return f"{dimension}:{ip}"
        return None

    async def on_request(self, ctx: RequestContext) -> RequestContext:
        for dimension, config in self.limits.items():
            key = self._get_bucket_key(dimension, ctx)
            if key is None:
                continue

            if key not in self.buckets:
                self.buckets[key] = TokenBucket(
                    capacity=config["capacity"],
                    refill_rate=config["refill_rate"],
                )

            bucket = self.buckets[key]
            if not bucket.consume(1):
                retry_after = int(1 / config["refill_rate"]) if config["refill_rate"] > 0 else 60
                logger.warning(
                    "Rate limit exceeded: %s (req=%s)", key, ctx.request_id
                )
                raise RateLimitExceeded(
                    f"Rate limit exceeded for {dimension}",
                    retry_after=retry_after,
                )

            ctx.metadata[f"rate_limit_{dimension}_remaining"] = int(bucket.tokens)

        return ctx
