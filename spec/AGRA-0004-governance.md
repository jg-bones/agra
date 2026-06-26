# AGRA-0004: Governance Model

| Field | Value |
|-------|-------|
| **Document ID** | AGRA-0004 |
| **Title** | Governance Model |
| **Status** | Draft |
| **Version** | 0.1 |
| **Last Updated** | 2026-06-26 |
| **Type** | Specification |
| **Depends On** | AGRA-0001, AGRA-0002 |

---

## 1. Summary

本规范定义 AGRA Governance Layer 的架构、组件和接口。治理层负责所有跨协议的统一管理能力：认证、授权、路由、限流、计费和审计。治理层通过 Middleware Chain 模式实现，与 Protocol Layer 完全解耦。

## 2. Architecture

```
Request → [Auth] → [Rate Limit] → [Router] → [Billing] → Provider
                                                        │
Response ← [Audit] ← [Billing] ← [Usage Extract] ←──────┘
```

### 设计原则

- 每个 Middleware 是独立的，不依赖其他 Middleware 的内部状态
- Middleware 可以配置为跳过（如内部服务调用跳过 Rate Limit）
- Middleware 可以按路由规则差异化配置（如不同模型限流策略不同）
- Middleware 的执行顺序可配置

## 3. Middleware Interface

```python
from typing import Optional

class Middleware:
    """AGRA Middleware 基类。所有治理组件继承此类。"""

    name: str  # Middleware 唯一标识

    async def on_request(self, context: RequestContext) -> RequestContext:
        """
        在请求发送到 Provider 之前调用。
        可以修改 context（如注入认证信息），也可以终止请求（抛出异常）。
        """
        return context

    async def on_response(
        self, context: RequestContext, response: Response
    ) -> Response:
        """
        在响应返回给客户端之前调用。
        可以修改 response（如添加 Header），也可以用于记录数据。
        """
        return response

    async def on_stream_event(
        self, context: RequestContext, event: StreamEvent
    ) -> StreamEvent:
        """
        在流式响应的每个事件上调用。
        用于在不缓冲流的情况下观测流事件。
        """
        return event

    async def on_error(
        self, context: RequestContext, error: Exception
    ) -> None:
        """当请求处理出错时调用。"""
        pass
```

### RequestContext

```python
@dataclass
class RequestContext:
    request_id: str
    trace_id: str
    # 客户端信息
    client_org_id: str
    client_user_id: str
    client_api_key_id: str
    # 请求信息
    method: str
    path: str
    protocol: str          # openai / anthropic / gemini
    headers: dict
    body_bytes: bytes      # 原始请求体（不解析）
    # 路由信息
    target_provider: Optional[str] = None
    target_model: Optional[str] = None
    target_endpoint: Optional[str] = None
    # 元数据
    metadata: dict = field(default_factory=dict)
```

## 4. Authentication

### 4.1 客户端认证

Gateway 接收客户端请求后，通过 Auth Middleware 验证客户端身份：

```
Client API Key (面向用户) → Gateway (Auth Middleware) → Provider API Key (面向上游)
```

支持的认证方式：

| 方式 | Header | 适用场景 |
|------|--------|---------|
| API Key | `Authorization: Bearer <key>` | 最常用 |
| JWT | `Authorization: Bearer <jwt>` | 组织级认证 |
| OAuth 2.0 | `Authorization: Bearer <token>` | 第三方集成 |
| mTLS | TLS 证书 | 服务间通信 |

### 4.2 Provider 认证注入

Auth Middleware 验证客户端身份后，根据路由结果注入目标 Provider 的 API Key：

- OpenAI: `Authorization: Bearer <provider_key>`
- Anthropic: `x-api-key: <provider_key>`, `anthropic-version: 2023-06-01`
- Gemini: `x-goog-api-key: <provider_key>`

## 5. Authorization

基于 RBAC（Role-Based Access Control）模型：

### 实体定义

| 实体 | 说明 |
|------|------|
| Organization | 组织，拥有多个 API Key |
| User | 用户，属于一个或多个 Organization |
| API Key | 归属于 Organization |
| Role | 角色：Admin / Developer / Viewer |
| Permission | 细粒度权限 |

### 权限示例

| Permission | 说明 |
|-----------|------|
| `model:access:gpt-5` | 访问 GPT-5 模型 |
| `model:access:*` | 访问所有模型 |
| `billing:view` | 查看计费 |
| `rate_limit:override` | 覆盖限流配置 |
| `admin:api_keys` | 管理 API Key |

