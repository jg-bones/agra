"""
AGRA Governance Layer — Middleware Chain。

对应 AGRA-0001 §3.4 / AGRA-0004 §3 (Middleware Interface)。
Principle 2: Governance over Translation — 统一治理，而非统一协议。
Principle 4: Extensible by Design — 所有能力通过扩展点实现。
"""
from __future__ import annotations

import abc
import logging
from typing import Any, AsyncIterator, Optional

from agra.context import RequestContext, Usage

logger = logging.getLogger("agra.governance")


class Response:
    """响应封装。"""

    def __init__(
        self,
        status: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
        is_stream: bool = False,
        stream: AsyncIterator[bytes] | None = None,
        usage: Usage | None = None,
    ):
        self.status = status
        self.headers = headers or {}
        self.body = body
        self.is_stream = is_stream
        self.stream = stream
        self.usage = usage or Usage()


class StreamEvent:
    """流事件封装。"""

    def __init__(self, data: bytes, event_type: str = "data"):
        self.data = data
        self.event_type = event_type


class Middleware(abc.ABC):
    """AGRA Middleware 基类。

    对应 AGRA-0004 §3 (Middleware Interface)。

    每个 Middleware 是独立的，不依赖其他 Middleware 的内部状态。
    可以配置为跳过，可以按路由规则差异化配置。
    """

    name: str = "base"

    async def on_request(self, ctx: RequestContext) -> RequestContext:
        """在请求发送到 Provider 之前调用。"""
        return ctx

    async def on_response(
        self, ctx: RequestContext, response: Response
    ) -> Response:
        """在响应返回给客户端之前调用。"""
        return response

    async def on_stream_event(
        self, ctx: RequestContext, event: StreamEvent
    ) -> StreamEvent:
        """在流式响应的每个事件上调用。"""
        return event

    async def on_error(self, ctx: RequestContext, error: Exception) -> None:
        """当请求处理出错时调用。"""
        pass


class MiddlewareChain:
    """Middleware 链。

    对应 AGRA-0004 §2 / AGRA-0001 §3.4。

    请求阶段：按注册顺序执行 on_request
    响应阶段：按注册逆序执行 on_response
    """

    def __init__(self) -> None:
        self._middlewares: list[Middleware] = []

    def add(self, middleware: Middleware) -> "MiddlewareChain":
        """添加 Middleware（链式调用）。"""
        self._middlewares.append(middleware)
        logger.debug("Middleware added: %s", middleware.name)
        return self

    @property
    def middlewares(self) -> list[Middleware]:
        return list(self._middlewares)

    async def run_request(self, ctx: RequestContext) -> RequestContext:
        """执行请求阶段的 Middleware Chain（顺序执行）。"""
        for mw in self._middlewares:
            try:
                ctx = await mw.on_request(ctx)
            except Exception as e:
                await mw.on_error(ctx, e)
                raise
        return ctx

    async def run_response(
        self, ctx: RequestContext, response: Response
    ) -> Response:
        """执行响应阶段的 Middleware Chain（逆序执行）。"""
        for mw in reversed(self._middlewares):
            try:
                response = await mw.on_response(ctx, response)
            except Exception as e:
                logger.warning("Middleware %s on_response error: %s", mw.name, e)
        return response

    async def run_stream_event(
        self, ctx: RequestContext, event: StreamEvent
    ) -> StreamEvent:
        """对流事件执行所有 Middleware 的 on_stream_event。"""
        for mw in self._middlewares:
            event = await mw.on_stream_event(ctx, event)
        return event
