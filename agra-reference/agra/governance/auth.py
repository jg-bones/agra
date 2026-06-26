"""
AGRA Auth Middleware — 认证与授权。

对应 AGRA-0004 §4 (Authentication) 和 §5 (Authorization)。

两个职责：
1. 验证客户端身份（客户端认证）
2. 注入 Provider API Key（Provider 认证注入）
"""
from __future__ import annotations

import logging

from agra.context import RequestContext
from agra.governance.middleware import Middleware

logger = logging.getLogger("agra.governance.auth")


class AuthError(Exception):
    """认证失败。"""

    def __init__(self, message: str, status: int = 401):
        self.message = message
        self.status = status
        super().__init__(message)


class AuthMiddleware(Middleware):
    """认证 Middleware。

    对应 AGRA-0004 §4。

    流程：
    Client API Key → 验证 → 注入 Provider API Key → Provider
    """

    name = "auth"

    def __init__(
        self,
        client_api_keys: dict[str, dict] | None = None,
        provider_api_keys: dict[str, str] | None = None,
    ):
        """
        Args:
            client_api_keys: 客户端 API Key → {org_id, user_id, scopes}
            provider_api_keys: Provider 名 → API Key
        """
        self.client_api_keys = client_api_keys or {}
        self.provider_api_keys = provider_api_keys or {}

    async def on_request(self, ctx: RequestContext) -> RequestContext:
        # 1. 提取客户端 API Key
        client_key = ctx.headers.get("Authorization", "").replace("Bearer ", "")
        if not client_key:
            client_key = ctx.headers.get("x-api-key", "")
        if not client_key:
            client_key = ctx.headers.get("x-goog-api-key", "")

        # 2. 验证客户端身份
        if not client_key:
            # Demo 模式：允许无认证（生产环境应拒绝）
            ctx.client_org_id = "org_demo"
            ctx.client_user_id = "user_demo"
            ctx.client_api_key_id = "key_demo"
            logger.debug("No API key, using demo mode for %s", ctx.request_id)
        elif client_key in self.client_api_keys:
            info = self.client_api_keys[client_key]
            ctx.client_org_id = info.get("org_id", "org_unknown")
            ctx.client_user_id = info.get("user_id", "user_unknown")
            ctx.client_api_key_id = client_key[:12] + "..."
        else:
            # Demo 模式：允许未注册的 API Key（生产环境应拒绝）
            ctx.client_org_id = "org_demo"
            ctx.client_user_id = "user_demo"
            ctx.client_api_key_id = client_key[:12] + "..."
            logger.debug("Unknown API key, using demo mode for %s", ctx.request_id)

        # 3. 注入 Provider 认证（Provider 认证注入，AGRA-0004 §4.2）
        provider = ctx.target_provider
        if provider and provider in self.provider_api_keys:
            provider_key = self.provider_api_keys[provider]
            # 根据协议设置正确的认证 Header
            if ctx.protocol == "openai":
                ctx.headers["Authorization"] = f"Bearer {provider_key}"
            elif ctx.protocol == "anthropic":
                ctx.headers["x-api-key"] = provider_key
                ctx.headers["anthropic-version"] = "2023-06-01"
            elif ctx.protocol == "gemini":
                ctx.headers["x-goog-api-key"] = provider_key
            # 移除客户端的认证信息，避免泄露
            # （实际上 httpx 会用 ctx.headers 发请求，这里已替换为 Provider Key）

        return ctx
