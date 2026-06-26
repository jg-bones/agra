# AGRA-0001: Architecture

| Field | Value |
|-------|-------|
| **Document ID** | AGRA-0001 |
| **Title** | Architecture |
| **Status** | Draft |
| **Version** | 0.1 |
| **Last Updated** | 2026-06-26 |
| **Type** | Specification |
| **Depends On** | AGRA-0000 |

---

## 1. Summary

本规范定义 AGRA 的四条设计原则和五层架构模型。五层模型将 AI Gateway 的职责划分为 Client Layer、Transport Layer、Protocol Layer、Governance Layer 和 Observability Layer，其中 **Protocol Layer 与 Governance Layer 的解耦** 是 AGRA 区别于传统 AI Gateway 的核心架构决策。

## 2. Design Principles

### 2.1 Principle 1: Protocol Preservation

> **协议是能力，不是兼容负担。**

AI Gateway 应尽可能保留协议原生能力，而不是把所有协议转换成另一种协议。

**含义：**

- Gateway 的默认行为是透传（pass-through），而非转换
- 协议特有字段（`thinking`、`cache_control`、`grounding`）应原样保留
- 协议转换是可选的 Reference Pattern，而非默认行为

**反例：** Gateway 维护参数白名单，未识别字段被静默丢弃。

### 2.2 Principle 2: Governance over Translation

> **网关应该统一治理，而不是统一协议。**

**统一的是治理能力：** Authentication、Authorization、Routing、Rate Limiting、Billing、Observability。

**而不是协议细节：** `thinking`、`cache_control`、`grounding`、MCP。

**含义：** 治理层的升级不应需要修改协议适配代码；协议演进不应影响治理逻辑。

### 2.3 Principle 3: Transport Transparency

> Transport 应尽可能保持透明。

**默认原则：**

- 不修改 Request Body
- 不修改 Response Body
- 保持 Streaming 透明（逐帧转发，不缓冲）
- 最小化 Header 修改

只有在明确需要时（认证、追踪、路由）才进行有限修改。

### 2.4 Principle 4: Extensible by Design

> 所有能力都应通过扩展点实现，而不是修改核心。

**扩展点：** Middleware、Plugin、Policy、Router、Usage Extractor。

核心引擎本身保持简洁稳定，所有功能通过扩展实现。

## 3. Five-Layer Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│   OpenAI SDK · Anthropic SDK · Gemini SDK · REST Client        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       TRANSPORT LAYER                           │
│   HTTP/2 · gRPC · WebSocket · SSE                              │
│   Connection Pool · TLS · Request/Response Passthrough          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       PROTOCOL LAYER                            │
│   Protocol Detection · Header Routing · Capability Mapping      │
│   ┌──────────┐  ┌────────────┐  ┌─────────┐                   │
│   │  OpenAI  │  │ Anthropic  │  │  Gemini │  ...               │
│   │ Protocol │  │  Protocol  │  │ Protocol│                    │
│   │ Handler  │  │  Handler   │  │ Handler │                    │
│   └──────────┘  └────────────┘  └─────────┘                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      GOVERNANCE LAYER                           │
│   Auth · Rate Limit · Routing · Billing · Audit                │
│   Middleware Chain · Policy Engine · Plugin System             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    OBSERVABILITY LAYER                          │
│   Logging · Metrics · Tracing · Alerting · Reporting           │
│   (Cross-cutting — spans all layers)                           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 Client Layer

Gateway 的外部接口。客户端使用任何 Provider 的官方 SDK，将 `base_url` 指向 Gateway 即可。

**设计约束：** 客户端不需要引入新的 SDK 或中间件。

### 3.2 Transport Layer

负责网络传输，核心职责：

- 接收客户端请求，管理 HTTP/2、gRPC、WebSocket 连接
- 管理 SSE 流式传输
- 保持请求体和响应体的完整性
- 在 Header 层注入追踪信息（`X-Request-ID`、`X-Trace-ID`）
- 管理连接池和后端连接复用

**关键约束：** Transport Layer 不解析请求体内容，只关心 HTTP 层元数据。

### 3.3 Protocol Layer

负责协议识别和路由，核心职责：

