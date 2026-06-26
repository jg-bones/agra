# AGRA-0005: Observability

| Field | Value |
|-------|-------|
| **Document ID** | AGRA-0005 |
| **Title** | Observability |
| **Status** | Draft |
| **Version** | 0.1 |
| **Last Updated** | 2026-06-26 |
| **Type** | Specification |
| **Depends On** | AGRA-0001, AGRA-0002 |

---

## 1. Summary

本规范定义 AGRA Observability Layer 的三根支柱（Logging、Metrics、Tracing）及其数据模型。可观测性是横切关注点，贯穿五层模型的所有层。

## 2. Three Pillars

```
┌──────────────────────────────────────────────────────┐
│                  OBSERVABILITY                       │
├───────────────┬──────────────────┬──────────────────┤
│    LOGGING    │     METRICS      │     TRACING      │
│  Request/     │  Throughput      │  Distributed     │
│  Response     │  Latency         │  Trace Context   │
│  Audit        │  Error Rate      │  Span Hierarchy  │
│  Structured   │  Token Usage     │  Baggage         │
└───────────────┴──────────────────┴──────────────────┘
```

## 3. Logging

### 3.1 结构化日志格式

所有日志采用 JSON 结构化格式，包含以下核心字段：

```json
{
  "timestamp": "2026-06-26T14:30:00.000Z",
  "level": "info",
  "request_id": "req_abc123",
  "trace_id": "trace_xyz789",
  "client": {
    "org_id": "org_001",
    "user_id": "user_001",
    "api_key_id": "key_001"
  },
  "request": {
    "method": "POST",
    "path": "/v1/messages",
    "protocol": "anthropic",
    "model": "claude-sonnet-4-5",
    "stream": true
  },
  "response": {
    "status_code": 200,
    "latency_ms": 1234,
    "ttft_ms": 450
  },
  "provider": {
    "name": "anthropic",
    "endpoint": "https://api.anthropic.com",
    "latency_ms": 1100
  },
  "usage": {
    "input_tokens": 500,
    "output_tokens": 200,
    "total_tokens": 700,
    "cached_tokens": 100,
    "cost_usd": 0.015
  },
  "governance": {
    "route_strategy": "latency-aware",
    "rate_limit_consumed": 1,
    "rate_limit_remaining": 999
  }
}
```

### 3.2 日志级别

| 级别 | 用途 |
|------|------|
| ERROR | 请求失败、Provider 错误 |
| WARN | 限流、降级、重试 |
| INFO | 正常请求记录 |
| DEBUG | 调试信息（生产环境默认关闭） |

### 3.3 审计日志

审计日志独立于请求日志，记录管理操作：

```json
{
  "timestamp": "2026-06-26T14:30:00.000Z",
  "event": "api_key.created",
  "actor": {
    "user_id": "user_001",
    "org_id": "org_001"
  },
  "resource": {
    "type": "api_key",
    "id": "key_002"
  },
  "details": {
    "scopes": ["model:access:*"]
  }
}
```

### 3.4 日志保留策略

| 日志类型 | 默认保留 | 说明 |
|---------|---------|------|
| 请求日志 | 30 天 | 可配置 |
| 审计日志 | 365 天 | 合规要求 |
| 错误日志 | 90 天 | 故障排查 |

## 4. Metrics

### 4.1 核心指标

#### 请求指标

| 指标 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `gateway_requests_total` | Counter | protocol, model, provider, status | 总请求数 |
| `gateway_request_duration_ms` | Histogram | protocol, model, provider | 请求总延迟 |
| `gateway_provider_duration_ms` | Histogram | provider, model | Provider 延迟 |
| `gateway_ttft_ms` | Histogram | protocol, model, provider | Time to First Token |

#### 错误指标

| 指标 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `gateway_errors_total` | Counter | protocol, error_type, status | 错误总数 |
| `gateway_provider_errors_total` | Counter | provider, error_type | Provider 错误 |
| `gateway_timeouts_total` | Counter | provider | 超时次数 |

