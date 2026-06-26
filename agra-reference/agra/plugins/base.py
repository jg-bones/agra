"""
AGRA Plugin System — 插件系统。

对应 AGRA-0001 §2.4 (Extensible by Design) / AGRA-BOOK Chapter 9。
Plugin 是独立的功能模块，可注册 Middleware 和路由。
"""
from __future__ import annotations

import abc
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agra.gateway import Gateway

logger = logging.getLogger("agra.plugins")


class Plugin(abc.ABC):
    """Plugin 基类。

    对应 AGRA-0001 §2.4 / AGRA-BOOK Chapter 9 §8.3。

    Plugin 可以在 setup 时注册 Middleware、路由等。
    """

    name: str = "base"
    version: str = "0.1.0"

    @abc.abstractmethod
    async def setup(self, gateway: "Gateway") -> None:
        """插件初始化，注册中间件、路由等。"""
        ...

    async def teardown(self) -> None:
        """插件清理。"""
        pass


class CachePlugin(Plugin):
    """响应缓存插件。

    缓存非流式响应，减少重复请求的成本。
    通过 Plugin 机制实现，不影响核心代码。
    """

    name = "cache"
    version = "0.1.0"

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._cache: dict[str, tuple[bytes, float]] = {}

    def _cache_key(self, ctx) -> str:
        return f"{ctx.method}:{ctx.path}:{hash(ctx.body_bytes)}"

    async def setup(self, gateway: "Gateway") -> None:
        from agra.governance.middleware import Middleware, Response
        from agra.context import RequestContext

        cache = self

        class CacheMiddleware(Middleware):
            name = "cache"

            async def on_request(self, ctx: RequestContext) -> RequestContext:
                key = cache._cache_key(ctx)
                if key in cache._cache:
                    body, ts = cache._cache[key]
                    if time.time() - ts < cache.ttl:
                        ctx.metadata["cache_hit"] = True
                        logger.debug("Cache hit: %s", key)
                return ctx

        gateway.middleware_chain.add(CacheMiddleware())
        logger.info("CachePlugin registered (ttl=%ds)", self.ttl)


class ContentFilterPlugin(Plugin):
    """内容审核插件。

    演示 Plugin 如何在不修改核心代码的情况下增加功能。
    """

    name = "content_filter"
    version = "0.1.0"

    BLOCKED_KEYWORDS = ["test-blocked-keyword"]

    async def setup(self, gateway: "Gateway") -> None:
        from agra.governance.middleware import Middleware
        from agra.context import RequestContext

        plugin = self

        class FilterMiddleware(Middleware):
            name = "content_filter"

            async def on_request(self, ctx: RequestContext) -> RequestContext:
                body_str = ctx.body_bytes.decode("utf-8", errors="ignore").lower()
                for keyword in plugin.BLOCKED_KEYWORDS:
                    if keyword in body_str:
                        raise Exception(f"Content blocked: contains '{keyword}'")
                return ctx

        gateway.middleware_chain.add(FilterMiddleware())
        logger.info("ContentFilterPlugin registered")