- 根据请求路径和 Header 自动检测协议类型
  - `POST /v1/chat/completions` → OpenAI Protocol
  - `POST /v1/messages` → Anthropic Protocol
  - `POST /v1beta/models/{model}:generateContent` → Gemini Protocol
- 将请求路由到对应的 Protocol Handler
- 维护协议兼容性元数据（参见 AGRA-0003）

**关键约束：** Protocol Handler 的默认行为是透传，而非转换。每个 Handler 知道如何处理特定协议的请求，但不主动修改请求体。

### 3.4 Governance Layer

统一治理能力的实现层。所有跨协议的管理功能在此实现：

- **Authentication**：验证客户端身份，注入 Provider API Key
- **Authorization**：基于角色或组织的细粒度权限控制
- **Rate Limiting**：多维度限流
- **Routing**：根据策略选择目标 Provider
- **Billing**：统一计费和成本归属
- **Audit**：完整的操作审计日志

通过 Middleware Chain 实现。每个 Middleware 是独立处理单元。

### 3.5 Observability Layer

横切关注点，贯穿所有层：

- **Logging**：请求和响应的结构化日志
- **Metrics**：延迟、吞吐量、错误率、Token 用量
- **Tracing**：分布式追踪，从客户端到 Provider 的完整链路
- **Alerting**：异常检测和自动告警
- **Reporting**：成本报告、用量趋势、SLA 看板

## 4. Key Architectural Decision

> **Protocol Layer 和 Governance Layer 是解耦的。**

这是 AGRA 最重要的架构决策，也是区别于传统 AI Gateway 的根本设计点。

**含义：**

| 维度 | 传统架构 | AGRA |
|------|---------|------|
| 层间关系 | 治理逻辑嵌入协议适配代码 | 治理层与协议层独立 |
| 协议演进 | 影响治理逻辑 | 不影响治理逻辑 |
| 治理增强 | 需要修改协议适配 | 不需要修改协议适配 |
| 测试 | 耦合测试 | 独立测试 |
| 可替换性 | 难以单独替换 | 可独立替换任一层 |

## 5. Request Lifecycle

```
Client Request
    │
    ▼
[Transport Layer] ── 接收 HTTP 请求，提取 Header 元数据
    │
    ▼
[Protocol Layer] ── 识别协议类型，路由到 Protocol Handler
    │
    ▼
[Governance Layer] ── Middleware Chain 顺序执行：
    │                   ├── Auth Middleware（认证）
    │                   ├── Rate Limit Middleware（限流）
    │                   ├── Router Middleware（路由选择 Provider）
    │                   └── Billing Middleware（计费预检）
    │
    ▼
[Transport Layer] ── 将请求转发到选定的 Provider
    │
    ▼
Provider Response
    │
    ▼
[Observability Layer] ── 记录日志、指标、追踪
    │
    ▼
[Governance Layer] ── Middleware Chain 逆序执行：
    │                   ├── Usage Extract Middleware（用量提取）
    │                   ├── Billing Middleware（计费记录）
    │                   └── Audit Middleware（审计记录）
    │
    ▼
[Transport Layer] ── 将响应返回给客户端
```

## 6. Conformance Requirements

符合 AGRA 架构的 Gateway 实现必须满足：

| 编号 | 要求 | 对应原则 |
|------|------|---------|
| ARCH-001 | 必须实现五层模型或其等价物 | §3 |
| ARCH-002 | Protocol Layer 与 Governance Layer 必须解耦 | §4 |
| ARCH-003 | 默认行为必须是透传，而非转换 | Principle 1 |
| ARCH-004 | 不得静默丢弃未识别的请求参数 | Principle 1 |
| ARCH-005 | 治理能力必须通过 Middleware Chain 实现 | Principle 4 |
| ARCH-006 | 必须支持至少一种可观测性支柱（Logging/Metrics/Tracing） | §3.5 |

## 7. References

- AGRA-0000: Vision
- AGRA-0002: Terminology
- AGRA-0003: Compatibility Model
- AGRA-0004: Governance Model
- AGRA-0005: Observability
- AGRA-0006: Reference Patterns
