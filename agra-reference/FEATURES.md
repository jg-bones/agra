# AGRA Reference — 功能清单与验证指南

> 本文件是 AGRA 参考实现的**功能索引**。
> 每个功能列出：实现位置、关键代码、验证方式。
> 供人类阅读，也供 AI 快速定位。

---

## 功能总览

| # | 功能 | 状态 | 实现文件 | 验证测试 |
|---|------|------|---------|---------|
| 1 | 原样请求（请求体透传） | ✅ | `agra/gateway.py` | `test_arch_004` |
| 2 | 原样响应（响应体透传） | ✅ | `agra/gateway.py` | `test_arch_003` |
| 3 | 全协议（OpenAI / Anthropic / Gemini） | ✅ | `agra/protocol/handlers.py` | `test_pc_1` |
| 4 | 统一认证 | ✅ | `agra/governance/auth.py` | `test_gov_002` |
| 5 | 统一限流 | ✅ | `agra/governance/rate_limit.py` | `test_gov_003` |
| 6 | 统一 Usage | ✅ | `agra/usage/extractor.py` | `test_obs_005` |
| 7 | 统一日志 | ✅ | `agra/observability/observability.py` | `test_obs_001` |

运行全部验证：`pytest tests/ -v`（29 个测试，0.1 秒完成）

---

## 1. 原样请求（请求体透传）

**原则：** Transport Transparency — 不修改 Request Body。

**实现位置：** `agra/gateway.py` → `_forward()` 方法

**关键代码：**

```python
# gateway.py, _forward() 方法
resp = await self._http_client.post(
    url,
    content=ctx.body_bytes,  # ← 原样透传请求体，不解析、不修改
    headers=headers,
)
```

**为什么有效：** Gateway 将客户端发来的原始字节流直接作为 HTTP 请求体转发给 Provider。全程不调用 `json.loads()`，不构造新 dict，不过滤任何字段。这就是 `thinking`、`cache_control` 等参数不会丢失的原因。

**验证：**

```bash
# 运行测试
pytest tests/test_compat.py::TestArchitecture::test_arch_004_no_silent_param_drop -v

# 测试内容：请求体包含 thinking/cache_control/unknown_future_param，
# 经过 Protocol Handler 后，所有字段完整保留
```

---

## 2. 原样响应（响应体透传）

**原则：** Transport Transparency — 不修改 Response Body。

**实现位置：** `agra/gateway.py` → `_forward()` 方法

**关键代码：**

```python
# gateway.py, _forward() 方法
return Response(
    status=resp.status_code,
    headers=dict(resp.headers),
    body=resp.content,  # ← 原样透传响应体
    usage=usage,
)
```

**流式响应：** `agra/gateway.py` → `_forward_stream()` 方法

```python
# gateway.py, _forward_stream() 方法
async for chunk in resp.aiter_bytes():
    yield chunk  # ← 逐帧透传，不缓冲、不修改、不合并
```

**为什么有效：** Provider 返回的响应体原样传回客户端。Usage 提取是在旁路进行的（通过 `UsageExtractor` 解析响应内容），不会修改响应体本身。

**验证：**

```bash
pytest tests/test_compat.py::TestArchitecture::test_arch_003_default_passthrough -v
pytest tests/test_compat.py::TestPatterns::test_pat_002_tlg_pc5 -v
```

---

## 3. 全协议（OpenAI / Anthropic / Gemini）

**实现位置：** `agra/protocol/handlers.py`

**三个 Protocol Handler：**

| Handler | 协议标识 | 端点 | 认证方式 |
|---------|---------|------|---------|
| `OpenAIProtocolHandler` | `openai` | `/v1/chat/completions`, `/v1/responses` | `Authorization: Bearer <key>` |
| `AnthropicProtocolHandler` | `anthropic` | `/v1/messages` | `x-api-key: <key>` + `anthropic-version` |
| `GeminiProtocolHandler` | `gemini` | `/v1beta/models/{model}:generateContent` | `x-goog-api-key: <key>` |

**协议检测：** `ProtocolDetector.detect(method, path)` 根据请求路径自动识别协议。

**关键代码：**

```python
# protocol/handlers.py
class ProtocolDetector:
    def detect(self, method, path) -> tuple[str, ProtocolHandler]:
        for handler in self.handlers:
            if handler.matches(method, path):
                return handler.protocol, handler
        return "unknown", None  # 未知协议也透传
```

**每个 Handler 的默认行为是透传**（不是转换），体现 Protocol Preservation 原则。

**验证：**

```bash
pytest tests/test_compat.py::TestCompatibility::test_pc_1_endpoint_compatible -v
pytest tests/test_compat.py::TestCompatibility::test_pc_4_sdk_compatible -v
```