#### 用量指标

| 指标 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `gateway_input_tokens_total` | Counter | model, provider, org | 输入 Token |
| `gateway_output_tokens_total` | Counter | model, provider, org | 输出 Token |
| `gateway_cached_tokens_total` | Counter | model, provider | 缓存 Token |
| `gateway_cost_usd_total` | Counter | model, provider, org | 总成本 |

#### 治理指标

| 指标 | 类型 | 标签 | 说明 |
|------|------|------|------|
| `gateway_rate_limited_total` | Counter | org, model | 被限流次数 |
| `gateway_circuit_breaker_open_total` | Counter | provider | 熔断器打开次数 |
| `gateway_retries_total` | Counter | provider | 重试次数 |

### 4.2 指标导出

推荐使用 Prometheus 格式导出：

```
# HELP gateway_requests_total Total number of requests
# TYPE gateway_requests_total counter
gateway_requests_total{protocol="anthropic",model="claude-sonnet-4-5",provider="anthropic",status="200"} 15234
gateway_requests_total{protocol="openai",model="gpt-5",provider="openai",status="200"} 89201
```

## 5. Tracing

### 5.1 Trace Context

采用 W3C Trace Context 标准：

```
Client → Gateway (创建 Root Span) → Provider (创建 Child Span)
```

### 5.2 Span 层次

```
Span: gateway.request (root)
├── Span: gateway.auth
├── Span: gateway.rate_limit
├── Span: gateway.route
├── Span: gateway.provider_call
│   ├── Event: request_sent
│   ├── Event: first_token (streaming only)
│   └── Event: response_received
├── Span: gateway.usage_extract
├── Span: gateway.billing
└── Span: gateway.audit
```

### 5.3 Span Attributes

遵循 OpenTelemetry GenAI Semantic Conventions：

| Attribute | 说明 |
|-----------|------|
| `gateway.protocol` | 协议标识（openai/anthropic/gemini） |
| `gateway.model` | 请求的模型名称 |
| `gateway.provider` | 上游 Provider |
| `gateway.route_strategy` | 路由策略 |
| `gateway.organization` | 组织 ID |
| `gen_ai.system` | GenAI 系统名称 |
| `gen_ai.request.model` | 请求模型 |
| `gen_ai.usage.input_tokens` | 输入 Token |
| `gen_ai.usage.output_tokens` | 输出 Token |

### 5.4 Trace 传播

Gateway 必须将 Trace Context 传播到 Provider：

```
traceparent: 00-{trace-id}-{span-id}-01
```

> 注意：并非所有 Provider 都会处理 traceparent Header，但 Gateway 应始终发送。

## 6. Alerting

### 6.1 告警规则示例

```yaml
alerts:
  - name: "high-error-rate"
    condition: "rate(gateway_errors_total[5m]) / rate(gateway_requests_total[5m]) > 0.05"
    for: "2m"
    severity: "critical"
    notify: ["slack", "pagerduty"]

  - name: "provider-latency-high"
    condition: "histogram_quantile(0.95, gateway_provider_duration_ms) > 5000"
    for: "5m"
    severity: "warning"
    notify: ["slack"]

  - name: "cost-anomaly"
    condition: "rate(gateway_cost_usd_total[1h]) > 100"
    for: "10m"
    severity: "warning"
    notify: ["email"]
```

## 7. Conformance Requirements

| 编号 | 要求 |
|------|------|
| OBS-001 | 必须支持结构化日志（JSON 格式） |
| OBS-002 | 必须支持至少一种 Metrics 导出格式（推荐 Prometheus） |
| OBS-003 | 必须支持分布式追踪（推荐 W3C Trace Context） |
| OBS-004 | 必须记录 request_id 和 trace_id |
| OBS-005 | 必须支持 Token 用量提取 |
| OBS-006 | 可观测性数据采集不得修改请求/响应体（Transport Transparency） |

## 8. References

- AGRA-0001: Architecture
- AGRA-0004: Governance Model
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
