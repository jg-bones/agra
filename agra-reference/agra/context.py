"""
AGRA RequestContext — 贯穿所有层的请求上下文。

对应 AGRA-0001 §3.4 / AGRA-0004 §3 (RequestContext)。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RequestContext:
    """请求上下文，在 Middleware Chain 中传递。

    治理层通过此对象获取请求元数据，但不解析完整请求体（Transport Transparency）。
    """

    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:16]}")
    # 客户端信息
    client_org_id: str = "org_unknown"
    client_user_id: str = "user_unknown"
    client_api_key_id: str = "key_unknown"
    # 请求信息
    method: str = "POST"
    path: str = "/"
    protocol: str = "unknown"  # openai / anthropic / gemini
    headers: dict[str, str] = field(default_factory=dict)
    body_bytes: bytes = b""
    # 路由结果
    target_provider: Optional[str] = None
    target_model: Optional[str] = None
    target_endpoint: Optional[str] = None
    # 元数据（Middleware 可读写）
    metadata: dict[str, Any] = field(default_factory=dict)
    # 时间戳
    start_time: float = field(default_factory=time.time)
    # 浅层解析的元数据（不破坏 Transport Transparency）
    is_stream: bool = False

    @property
    def latency_ms(self) -> float:
        return (time.time() - self.start_time) * 1000

    def shallow_parse(self) -> dict[str, Any]:
        """浅层解析请求体，提取治理必需的少量字段。

        对应 AGRA-0001 §6.4：只读取顶层 model/stream 字段，不解析完整结构。
        """
        import json

        try:
            body = json.loads(self.body_bytes)
            if isinstance(body, dict):
                self.target_model = body.get("model", self.target_model)
                self.is_stream = body.get("stream", False)
                return {"model": self.target_model, "stream": self.is_stream}
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return {}


@dataclass
class ProviderCandidate:
    """路由候选 Provider。对应 AGRA-0004 §6.2。"""

    provider: str
    endpoint: str
    model: str
    weight: float = 1.0
    priority: int = 0
    capabilities: set[str] = field(default_factory=set)


@dataclass
class Usage:
    """Token 用量。对应 AGRA-0004 §8。"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens
        self.cached_tokens += other.cached_tokens
        self.cost_usd += other.cost_usd