---

## 4. 统一认证

**实现位置：** `agra/governance/auth.py` → `AuthMiddleware`

**两个职责：**

| 职责 | 说明 |
|------|------|
| 客户端认证 | 验证客户端 API Key，识别 org_id / user_id |
| Provider 认证注入 | 根据目标协议，注入正确的 Provider API Key |

**关键代码：**

```python
# governance/auth.py
async def on_request(self, ctx):
    # 1. 提取客户端 API Key（支持三种 Header 格式）
    client_key = ctx.headers.get("Authorization", "").replace("Bearer ", "")
    if not client_key:
        client_key = ctx.headers.get("x-api-key", "")
    if not client_key:
        client_key = ctx.headers.get("x-goog-api-key", "")

    # 2. 验证客户端身份 → 设置 org_id, user_id

    # 3. 根据协议注入 Provider 认证
    if ctx.protocol == "openai":
        ctx.headers["Authorization"] = f"Bearer {provider_key}"
    elif ctx.protocol == "anthropic":
        ctx.headers["x-api-key"] = provider_key
        ctx.headers["anthropic-version"] = "2023-06-01"
    elif ctx.protocol == "gemini":
        ctx.headers["x-goog-api-key"] = provider_key
```

**统一性：** 无论客户端用哪种协议，认证逻辑只在 `AuthMiddleware` 中实现一次。新增加密方式只需修改这一个文件。

**验证：**

```bash
pytest tests/test_compat.py::TestGovernance::test_gov_002_api_key_auth -v
```

---

## 5. 统一限流

**实现位置：** `agra/governance/rate_limit.py` → `RateLimitMiddleware`

**多维度限流：**

| 维度 | 说明 | 配置示例 |
|------|------|---------|
| User | 按用户限流 | `capacity: 100, refill_rate: 10` |
| Organization | 按组织限流 | `capacity: 1000, refill_rate: 100` |
| Model | 按模型限流 | 限制高成本模型 |
| Provider | 按 Provider 限流 | 保护上游配额 |
| IP | 按 IP 限流 | 防滥用 |

**算法：** Token Bucket（可扩展为 Leaky Bucket / Sliding Window）

**关键代码：**

```python
# governance/rate_limit.py
class RateLimitMiddleware(Middleware):
    async def on_request(self, ctx):
        for dimension, config in self.limits.items():
            key = self._get_bucket_key(dimension, ctx)  # 如 "user:alice"
            bucket = self.buckets[key]
            if not bucket.consume(1):
                raise RateLimitExceeded(f"Rate limit exceeded for {dimension}")
```

**统一性：** 限流逻辑与协议无关。无论请求是 OpenAI、Anthropic 还是 Gemini 协议，都经过同一个限流 Middleware。

**验证：**

```bash
pytest tests/test_compat.py::TestGovernance::test_gov_003_rate_limit -v
# 测试：capacity=2 的 bucket，第三次请求触发限流
```

---

## 6. 统一 Usage

**实现位置：** `agra/usage/extractor.py`

**三个 Usage Extractor：**

| Extractor | 协议 | 用量字段 |
|-----------|------|---------|
| `OpenAIUsageExtractor` | openai | `usage.prompt_tokens` / `completion_tokens` |
| `AnthropicUsageExtractor` | anthropic | `usage.input_tokens` / `output_tokens` / `cache_read_input_tokens` |
| `GeminiUsageExtractor` | gemini | `usageMetadata.promptTokenCount` / `candidatesTokenCount` |

**统一输出：** 无论哪个协议，最终都输出统一的 `Usage` 对象：

```python
@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_tokens: int
    cost_usd: float
```

**关键代码：**

```python
# usage/extractor.py
EXTRACTORS = {
    "openai": OpenAIUsageExtractor(),
    "anthropic": AnthropicUsageExtractor(),
    "gemini": GeminiUsageExtractor(),
}

def get_extractor(protocol: str) -> UsageExtractor:
    return EXTRACTORS.get(protocol, OpenAIUsageExtractor())
```

**流式支持：** 每个 Extractor 同时实现 `extract_from_response()`（非流式）和 `extract_from_stream_chunk()`（流式）。

**验证：**

```bash
pytest tests/test_compat.py::TestObservability::test_obs_005_usage_extraction -v
pytest tests/test_compat.py::TestCompatibility::test_pc_2_schema_compatible -v
pytest tests/test_compat.py::TestCompatibility::test_pc_3_streaming_compatible -v
```

---

## 7. 统一日志

**实现位置：** `agra/observability/observability.py` → `ObservabilityMiddleware`

**三根支柱：**