## 6. Routing

### 6.1 路由策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| Round Robin | 轮询 | 均衡加载 |
| Weighted | 按权重分配 | 部分 Provider 容量大 |
| Latency-Aware | 优先低延迟 Provider | 对响应时间敏感 |
| Cost-Aware | 优先低成本 Provider | 成本控制 |
| Fallback | 主不可用切换备用 | 高可用 |
| Capability-Aware | 根据请求特性选择 Provider | Thinking/Grounding 路由 |
| Sticky | 同一会话固定 Provider | 上下文一致性 |

### 6.2 Router Interface

```python
class Router:
    """路由器接口。选择目标 Provider。"""

    async def select(
        self, context: RequestContext, candidates: list[ProviderCandidate]
    ) -> ProviderCandidate:
        """从候选 Provider 中选择一个。"""
        pass

@dataclass
class ProviderCandidate:
    provider: str           # openai / anthropic / gemini
    endpoint: str           # 上游端点 URL
    model: str              # 模型名称
    weight: float = 1.0     # 权重
    priority: int = 0       # 优先级（用于 Fallback）
    capabilities: set = field(default_factory=set)  # 支持的能力集合
```

## 7. Rate Limiting

### 7.1 限流维度

| 维度 | 时间窗口 | 典型策略 |
|------|---------|---------|
| User | per minute | Token Bucket |
| Organization | per day | Sliding Window |
| Model | per minute | Leaky Bucket |
| Provider | per minute | Fixed Window |
| IP | per second | Token Bucket |
| Endpoint | per minute | Sliding Window |

### 7.2 限流算法

| 算法 | 特点 | 适用场景 |
|------|------|---------|
| Token Bucket | 允许突发 | API 限流 |
| Leaky Bucket | 平滑输出 | 流量整形 |
| Fixed Window | 简单高效 | 粗粒度限流 |
| Sliding Window | 精确 | 精细限流 |

### 7.3 限流响应

当请求被限流时，Gateway 应返回：

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719403200

{
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded. Retry after 60 seconds."
  }
}
```

## 8. Billing

### 8.1 计费模型

| 维度 | 说明 |
|------|------|
| 按 Token | 按 input_tokens + output_tokens 计费 |
| 按模型 | 不同模型差异化定价 |
| 按请求 | 固定费用 per request |
| 混合 | Token + 请求费 |

### 8.2 成本追踪

每个请求记录以下成本数据：

```json
{
  "request_id": "req_abc123",
  "provider_cost_usd": 0.015,    // 上游 Provider 实际成本
  "billing_cost_usd": 0.020,     // 向客户计费金额
  "margin_usd": 0.005,           // 利润
  "usage": {
    "input_tokens": 500,
    "output_tokens": 200,
    "cached_tokens": 100
  },
  "model": "claude-sonnet-4-5"
}
```

## 9. Policy Engine

声明式规则，不编写代码：

```yaml
policies:
  - name: "high-cost-model-rate-limit"
    description: "限制高成本模型的调用频率"
    match:
      model: ["gpt-5", "claude-opus-5"]
    action:
      rate_limit:
        requests_per_minute: 10
        tokens_per_minute: 100000

  - name: "internal-service-bypass-auth"
    match:
      source_ip: ["10.0.0.0/8"]
      headers:
        X-Internal-Service: "true"
    action:
      bypass:
        - auth
        - rate_limit

  - name: "thinking-capability-routing"
    match:
      body_contains: "thinking"  # 请求体包含 thinking 字段
    action:
      route:
        require_capability: "thinking"
        fallback: "claude-sonnet-4-5"
```

## 10. Conformance Requirements

| 编号 | 要求 |
|------|------|
| GOV-001 | 必须实现 Middleware Chain 模式 |
| GOV-002 | 必须支持 API Key 认证 |
| GOV-003 | 必须支持至少一种限流算法 |
| GOV-004 | 必须支持至少一种路由策略 |
| GOV-005 | 治理逻辑不得依赖请求体解析（保持 Transport Transparency） |
| GOV-006 | Middleware 必须可独立配置和跳过 |

## 11. References

- AGRA-0001: Architecture
- AGRA-0002: Terminology
- AGRA-0005: Observability
