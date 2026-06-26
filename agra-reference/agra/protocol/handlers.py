"""
AGRA Protocol Layer — 协议检测与 Handler。

对应 AGRA-0001 §3.3 (Protocol Layer) 和 AGRA-BOOK Chapter 6。
核心原则：Protocol Preservation — 默认行为是透传，而非转换。
"""
from __future__ import annotations

import abc
import logging
from typing import Any, Optional

from agra.context import RequestContext

logger = logging.getLogger("agra.protocol")


class ProtocolHandler(abc.ABC):
    """Protocol Handler 基类。

    对应 AGRA-0001 §6.3 / AGRA-BOOK Chapter 6。

    关键约束：Handler 的默认行为是透传（passthrough），而非转换。
    这体现了 Principle 1: Protocol Preservation。
    """

    protocol: str = "unknown"

    @abc.abstractmethod
    def matches(self, method: str, path: str) -> bool:
        """判断请求是否属于此协议。"""
        ...

    def extract_metadata(self, ctx: RequestContext) -> dict[str, Any]:
        """从请求中提取元数据（浅层解析，不破坏 Transport Transparency）。

        对应 AGRA-0001 §6.4：只读取顶层 model/stream 字段。
        """
        return ctx.shallow_parse()

    def get_provider_endpoint(self, model: str | None) -> str:
        """获取此协议对应的 Provider 上游端点。"""
        raise NotImplementedError

    def get_auth_headers(self, api_key: str) -> dict[str, str]:
        """构造此协议的认证 Header。对应 AGRA-0002 §3.2。"""
        raise NotImplementedError

    def passthrough(self, ctx: RequestContext, provider_endpoint: str) -> str:
        """构造对 Provider 的请求 URL（默认：透传路径）。

        这是 TLG 模式的核心——不修改请求体，只构造目标 URL。
        """
        return provider_endpoint


class OpenAIProtocolHandler(ProtocolHandler):
    """OpenAI 协议 Handler。

    支持端点：
    - POST /v1/chat/completions
    - POST /v1/responses
    - POST /v1/embeddings
    - GET  /v1/models
    """

    protocol = "openai"

    OPENAI_PATHS = {
        "/v1/chat/completions",
        "/v1/responses",
        "/v1/embeddings",
        "/v1/models",
    }

    def matches(self, method: str, path: str) -> bool:
        return path in self.OPENAI_PATHS or path.startswith("/v1/")

    def get_provider_endpoint(self, model: str | None) -> str:
        return "https://api.openai.com"

    def get_auth_headers(self, api_key: str) -> dict[str, str]:
        # AGRA-0002 §3.2: OpenAI 使用 Authorization: Bearer
        return {"Authorization": f"Bearer {api_key}"}


class AnthropicProtocolHandler(ProtocolHandler):
    """Anthropic 协议 Handler。

    支持端点：
    - POST /v1/messages
    - POST /v1/messages/count_tokens
    """

    protocol = "anthropic"

    def matches(self, method: str, path: str) -> bool:
        return path.startswith("/v1/messages")

    def get_provider_endpoint(self, model: str | None) -> str:
        return "https://api.anthropic.com"

    def get_auth_headers(self, api_key: str) -> dict[str, str]:
        # AGRA-0002 §3.2: Anthropic 使用 x-api-key + anthropic-version
        return {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }


class GeminiProtocolHandler(ProtocolHandler):
    """Gemini 协议 Handler。

    支持端点：
    - POST /v1beta/models/{model}:generateContent
    - POST /v1beta/models/{model}:streamGenerateContent
    """

    protocol = "gemini"

    def matches(self, method: str, path: str) -> bool:
        return "/v1beta/models/" in path and (
            ":generateContent" in path or ":streamGenerateContent" in path
        )

    def get_provider_endpoint(self, model: str | None) -> str:
        return "https://generativelanguage.googleapis.com"

    def get_auth_headers(self, api_key: str) -> dict[str, str]:
        # AGRA-0002 §3.2: Gemini 使用 x-goog-api-key
        return {"x-goog-api-key": api_key}


class ProtocolDetector:
    """协议检测器。

    对应 AGRA-0001 §3.3：根据请求路径自动检测协议类型。
    """

    def __init__(self) -> None:
        # 顺序很重要：Anthropic 和 Gemini 必须在 OpenAI 之前检测，
        # 因为 OpenAI 的 matches() 会匹配所有 /v1/ 开头的路径
        self.handlers: list[ProtocolHandler] = [
            AnthropicProtocolHandler(),
            GeminiProtocolHandler(),
            OpenAIProtocolHandler(),
        ]

    def detect(self, method: str, path: str) -> tuple[str, Optional[ProtocolHandler]]:
        """检测协议类型，返回 (protocol_name, handler)。

        如果没有匹配的 Handler，返回 ("unknown", None)。
        此时仍然透传请求（不拒绝未知协议），体现 Protocol Preservation。
        """
        for handler in self.handlers:
            if handler.matches(method, path):
                logger.debug("Protocol detected: %s for %s %s", handler.protocol, method, path)
                return handler.protocol, handler

        # 未知协议也透传——这是 Protocol Preservation 的体现
        logger.debug("Unknown protocol for %s %s, will passthrough", method, path)
        return "unknown", None

    def register(self, handler: ProtocolHandler) -> None:
        """注册自定义 Protocol Handler。"""
        self.handlers.append(handler)