| 支柱 | 实现 | 输出 |
|------|------|------|
| Logging | `on_response()` 中的 `logger.info(json.dumps(...))` | 结构化 JSON 日志 |
| Metrics | `self.metrics` 字典 + `get_metrics_summary()` | Prometheus 格式 |
| Tracing | `self.traces` 字典 + `Span` 对象 | W3C Trace Context |

**结构化日志格式（每个请求一条）：**

```json
{
  "timestamp": "2026-06-26T14:30:00.000Z",
  "level": "INFO",
  "request_id": "req_abc123",
  "trace_id": "trace_xyz789",
  "client": {"org_id": "org_demo", "user_id": "user_demo"},
  "request": {"method": "POST", "path": "/v1/messages", "protocol": "anthropic", "model": "claude-sonnet-4-5"},
  "response": {"status_code": 200, "latency_ms": 1234.5},
  "provider": {"name": "anthropic"},
  "usage": {"input_tokens": 500, "output_tokens": 200, "cost_usd": 0.015}
}
```

**Metrics 端点：** `GET /metrics` → Prometheus 格式

```
agra_requests_total_openai 15234
agra_requests_total_anthropic 8920
agra_latency_samples_gpt-4o_count 100
agra_latency_samples_gpt-4o_p95_ms 234.5
agra_cost_usd_total_org_acme 15.67
```

**统一性：** 无论哪个协议的请求，都经过同一个 `ObservabilityMiddleware`，产生统一格式的日志、指标和追踪。

**验证：**

```bash
pytest tests/test_compat.py::TestObservability::test_obs_001_structured_logging -v
pytest tests/test_compat.py::TestObservability::test_obs_002_metrics -v
pytest tests/test_compat.py::TestObservability::test_obs_003_tracing -v
```

---

## 端到端验证

### 方式一：运行 Conformance Test

```bash
cd agra-reference
pip install -r requirements.txt
pytest tests/ -v
```

预期输出：`29 passed in 0.1s`

### 方式二：启动 Gateway 并发送请求

```bash
# 终端 1：启动 Gateway
python examples/run_demo.py

# 终端 2：运行客户端示例（7 个场景）
python examples/client_example.py
```

客户端示例覆盖：

| Demo | 功能 |
|------|------|
| Demo 1 | OpenAI 协议透传 |
| Demo 2 | extra_body 透传（thinking 参数不丢失） |
| Demo 3 | Anthropic 协议透传 |
| Demo 4 | Gemini 协议透传 |
| Demo 5 | SSE 流式透传 |
| Demo 6 | 兼容性声明端点 |
| Demo 7 | Metrics 端点 |

### 方式三：查询兼容性声明

```bash
curl http://localhost:8080/.well-known/agra-compatibility
```

```json
{
  "gateway": "AGRA Reference Implementation v0.1",
  "compatibility": {
    "openai": {"level": "PC-5", "name": "Protocol Native"},
    "anthropic": {"level": "PC-5", "name": "Protocol Native"},
    "gemini": {"level": "PC-5", "name": "Protocol Native"}
  },
  "pattern": "Transparent Gateway (TLG)"
}
```

---

## 给 AI 的结构化清单

```
AGRA Reference Implementation Feature Map

1. passthrough_request:
   file: agra/gateway.py
   method: _forward
   key_line: content=ctx.body_bytes
   test: test_arch_004_no_silent_param_drop

2. passthrough_response:
   file: agra/gateway.py
   method: _forward
   key_line: body=resp.content
   test: test_arch_003_default_passthrough

3. streaming_passthrough:
   file: agra/gateway.py
   method: _forward_stream
   key_line: yield chunk
   test: test_pc_3_streaming_compatible

4. protocol_detection:
   file: agra/protocol/handlers.py
   class: ProtocolDetector
   handlers: [OpenAI, Anthropic, Gemini]
   test: test_pc_1_endpoint_compatible

5. unified_auth:
   file: agra/governance/auth.py
   class: AuthMiddleware
   supports: [Bearer, x-api-key, x-goog-api-key]
   test: test_gov_002_api_key_auth

6. unified_rate_limit:
   file: agra/governance/rate_limit.py
   class: RateLimitMiddleware
   dimensions: [user, org, model, provider, ip]
   algorithm: TokenBucket
   test: test_gov_003_rate_limit

7. unified_usage:
   file: agra/usage/extractor.py
   extractors: [OpenAI, Anthropic, Gemini]
   output: Usage(input_tokens, output_tokens, total_tokens, cached_tokens, cost_usd)
   test: test_obs_005_usage_extraction

8. unified_logging:
   file: agra/observability/observability.py
   class: ObservabilityMiddleware
   output: structured JSON
   endpoint: GET /metrics (Prometheus)
   test: test_obs_001_structured_logging
```
