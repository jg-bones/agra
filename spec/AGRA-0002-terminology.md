# AGRA-0002: Terminology

| Field | Value |
|-------|-------|
| **Document ID** | AGRA-0002 |
| **Title** | Terminology |
| **Status** | Draft |
| **Version** | 0.1 |
| **Last Updated** | 2026-06-26 |
| **Type** | Specification |
| **Depends On** | AGRA-0000 |

---

## 1. Summary

本规范定义 AGRA 文档体系中使用的统一术语，确保跨文档、跨实现的语义一致性。

## 2. Core Terms

### 2.1 Architecture Terms

| 术语 | 英文 | 定义 |
|------|------|------|
| **AGRA** | AI Gateway Reference Architecture | AI 网关参考架构，本规范集的统称 |
| **AI Gateway** | AI Gateway | 代理、治理和观测 AI 模型 API 请求的系统 |
| **Provider** | Provider | 模型服务提供方，如 OpenAI、Anthropic、Google |
| **Client** | Client | 向 Gateway 发送请求的应用或 SDK |
| **Reference Architecture** | Reference Architecture | 可被引用和遵循的架构方法论，非特定实现 |

### 2.2 Protocol Terms

| 术语 | 英文 | 定义 |
|------|------|------|
| **Protocol** | Protocol | Provider 定义 API 的规范，包括端点、请求/响应格式、流式事件等 |
| **Protocol Preservation** | Protocol Preservation | AGRA 第一原则：保持协议原生能力，不将协议转换为另一种协议 |
| **Protocol Translation** | Protocol Translation | 将一种协议转换为另一种协议的架构模式（AGRA 参考模式之一） |
| **Protocol Handler** | Protocol Handler | Protocol Layer 中处理特定协议的组件 |
| **Protocol Native** | Protocol Native | 保留协议全部原生扩展能力的兼容等级（PC-5） |
| **Protocol is Product** | Protocol is Product | AGRA 核心论断：协议承载 Provider 产品能力，不可被完全抽象 |

### 2.3 Governance Terms

| 术语 | 英文 | 定义 |
|------|------|------|
| **Governance** | Governance | 跨协议的统一管理能力：认证、授权、路由、限流、计费、审计 |
| **Governance over Translation** | Governance over Translation | AGRA 第二原则：统一治理而非统一协议 |
| **Middleware** | Middleware | Governance Layer 中的请求/响应拦截器 |
| **Middleware Chain** | Middleware Chain | Middleware 的有序执行链 |
| **Policy** | Policy | 声明式规则，描述在什么条件下执行什么动作 |
| **Router** | Router | 根据策略选择目标 Provider 的组件 |

### 2.4 Transport Terms

| 术语 | 英文 | 定义 |
|------|------|------|
| **Transport Transparency** | Transport Transparency | AGRA 第三原则：不修改请求/响应体，保持流式传输透明 |
| **Passthrough** | Passthrough / Pass-through | Gateway 将请求体和响应体原样转发，不解析或修改 |
| **SSE** | Server-Sent Events | 服务器推送事件，AI API 流式传输的标准方式 |
| **TTFT** | Time to First Token | 从请求发出到收到第一个 Token 的时间 |

### 2.5 Compatibility Terms

| 术语 | 英文 | 定义 |
|------|------|------|
| **PC-N** | Protocol Compatibility Level N | 协议兼容性等级，N ∈ {0,1,2,3,4,5} |
| **PC-0** | HTTP Compatible | 支持 HTTP 与基本 REST 访问 |
| **PC-1** | Endpoint Compatible | 兼容 API 路径与请求方式 |
| **PC-2** | Schema Compatible | 请求/响应结构兼容 |
| **PC-3** | Streaming Compatible | 流式事件兼容 |
| **PC-4** | SDK Compatible | 官方 SDK 可直接使用 |
| **PC-5** | Protocol Native | 保留协议原生扩展能力 |
| **OpenAI Compatible** | OpenAI Compatible | 行业惯用语，指兼容 OpenAI API 格式（AGRA 建议用 PC-N 精确描述） |

### 2.6 Extension Terms

| 术语 | 英文 | 定义 |
|------|------|------|
| **Extensible by Design** | Extensible by Design | AGRA 第四原则：所有能力通过扩展点实现 |
| **Plugin** | Plugin | 独立的功能模块，可注册 Middleware 和路由 |
| **Usage Extractor** | Usage Extractor | 从请求/响应中提取 Token 用量的组件 |

### 2.7 Observability Terms

| 术语 | 英文 | 定义 |
|------|------|------|
| **Span** | Span | 分布式追踪中的一个操作单元 |
| **Trace** | Trace | 从客户端到 Provider 的完整请求链路 |
| **ADR** | Architecture Decision Record | 架构决策记录 |
| **Semantic Conventions** | Semantic Conventions | 可观测性领域的属性命名约定（如 OpenTelemetry GenAI Semantic Conventions） |

### 2.8 Pattern Terms

| 术语 | 英文 | 定义 |
|------|------|------|
| **Reference Pattern** | Reference Pattern | AGRA 定义的、可复用的架构模式 |
| **TLG** | Transparent Gateway | 透明网关，AGRA 的核心参考模式，PC-5 级别 |
| **Provider Adapter** | Provider Adapter | 传统 AI Gateway 中负责协议转换的组件，维护参数白名单 |

## 3. Naming Conventions

### 3.1 文档编号

- 规范文档：`AGRA-NNNN-title`（如 AGRA-0001-architecture）
- ADR：`ADR-NNN-title`（如 ADR-001-passthrough-as-default）

### 3.2 协议标识

| Provider | 协议标识 | 认证方式 |
|----------|---------|---------|
| OpenAI | `openai` | `Authorization: Bearer <key>` |
| Anthropic | `anthropic` | `x-api-key: <key>` + `anthropic-version` |
| Gemini | `gemini` | `x-goog-api-key: <key>` 或 OAuth 2.0 |

### 3.3 兼容性声明格式

```
<Gateway/Provider Name> <version>
- <Protocol> Compatibility: PC-<N> (<Level Name>)
```

示例：

```
MyGateway v2.3.1
- OpenAI Compatibility: PC-4 (SDK Compatible)
- Anthropic Compatibility: PC-2 (Schema Compatible)
- Gemini Compatibility: PC-1 (Endpoint Compatible)
```

## 4. References

- AGRA-0000: Vision
- AGRA-0001: Architecture
- AGRA-0003: Compatibility Model
