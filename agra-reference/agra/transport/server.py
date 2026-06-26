"""
AGRA Transport Layer — HTTP 服务器与字节流透传。

对应 AGRA-0001 §3.2 (Transport Layer) 和 AGRA-BOOK Chapter 5。
核心约束：不解析请求体内容，以字节流透传。

Principle 3: Transport Transparency — 不修改 Request/Response Body。
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from agra.gateway import Gateway

logger = logging.getLogger("agra.transport")


class TransportServer:
    """HTTP 服务器，对应 Transport Layer。

    职责：
    - 接收客户端 HTTP 请求
    - 读取请求体为原始字节（不解析）
    - 注入追踪 Header (X-Request-ID, X-Trace-ID)
    - 将请求交给 Gateway 处理
    - 管理流式响应（SSE 透传）
    """

    def __init__(self, gateway: "Gateway", host: str = "0.0.0.0", port: int = 8080):
        self.gateway = gateway
        self.host = host
        self.port = port
        self._runner: web.AppRunner | None = None

    def create_app(self) -> web.Application:
        """创建 aiohttp 应用。

        关键：使用 catch-all 路由，所有路径都交给 Gateway 处理。
        Transport Layer 不关心具体路径——那是 Protocol Layer 的事。
        """
        app = web.Application(client_max_size=100 * 1024 * 1024)  # 100MB

        # 所有路径和方法都走同一个 handler
        app.router.add_route("*", "/{tail:.*}", self._handle_request)

        return app

    async def _handle_request(self, request: web.Request) -> web.StreamResponse:
        """处理所有 HTTP 请求。

        Transport Layer 的核心：读取原始字节，不解析，交给 Gateway。
        """
        # 读取原始请求体字节（不解析 JSON）
        body_bytes = await request.read()

        # 注入追踪 Header（AGRA-0001 §3.2 允许的最小化 Header 修改）
        headers = dict(request.headers)

        # 构造上下文并交给 Gateway
        from agra.context import RequestContext

        ctx = RequestContext(
            method=request.method,
            path=request.path,
            headers=headers,
            body_bytes=body_bytes,
        )

        # 确保 X-Request-ID 存在
        if "X-Request-ID" not in headers and "x-request-id" not in headers:
            headers["X-Request-ID"] = ctx.request_id

        try:
            result = await self.gateway.handle(ctx)
            return await self._build_response(request, ctx, result)
        except Exception as e:
            logger.error("Request %s failed: %s", ctx.request_id, e, exc_info=True)
            return web.json_response(
                {"error": {"type": "gateway_error", "message": str(e)}},
                status=502,
                headers={"X-Request-ID": ctx.request_id},
            )

    async def _build_response(
        self, request: web.Request, ctx, result: dict
    ) -> web.StreamResponse:
        """构造响应。

        支持两种模式：
        - 非流式：直接返回 JSON
        - 流式（SSE）：逐帧透传 Provider 的 SSE 事件
        """
        status = result.get("status", 200)
        provider_headers = result.get("headers", {})
        body = result.get("body", b"")
        is_stream = result.get("is_stream", False)

        if is_stream and asyncio.iscoroutine(body):
            # SSE 流式透传
            response = web.StreamResponse(
                status=status,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-ID": ctx.request_id,
                },
            )
            await response.prepare(request)

            async for chunk in body:
                # 逐帧透传——不修改、不缓冲、不合并
                response.write(chunk)
                await response.drain()

            await response.write_eof()
            return response
        else:
            # 非流式：原样返回响应体
            response = web.Response(
                status=status,
                body=body,
                headers={
                    **{k: v for k, v in provider_headers.items()},
                    "X-Request-ID": ctx.request_id,
                },
            )
            return response

    async def start(self) -> None:
        """启动服务器。"""
        app = self.create_app()
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        logger.info("AGRA Gateway listening on http://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        """停止服务器。"""
        if self._runner:
            await self._runner.cleanup()
            logger.info("AGRA Gateway stopped")
