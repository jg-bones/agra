"""
AGRA Gateway — 核心引擎。

对应 AGRA-0001 §3 (Five-Layer Model)。
集成 Transport Layer、Protocol Layer、Governance Layer、Observability Layer。

这是 TLG (Transparent Gateway) 模式的实现——默认行为是透传，不修改请求体。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from agra.context import RequestContext, Usage
from agra.governance.middleware import MiddlewareChain, Response, StreamEvent
from agra.observability.observability import ObservabilityMiddleware
from agra.policy.engine import PolicyEngine
from agra.protocol.handlers import ProtocolDetector, ProtocolHandler
from agra.usage.extractor import get_extractor

logger = logging.getLogger("agra.gateway")


class Gateway:
    """AGRA Gateway 核心引擎。

    对应 AGRA-0001 §3 完整五层模型。

    层次：
    1. Transport Layer → 由 TransportServer 处理（见 transport/server.py）
    2. Protocol Layer  → ProtocolDetector
    3. Governance Layer → MiddlewareChain
    4. Observability Layer → ObservabilityMiddleware（贯穿所有层）
    5. Client Layer → 外部 SDK

    本类负责协调 2/3/4 层，以及向上游 Provider 发送请求。
    """

    def __init__(
        self,
        middleware_chain: MiddlewareChain | None = None,
        policy_engine: PolicyEngine | None = None,
        provider_api_keys: dict[str, str] | None = None,
        provider_configs: dict[str, dict] | None = None,
        default_provider: str = "openai",
    ):
        self.middleware_chain = middleware_chain or MiddlewareChain()
        self.policy_engine = policy_engine or PolicyEngine()
        self.protocol_detector = ProtocolDetector()
        self.provider_api_keys = provider_api_keys or {}
        self.provider_configs = provider_configs or {}
        self.default_provider = default_provider
        self.observability = ObservabilityMiddleware()

        # 确保 Observability 在链中
        if not any(mw.name == "observability" for mw in self.middleware_chain.middlewares):
            self.middleware_chain.add(self.observability)

        # httpx 客户端（连接池复用）
        self._http_client: httpx.AsyncClient | None = None

    async def handle(self, ctx: RequestContext) -> dict[str, Any]:
        """处理请求——这是 Transport Layer 调用的入口。

        完整流程对应 AGRA-0001 §3.4 (Request Lifecycle):
        1. Protocol Layer: 识别协议
        2. Governance Layer: Middleware Chain 请求阶段
        3. Transport Layer: 转发到 Provider
        4. Governance Layer: Middleware Chain 响应阶段
        5. Observability: 记录日志/指标/追踪
        """
        # ─── 1. Protocol Layer ───
        protocol_name, handler = self.protocol_detector.detect(ctx.method, ctx.path)
        ctx.protocol = protocol_name

        # 浅层解析（提取 model/stream 等治理必需元数据）
        if handler:
            handler.extract_metadata(ctx)
        else:
            ctx.shallow_parse()

        # 如果没有指定 Provider，根据协议推断默认 Provider
        if not ctx.target_provider:
            ctx.target_provider = protocol_name if protocol_name != "unknown" else self.default_provider

        # ─── 2. Governance Layer: 请求阶段 ───
        # 检查 Policy 引擎，获取应跳过的 Middleware
        bypass = self.policy_engine.get_bypass_middlewares(ctx)

        # 手动执行 Middleware Chain（跳过被 bypass 的）
        for mw in self.middleware_chain.middlewares:
            if mw.name in bypass:
                logger.debug("Bypassing middleware: %s", mw.name)
                continue
            try:
                ctx = await mw.on_request(ctx)
            except Exception as e:
                logger.error("Middleware %s failed: %s", mw.name, e)
                raise

        # ─── 3. Transport Layer: 转发到 Provider ───
        if ctx.is_stream:
            result = await self._forward_stream(ctx, handler)
        else:
            result = await self._forward(ctx, handler)

        # ─── 4. Governance Layer: 响应阶段 ───
        for mw in reversed(self.middleware_chain.middlewares):
            if mw.name in bypass:
                continue
            try:
                if isinstance(result, Response):
                    result = await mw.on_response(ctx, result)
            except Exception as e:
                logger.warning("Middleware %s on_response error: %s", mw.name, e)

        # ─── 5. 返回结果给 Transport Layer ───
        return {
            "status": result.status,
            "headers": result.headers,
            "body": result.body if not result.is_stream else result.stream,
            "is_stream": result.is_stream,
        }

    async def _forward(self, ctx: RequestContext, handler: ProtocolHandler | None) -> Response:
        """非流式转发到 Provider。

        关键：请求体原样透传（Transport Transparency）。
        """
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))

        # 构造目标 URL
        endpoint = ctx.target_endpoint or self._get_endpoint(ctx, handler)
        url = f"{endpoint}{ctx.path}"

        # 准备 Header：移除 hop-by-hop Header，注入 Provider 认证
        headers = self._prepare_headers(ctx, handler)

        logger.info(
            "Forwarding %s → %s %s (model=%s, stream=%s)",
            ctx.request_id, ctx.target_provider, url, ctx.target_model, ctx.is_stream,
        )

        try:
            resp = await self._http_client.post(
                url,
                content=ctx.body_bytes,  # 原样透传请求体
                headers=headers,
            )

            # 提取 Usage
            usage = Usage()
            extractor = get_extractor(ctx.protocol)
            if extractor:
                usage = extractor.extract_from_response(resp.content)

            return Response(
                status=resp.status_code,
                headers=dict(resp.headers),
                body=resp.content,  # 原样透传响应体
                usage=usage,
            )
        except httpx.ConnectError as e:
            logger.error("Provider connection error: %s", e)
            return Response(
                status=503,
                body=b'{"error": {"type": "provider_unavailable", "message": "Provider unavailable"}}',
            )
        except httpx.TimeoutException as e:
            logger.error("Provider timeout: %s", e)
            return Response(
                status=504,
                body=b'{"error": {"type": "timeout", "message": "Provider timeout"}}',
            )

    async def _forward_stream(self, ctx: RequestContext, handler: ProtocolHandler | None) -> Response:
        """流式转发到 Provider（SSE 透传）。

        对应 AGRA-0001 §3.2 / AGRA-BOOK Chapter 5 §5.3。
        SSE 逐帧透传，不缓冲、不修改、不合并。
        """
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))

        endpoint = ctx.target_endpoint or self._get_endpoint(ctx, handler)
        url = f"{endpoint}{ctx.path}"
        headers = self._prepare_headers(ctx, handler)

        logger.info("Forwarding stream %s → %s %s", ctx.request_id, ctx.target_provider, url)

        client = self._http_client
        extractor = get_extractor(ctx.protocol)

        async def stream_generator() -> typing.AsyncIterator[bytes]:
            usage = Usage()
            try:
                async with client.stream("POST", url, content=ctx.body_bytes, headers=headers) as resp:
                    async for chunk in resp.aiter_bytes():
                        # 逐帧透传——不修改、不缓冲
                        yield chunk

                        # 提取 Usage（不修改 chunk）
                        u = extractor.extract_from_stream_chunk(chunk)
                        if u:
                            usage.add(u)

                # 流结束后，将 Usage 存入 metadata
                ctx.metadata["stream_usage"] = usage
            except Exception as e:
                logger.error("Stream error: %s", e)
                yield b'data: {"error": "stream interrupted"}\n\ndata: [DONE]\n\n'

        return Response(
            status=200,
            is_stream=True,
            stream=stream_generator(),
            usage=Usage(),  # Usage 在流结束后从 metadata 获取
        )

    def _get_endpoint(self, ctx: RequestContext, handler: ProtocolHandler | None) -> str:
        """获取 Provider 上游端点。"""
        if handler:
            return handler.get_provider_endpoint(ctx.target_model)
        # 回退到配置
        provider_config = self.provider_configs.get(ctx.target_provider, {})
        return provider_config.get("endpoint", "https://api.openai.com")

    def _prepare_headers(self, ctx: RequestContext, handler: ProtocolHandler | None) -> dict[str, str]:
        """准备转发 Header。

        对应 AGRA-0001 §3.2 / AGRA-BOOK Chapter 5 §5.2。
        最小化 Header 修改：注入 Provider 认证、追踪 ID。
        """
        headers = {}
        for key, val in ctx.headers.items():
            # 跳过 hop-by-hop Header
            if key.lower() in ("host", "connection", "transfer-encoding", "content-length"):
                continue
            headers[key] = val

        # 注入 Provider 认证
        provider_key = self.provider_api_keys.get(ctx.target_provider, "")
        if handler and provider_key:
            auth_headers = handler.get_auth_headers(provider_key)
            headers.update(auth_headers)

        # 注入追踪 Header
        headers["X-Request-ID"] = ctx.request_id
        headers["X-Trace-ID"] = ctx.trace_id

        return headers

    async def start(self) -> None:
        """初始化 Gateway。"""
        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        logger.info("AGRA Gateway started (providers: %s)", list(self.provider_configs.keys()))

    async def stop(self) -> None:
        """关闭 Gateway。"""
        if self._http_client:
            await self._http_client.aclose()
        logger.info("AGRA Gateway stopped")


# 避免循环引用中的类型检查问题
import typing
