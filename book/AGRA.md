# AI Gateway Reference Architecture (AGRA)

> **A Reference Architecture for Building Multi-Protocol AI Gateways**
>
> 一套构建多协议、Provider 无关 AI Gateway 的参考架构

| Field | Value |
|-------|-------|
| **Document ID** | AGRA-BOOK |
| **Version** | 0.1-draft |
| **Status** | Draft |
| **Last Updated** | 2026-06-26 |

---

## Preface

AGRA（AI Gateway Reference Architecture）试图回答一个行业中的根本问题：**在协议多元化的时代，AI Gateway 应该如何设计？**

过去三年，AI Gateway 领域经历了一次范式转移。2023 年，行业共识是「将所有协议统一为 OpenAI 格式」。2025 年，这个共识开始瓦解——Anthropic 的 Thinking、Gemini 的 Grounding、OpenAI 的 Responses API 让协议本身成为产品能力的一部分。继续用「统一协议」的思路构建 Gateway，意味着永远追不上协议演进的速度。

AGRA 提出另一个方向：**不统一协议，统一治理。** 在保持协议原生能力的前提下，实现认证、路由、限流、计费和可观测性的统一。

本书不是某一个 Gateway 项目的使用文档，而是一套可被引用的参考架构方法论。它定义设计原则、架构边界、兼容性标准和参考模式，而非某一个具体实现。

---

# Part I: Foundation

## Chapter 1: AI Gateway Crisis

### 1.1 引言

过去两年，大语言模型（Large Language Model, LLM）的 API 生态发生了根本性的变化。

2023 年以前，绝大多数 AI 应用只需要调用单一 Provider，例如 OpenAI 的 Chat Completions API。API 网关（Gateway）的职责也相对简单：统一认证、记录日志、控制流量，并将请求转发给上游模型。

随着越来越多模型厂商进入市场，这种单一 Provider 的模式逐渐演变为多 Provider 接入。为了降低应用开发成本，行业开始采用一种新的架构模式：**Protocol Translation（协议转换）**。

其基本思想是：

> 将所有 Provider 的 API 转换为一种统一协议，通常是 OpenAI Chat Completions API。

在这一阶段，大量 AI Gateway 项目采用了相同的设计思路：

```
Application
    │
    ▼
OpenAI Request
    │
    ▼
Gateway
    │
    ▼
Provider Adapter
    │
    ├──→ Anthropic    (转换为 Anthropic Messages 格式)
    ├──→ Gemini       (转换为 Gemini generateContent 格式)
    ├──→ DeepSeek     (保持 OpenAI 格式)
    └──→ Azure OpenAI (保持 OpenAI 格式)
```

这种架构极大降低了多模型接入成本，也推动了 "OpenAI Compatible" 成为事实上的行业标准。

然而，随着模型能力快速演进，这种架构开始暴露越来越多的问题。

### 1.2 协议开始分化

今天的大模型 API 已不再只是「聊天接口」。

不同 Provider 已经开始围绕自身能力设计协议，而不是围绕 OpenAI Chat Completions 兼容。例如：

**OpenAI** 推出了 Responses API，将文本、图片、音频、工具调用、多轮推理统一到新的响应模型中。Responses API 不是 Chat Completions 的扩展，而是一个全新的协议层，支持状态管理、内置工具和结构化输出。

**Anthropic** 在 Messages API 中引入了 Thinking（扩展推理）、Prompt Cache（提示缓存）、Computer Use（计算机操作）、Citations（引用）等原生能力。这些能力通过协议字段表达，不是简单的参数增加。

**Gemini** 则围绕 Grounding（Google 搜索增强）、Live API（实时双向通信）、Code Execution（代码执行）建立了不同于 OpenAI 的协议体系。Gemini 的 `contents`/`parts` 结构与 OpenAI 的 `messages` 结构在语义上不可通约。

这些能力并不是简单增加几个 JSON 字段，而是：

> **协议本身正在演进。**

协议已经开始承担 Provider 产品能力的表达职责。这意味着：

> **Protocol is Product.**
>
> 协议不再只是网络通信格式，而是模型能力的一部分。

### 1.3 Provider Adapter 的困境

大多数现有 AI Gateway 都采用 Provider Adapter 架构。其生命周期通常如下：

```
HTTP Request
    │
    ▼
Gateway 接收请求
    │
    ▼
Parse Request (解析为内部统一格式)
    │
    ▼
Normalize Parameters (参数标准化)
    │
    ▼
Provider Adapter (适配器转换)
    │
    ▼
Provider Request (发送到上游)
```

Provider Adapter 的职责通常包括：

- **参数映射**：将 Provider 特定参数映射到统一格式
- **参数过滤**：根据白名单过滤未知参数
- **默认值填充**：补全缺失的默认参数
- **Provider 特殊参数转换**：处理 Provider 特有的参数语义
- **Streaming 转换**：统一流式事件格式
- **Usage 转换**：统一 Token 用量计算
- **Error 转换**：统一错误码和错误信息

这种设计在 Provider 数量较少、协议变化缓慢时非常有效。

但是随着协议持续演进，Gateway 必须不断更新 Adapter 才能支持新的 Provider 能力。每一次新增协议字段，都意味着：

1. SDK 更新
2. Gateway 更新
3. Provider Adapter 更新
4. 参数白名单更新
5. Streaming 更新
6. Usage 更新
7. 测试更新

**协议越快演进，Gateway 的维护成本越高。**

这不是某一个项目的工程质量问题，而是 **Protocol Translation 架构的结构性缺陷**。

### 1.4 真实案例：Thinking 参数丢失

下面来看一个真实的问题。

客户端使用 OpenAI Python SDK，通过 Gateway 访问支持 `thinking` 参数的 Provider：

```python
from openai import OpenAI

client = OpenAI(base_url="https://my-gateway.example.com/v1")

response = client.chat.completions.create(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": "9.11 和 9.8 哪个更大？"}],
    extra_body={
        "thinking": {
            "type": "enabled",
            "budget_tokens": 4000
        }
    }
)
```

OpenAI SDK 会将 `extra_body` 展开到请求体顶层，因此实际发送的 HTTP Body 为：

```json
{
    "model": "claude-sonnet-4-5",
    "messages": [
        {"role": "user", "content": "9.11 和 9.8 哪个更大？"}
    ],
    "thinking": {
        "type": "enabled",
        "budget_tokens": 4000
    }
}
```

如果该请求直接发送到支持 `thinking` 的 Provider，参数能够正常生效，模型会先进行内部推理再回答。

然而，当请求经过某些采用 Provider Adapter 的 Gateway 时，Gateway 会根据自身维护的参数白名单重新构造请求对象。如果当前 Gateway 尚未认识 `thinking` 参数，那么该字段会在请求生命周期中被静默过滤。

最终发送给上游 Provider 的请求变成：

```json
{
    "model": "claude-sonnet-4-5",
    "messages": [
        {"role": "user", "content": "9.11 和 9.8 哪个更大？"}
    ]
}
```

`thinking` 参数消失了。

整个过程中：

- HTTP 没有问题；
- SDK 没有问题；
- Provider 也支持该能力；

**问题发生在 Gateway 内部的协议转换阶段。**

更严重的是，这个问题是 **静默的**。客户端不会收到任何错误，模型会正常返回回答——只是没有进行 Thinking 推理。用户可能永远不会发现 Gateway 偷偷吃掉了这个能力。

这类问题并非某一个项目的缺陷，而是 **Protocol Translation 架构** 在面对快速演进协议时的普遍挑战。只要 Gateway 维护参数白名单，就必然存在白名单未覆盖的新参数被丢弃的风险。

### 1.5 危机的根源

过去几年，AI Gateway 一直围绕一个目标构建：

> **统一协议。**

但今天我们认为，这个目标值得重新审视。

协议越来越多样化，且越来越承载 Provider 的独特能力。如果强行将所有协议压缩到同一个抽象层，Gateway 将不断面临以下矛盾：

1. **新协议能力出现，需要等待 Gateway 适配**——Provider 发布新能力到 Gateway 支持之间存在时间差
2. **不同 Provider 的语义无法完全映射**——Anthropic 的 `system`（数组，支持 `cache_control`）和 OpenAI 的 `system`（字符串）本质不同
3. **协议转换逻辑越来越复杂**——随着 Provider 增多，Adapter 数量指数增长
4. **网关升级速度难以跟上模型能力演进速度**——Provider 每周更新，Gateway 季度发版

问题并不是 Provider 太多，而是：

> **协议已经成为产品能力的一部分，而不是可以被完全抽象掉的细节。**

因此，AGRA 提出一个新的设计方向：

> **AI Gateway 应优先保持协议原生能力（Protocol Preservation），统一治理能力（Governance），而不是统一协议本身。**

这一观点构成了 AGRA 的核心设计哲学，也是后续章节提出参考架构的理论基础。

### Chapter 1 ADR

**ADR-001: 选择透传作为默认行为**

- **状态：** Accepted
- **背景：** 传统 AI Gateway 将协议转换作为默认行为。AGRA 面临关键决策：默认行为应该是转换还是透传。
- **决策：** 采用透传作为默认行为。
- **理由：** 协议分化不可逆；透传保证 PC-5 兼容性；透传性能更好；转换可作为可选模式。
- **后果：** Protocol Handler 默认实现更简单；新增 Provider 成本降低；转换模式需显式配置。

### Chapter 1 Summary

本章分析了 AI Gateway 领域面临的结构性危机。Protocol Translation 架构在协议缓慢演进时有效，但在协议已成为产品能力一部分的今天，它导致了参数丢失、能力退化和维护成本失控。AGRA 提出从「统一协议」转向「保持协议、统一治理」的新方向。

---

## Chapter 2: Design Principles

AGRA 凝练为四条核心原则。这四条原则相互关联，共同构成了 AGRA 不同于传统 AI Gateway 的设计哲学。

### 2.1 Principle 1: Protocol Preservation

> **协议是能力，不是兼容负担。**

AI Gateway 应尽可能保留协议原生能力，而不是把所有协议转换成另一种协议。

**含义：**

- Gateway 的默认行为是 **透传**（pass-through），而非转换
- 协议特有字段（`thinking`、`cache_control`、`grounding`）应原样保留，不被白名单过滤
- 当客户端和 Provider 使用相同协议时，Gateway 不应做任何协议层操作
- 协议转换是可选的 Reference Pattern（参见 AGRA-0006），而非默认行为

**反例：** Gateway 维护参数白名单，未识别字段被静默丢弃，导致 Thinking 等能力丢失（参见 §1.4）。

**与 `extra_body` 的关系：** OpenAI SDK 的 `extra_body` 机制是实现 Protocol Preservation 的重要工具。它允许客户端向请求体注入任意字段，这些字段应被 Gateway 原样透传给 Provider。AGRA 要求所有符合 PC-5 的 Gateway 必须保护 `extra_body` 机制。

### 2.2 Principle 2: Governance over Translation

> **网关应该统一治理，而不是统一协议。**

这是 AGRA 区别于现有 AI Gateway 的根本设计选择。

**统一的是治理能力：**

- Authentication（认证）
- Authorization（授权）
- Routing（路由）
- Rate Limiting（限流）
- Billing（计费）
- Observability（可观测性）

**而不是协议细节：**

- `thinking` 参数
- `cache_control` 语义
- `grounding` 配置
- MCP 协议交互

**含义：** 治理层（Governance Layer）和协议层（Protocol Layer）是解耦的。

- 治理能力的提升不应需要修改协议适配代码
- 协议演进不应影响治理逻辑
- 新增一个 Provider 只需要关注协议适配，不需要重写治理逻辑

### 2.3 Principle 3: Transport Transparency

> Transport 应尽可能保持透明。

**默认原则：**

- **不修改 Request Body**：客户端发送的请求体应原样到达 Provider
- **不修改 Response Body**：Provider 返回的响应体应原样返回给客户端
- **保持 Streaming 透明**：SSE 流应逐帧透传，Gateway 仅做必要的转发和观测
- **最小化 Header 修改**：只在明确需要时（认证 Token 注入、Request ID 追踪）才修改 HTTP Header

只有在明确需要时（例如认证、追踪、路由）才进行有限修改。

**Streaming 透明性详解：**

SSE（Server-Sent Events）是 AI API 中最常用的流式传输方式。AGRA 对 SSE 的透明传输要求：

1. **逐帧转发**：Provider 发出的每个 SSE 事件原样转发
2. **不缓冲**：不将多个事件合并后发送（会增加首字延迟）
3. **不修改事件内容**：即使 Gateway 不理解某个事件类型，也保持原样转发
4. **正确处理终止标记**：`data: [DONE]` 等流结束标记正确转发

### 2.4 Principle 4: Extensible by Design

> 所有能力都应通过扩展点实现，而不是修改核心。

AGRA 将 Gateway 的所有增值能力设计为可插拔的扩展点：

| 扩展点 | 职责 | 示例 |
|--------|------|------|
| **Middleware** | 请求/响应生命周期中的拦截器 | 日志、认证、限流 |
| **Plugin** | 独立的功能模块 | 缓存、内容审核 |
| **Policy** | 声明式规则引擎 | 限流策略、路由规则 |
| **Router** | 可插拔的路由策略 | 轮询、权重、延迟优先 |
| **Usage Extractor** | 可扩展的用量提取器 | 不同 Provider 的 Token 计数 |

核心引擎本身保持简洁和稳定，所有功能通过扩展实现。这意味着：

- 新增功能不需要修改核心代码
- 功能可以独立开发和测试
- 功能可以按需启用或禁用
- 第三方可以开发自己的扩展

### Chapter 2 ADR

**ADR-002: Protocol Layer 与 Governance Layer 解耦**

- **状态：** Accepted
- **背景：** 传统架构中，治理逻辑和协议逻辑耦合在一起。
- **决策：** 将两层设计为独立的、解耦的层。
- **理由：** 协议演进不影响治理；治理增强不影响协议；独立测试和部署；可独立替换。
- **后果：** 增加一层抽象；需明确定义层间接口。

### Chapter 2 Summary

AGRA 的四条设计原则——Protocol Preservation、Governance over Translation、Transport Transparency、Extensible by Design——共同构成了一个连贯的设计哲学：Gateway 应该是协议的守护者和治理的统一者，而不是协议的翻译者。这四条原则推导出下一章的五层架构模型。

---

## Chapter 3: Five-Layer Architecture

### 3.1 架构总览

这是 AGRA 最核心的架构图。五层模型将 Gateway 的职责清晰地分层，每层有明确的职责边界。

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│   OpenAI SDK · Anthropic SDK · Gemini SDK · REST Client        │
│   (客户端不需要引入新的 SDK，仅需修改 base_url)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       TRANSPORT LAYER                           │
│   HTTP/2 · gRPC · WebSocket · SSE                              │
│   Connection Pool · TLS · Request/Response Passthrough          │
│   (不解析请求体，只处理 HTTP 层元数据)                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       PROTOCOL LAYER                            │
│   Protocol Detection · Header Routing · Capability Mapping      │
│   ┌──────────┐  ┌────────────┐  ┌─────────┐                   │
│   │  OpenAI  │  │ Anthropic  │  │  Gemini │  ...               │
│   │ Handler  │  │  Handler   │  │ Handler │                    │
│   └──────────┘  └────────────┘  └─────────┘                   │
│   (默认行为：透传。转换是可选模式。)                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      GOVERNANCE LAYER                           │
│   Auth · Rate Limit · Routing · Billing · Audit                │
│   Middleware Chain · Policy Engine · Plugin System             │
│   (跨协议统一治理，与协议层解耦)                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    OBSERVABILITY LAYER                          │
│   Logging · Metrics · Tracing · Alerting · Reporting           │
│   (横切关注点，贯穿所有层)                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 各层详解

#### Client Layer

Gateway 的外部接口。客户端使用任何 Provider 的官方 SDK 来访问 Gateway。

**设计约束：** 客户端不需要引入新的 SDK 或中间件。开发者继续使用他们熟悉的 OpenAI SDK、Anthropic SDK 或 Gemini SDK，只需将 `base_url` 指向 Gateway。

#### Transport Layer

负责网络传输，核心职责：

- 接收客户端请求，建立 HTTP/2、gRPC 或 WebSocket 连接
- 管理 SSE 流式传输
- 保持请求体和响应体的完整性
- 在 Header 层注入追踪信息（`X-Request-ID`、`X-Trace-ID`）
- 管理连接池和后端连接复用

**关键约束：** Transport Layer 不解析请求体内容。它只关心 HTTP 层的元数据（Method、Path、Headers）。请求体以字节流形式透传。

#### Protocol Layer

负责协议识别和路由。核心职责：

- 根据请求路径和 Header 自动检测协议类型：

| 请求路径 | 协议 |
|---------|------|
| `POST /v1/chat/completions` | OpenAI |
| `POST /v1/messages` | Anthropic |
| `POST /v1beta/models/{model}:generateContent` | Gemini |

- 将请求路由到对应的 Protocol Handler
- 维护协议兼容性元数据（参见 AGRA-0003）

**关键约束：** Protocol Handler 的默认行为是 **透传**，而非转换。每个 Handler 知道如何处理特定协议的请求，但不主动修改请求体。

#### Governance Layer

这是 AGRA 统一治理能力的实现层。所有跨协议的管理功能都在这里实现：

- **Authentication**：验证客户端身份，注入 Provider API Key
- **Authorization**：基于角色的细粒度权限控制
- **Rate Limiting**：多维度限流（用户级、组织级、模型级、Provider 级）
- **Routing**：根据策略选择目标 Provider
- **Billing**：统一计费和成本归属
- **Audit**：完整的操作审计日志

通过 Middleware Chain 实现。每个 Middleware 是独立处理单元，可以在请求前、请求后或两者都执行逻辑。

#### Observability Layer

贯穿所有层的横切关注点：

- **Logging**：请求和响应的结构化日志
- **Metrics**：延迟、吞吐量、错误率、Token 用量
- **Tracing**：分布式追踪，从客户端到 Provider 的完整链路
- **Alerting**：异常检测和自动告警
- **Reporting**：成本报告、用量趋势、SLA 看板

### 3.3 关键设计思想

> **Protocol Layer 和 Governance Layer 是解耦的。**

这是 AGRA 最重要的架构决策。

| 维度 | 传统架构 | AGRA |
|------|---------|------|
| 层间关系 | 治理逻辑嵌入协议适配代码 | 治理层与协议层独立 |
| 协议演进 | 影响治理逻辑 | 不影响治理逻辑 |
| 治理增强 | 需要修改协议适配 | 不需要修改协议适配 |
| 测试 | 耦合测试 | 独立测试 |
| 可替换性 | 难以单独替换 | 可独立替换任一层 |

### 3.4 请求生命周期

```
Client Request
    │
    ▼
[Transport Layer] ── 接收 HTTP 请求，提取 Header 元数据
    │                   注入 X-Request-ID, X-Trace-ID
    ▼
[Protocol Layer] ── 识别协议类型（/v1/messages → anthropic）
    │                  路由到 Anthropic Protocol Handler
    ▼
[Governance Layer] ── Middleware Chain 顺序执行：
    │                   ├── Auth Middleware (验证客户端，注入 Provider Key)
    │                   ├── Rate Limit Middleware (检查限流)
    │                   ├── Router Middleware (选择目标 Provider)
    │                   └── Billing Middleware (计费预检)
    ▼
[Transport Layer] ── 将请求转发到选定的 Provider
    │                   (请求体原样透传)
    ▼
Provider Response
    │
    ▼
[Observability Layer] ── 记录日志、指标、追踪 Span
    │
    ▼
[Governance Layer] ── Middleware Chain 逆序执行：
    │                   ├── Usage Extract (提取 Token 用量)
    │                   ├── Billing (记录计费)
    │                   └── Audit (审计记录)
    ▼
[Transport Layer] ── 将响应返回给客户端
                       (响应体原样透传)
```

### Chapter 3 Summary

五层模型将 AI Gateway 的职责清晰分层。Protocol Layer 与 Governance Layer 的解耦是核心架构决策，使得协议演进和治理增强可以独立进行。Transport Layer 的不解析约束保证了传输透明性。Observability Layer 作为横切关注点贯穿所有层。

---

## Chapter 4: Compatibility Levels

### 4.1 问题的本质

目前行业里说「OpenAI Compatible」，实际上缺乏统一定义。

- 有的 Gateway 只兼容了 `/v1/chat/completions` 这一个端点（Endpoint Compatible）
- 有的兼容了请求/响应结构（Schema Compatible）
- 有的连 Streaming 事件格式都对齐了（Streaming Compatible）
- 有的可以让 OpenAI SDK 无缝替换 `base_url`（SDK Compatible）
- 但几乎没有 Gateway 能完整保留协议的原生扩展能力（Protocol Native）

这种模糊性导致开发者选型时无法准确评估兼容程度，也无法在 Gateway 之间做横向比较。

### 4.2 AGRA 兼容性分级模型

AGRA 提出一套 **六级兼容性分级模型**：

| 等级 | 名称 | 含义 |
|------|------|------|
| **PC-0** | HTTP Compatible | 支持 HTTP 与基本 REST 访问 |
| **PC-1** | Endpoint Compatible | 兼容 API 路径与请求方式 |
| **PC-2** | Schema Compatible | 请求/响应结构兼容 |
| **PC-3** | Streaming Compatible | 流式事件兼容 |
| **PC-4** | SDK Compatible | 官方 SDK 可直接使用 |
| **PC-5** | Protocol Native | 保留协议原生扩展能力 |

等级是 **累积的**：达到 PC-N 意味着同时满足 PC-0 到 PC-(N-1) 的全部要求。

### 4.3 各级详解

#### PC-0: HTTP Compatible

最低的兼容级别。Gateway 只需提供 HTTP/HTTPS 接口，接受 Web 请求并返回响应。不保证路径、参数或响应格式与任何特定 Provider 一致。

**适用场景：** 自建模型服务的简单代理。

#### PC-1: Endpoint Compatible

兼容特定 Provider 的 API 路径和方法。例如，Gateway 接受 `POST /v1/chat/completions` 请求，但可能不保证请求体或响应体结构与 OpenAI 完全一致。

**适用场景：** 简单的负载均衡代理，客户端需自行处理参数映射。

#### PC-2: Schema Compatible

请求体和响应体结构与目标 Provider 一致。但可能不支持 Streaming，不支持 `n > 1`，不支持 Function Calling 的完整语义。

**已知风险：** 部分参数（如 `thinking`、`cache_control`）可能被 Gateway 过滤。

**适用场景：** 基本的 Chat 场景，不需要流式响应。

#### PC-3: Streaming Compatible

在 PC-2 基础上，完整支持 SSE 流式响应，流事件格式与目标 Provider 一致。包括所有流事件类型和 Usage 信息。

**适用场景：** 需要流式响应的 Chat 和 Completion 场景。

#### PC-4: SDK Compatible

官方 SDK 可以直接使用，只需修改 `base_url`。所有标准 API Endpoint 兼容，认证方式兼容，Error 格式一致。

**适用场景：** 希望无缝替换 Provider Endpoint 的生产环境。

#### PC-5: Protocol Native

最高兼容等级。在 PC-4 基础上，保留协议的原生扩展能力：

- Provider 特有参数不被过滤（`thinking`、`cache_control`、`grounding`）
- 非标准响应字段保留
- 流式扩展事件保留
- 支持 Provider 特有的 API Endpoint
- `extra_body` 机制有效

**这是 AGRA 推荐的目标兼容等级，也是 TLG 模式的默认等级。**

**适用场景：** 需要完整利用 Provider 所有能力的生产环境。

### 4.4 兼容性声明

任何 Gateway 或 Provider 都可以声明自己的兼容等级：

```
MyGateway v2.3.1
- OpenAI Compatibility: PC-4 (SDK Compatible)
- Anthropic Compatibility: PC-2 (Schema Compatible)
- Gemini Compatibility: PC-1 (Endpoint Compatible)
```

这样，开发者可以准确了解 Gateway 对每个 Provider 的支持程度，而不是笼统地说「兼容 OpenAI」。

### Chapter 4 Summary

AGRA 的六级兼容性分级模型（PC-0 到 PC-5）为行业提供了精确描述 Gateway 兼容程度的工具。PC-5（Protocol Native）是 AGRA 推荐的目标等级，保证协议全部原生扩展能力不被丢弃。

---

# Part II: Architecture Deep Dive

## Chapter 5: Transport Layer

### 5.1 职责

Transport Layer 是 Gateway 的网络入口和出口，负责：

1. 接收客户端 HTTP/2 请求
2. 管理连接池
3. 处理 TLS
4. 转发请求到 Provider
5. 管理 SSE 流式传输
6. 返回响应给客户端

### 5.2 透明性原则

Transport Layer 的核心约束：**不解析请求体内容**。

请求体以字节流形式从客户端透传到 Provider，响应体以字节流形式从 Provider 透传到客户端。Transport Layer 只关心 HTTP 层元数据（Method、Path、Headers、Status Code）。

**例外情况（需显式配置）：**

| 修改类型 | 何时允许 | 如何修改 |
|---------|---------|---------|
| 注入 Request ID | 始终 | 添加 `X-Request-ID` Header |
| 注入 Trace ID | 开启 Tracing 时 | 添加 `X-Trace-ID` Header |
| 替换 API Key | 需要 Provider 认证时 | 修改 `Authorization` Header |
| 协议转换 | 使用 Translation Pattern 时 | 在 Protocol Layer 处理 |

### 5.3 SSE 流式传输

SSE（Server-Sent Events）是 AI API 流式传输的标准方式。AGRA 对 SSE 透传的要求：

1. **逐帧转发**：Provider 发出的每个 SSE 事件原样转发
2. **不缓冲**：不将多个事件合并后再发送
3. **不修改事件内容**：即使不理解某事件类型也保持原样
4. **正确处理终止标记**：`data: [DONE]` 正确转发

```
Provider SSE Stream          Gateway              Client
    │                           │                    │
    │── event: message_start ──→│── (透传) ────────→│
    │── event: content_delta ──→│── (透传) ────────→│
    │── event: content_delta ──→│── (透传) ────────→│
    │── event: message_delta ──→│── (透传) ────────→│
    │── data: [DONE] ──────────→│── (透传) ────────→│
```

### 5.4 连接管理

| 组件 | 说明 |
|------|------|
| 客户端连接池 | 管理客户端到 Gateway 的连接 |
| Provider 连接池 | 管理Gateway到各 Provider 的连接复用 |
| 超时配置 | 连接超时、读取超时、空闲超时 |
| 重试策略 | 对 Provider 错误的重试策略 |
| 熔断器 | Provider 连续错误时自动熔断 |

### Chapter 5 Summary

Transport Layer 是 Gateway 的网络基础设施，核心约束是不解析请求体。SSE 流式传输的逐帧透传是保证流式能力不被退化的关键。

---

## Chapter 6: Protocol Layer

### 6.1 职责

Protocol Layer 负责协议识别和路由：

1. 根据请求路径和 Header 检测协议类型
2. 将请求路由到对应的 Protocol Handler
3. 维护协议兼容性元数据

### 6.2 协议检测

```
请求路径                              → 协议
─────────────────────────────────────────────
POST /v1/chat/completions            → openai
POST /v1/responses                   → openai (Responses API)
POST /v1/messages                    → anthropic
POST /v1beta/models/*/generateContent → gemini
POST /v1beta/models/*/streamGenerateContent → gemini (streaming)
```

### 6.3 Protocol Handler

每个协议有对应的 Handler，但关键区别在于：**Handler 的默认行为是透传，而非转换。**

```
Protocol Handler 接口：

class ProtocolHandler:
    protocol: str  # openai / anthropic / gemini

    def detect(self, request: HTTPRequest) -> bool:
        """判断请求是否属于此协议"""
        pass

    def extract_metadata(self, request: HTTPRequest) -> ProtocolMetadata:
        """从请求中提取元数据（不解析请求体）"""
        # 提取 model, stream 等信息用于治理层
        pass

    def passthrough(self, request: HTTPRequest) -> ProviderRequest:
        """构造对 Provider 的请求（默认：透传）"""
        pass
```

### 6.4 元数据提取

Protocol Layer 需要从请求中提取治理层需要的元数据，但 **不通过解析完整请求体来实现**（保持 Transport Transparency）。

提取方式：

| 元数据 | 提取方式 | 说明 |
|--------|---------|------|
| 协议类型 | 请求路径 | 从 URL Path 推断 |
| 模型名称 | 请求体浅层解析 | 仅读取顶层 `model` 字段 |
| 是否流式 | 请求体浅层解析 | 仅读取顶层 `stream` 字段 |
| 客户端认证 | HTTP Header | `Authorization` 或 `x-api-key` |

> **注意：** 浅层解析（只读取顶层特定字段）与完整解析不同。Gateway 只提取治理必需的少量字段，不解析完整请求体结构。

### Chapter 6 Summary

Protocol Layer 负责协议识别和路由，默认行为是透传。通过浅层解析提取治理必需的元数据，保持传输透明性。

---

## Chapter 7: Governance Layer

### 7.1 Middleware Chain

治理层通过 Middleware Chain 模式实现：

```
Request → [Auth] → [Rate Limit] → [Router] → [Billing] → Provider
                                                        │
Response ← [Audit] ← [Billing] ← [Usage Extract] ←──────┘
```

每个 Middleware 是独立的，可配置跳过，可按路由差异化配置。

### 7.2 认证

```
Client API Key (面向用户) → Gateway (Auth Middleware) → Provider API Key (面向上游)
```

支持的认证方式：API Key、JWT、OAuth 2.0、mTLS。

### 7.3 路由策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| Round Robin | 轮询 | 均衡加载 |
| Weighted | 按权重 | 部分 Provider 容量大 |
| Latency-Aware | 优先低延迟 | 对响应时间敏感 |
| Cost-Aware | 优先低成本 | 成本控制 |
| Fallback | 主不可用切换备用 | 高可用 |
| Capability-Aware | 根据请求特性选择 | Thinking/Grounding 路由 |

### 7.4 限流

多维度限流：

| 维度 | 时间窗口 | 算法 |
|------|---------|------|
| User | per minute | Token Bucket |
| Organization | per day | Sliding Window |
| Model | per minute | Leaky Bucket |
| Provider | per minute | Fixed Window |
| IP | per second | Token Bucket |

### 7.5 计费

| 维度 | 说明 |
|------|------|
| 按 Token | input_tokens + output_tokens |
| 按模型 | 不同模型差异化定价 |
| 按请求 | 固定费用 per request |

### Chapter 7 Summary

Governance Layer 通过 Middleware Chain 实现统一治理，包含认证、授权、路由、限流、计费和审计。与 Protocol Layer 完全解耦，治理逻辑不依赖协议细节。

---

## Chapter 8: Observability Layer

### 8.1 三根支柱

```
┌──────────────────────────────────────────────────────┐
│    LOGGING    │     METRICS      │     TRACING      │
│  Request/     │  Throughput      │  Distributed     │
│  Response     │  Latency         │  Trace Context   │
│  Audit        │  Error Rate      │  Span Hierarchy  │
└───────────────┴──────────────────┴──────────────────┘
```

### 8.2 核心指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `gateway_requests_total` | Counter | 总请求数 |
| `gateway_request_duration_ms` | Histogram | 请求总延迟 |
| `gateway_ttft_ms` | Histogram | Time to First Token |
| `gateway_errors_total` | Counter | 错误总数 |
| `gateway_tokens_total` | Counter | Token 总量 |
| `gateway_cost_usd_total` | Counter | 总成本 |

### 8.3 分布式追踪

采用 W3C Trace Context 标准：

```
Span: gateway.request (root)
├── Span: gateway.auth
├── Span: gateway.rate_limit
├── Span: gateway.route
├── Span: gateway.provider_call
│   ├── Event: request_sent
│   ├── Event: first_token (streaming)
│   └── Event: response_received
├── Span: gateway.usage_extract
└── Span: gateway.billing
```

### Chapter 8 Summary

Observability Layer 提供三根支柱：结构化日志、Prometheus 指标和 W3C 分布式追踪。作为横切关注点贯穿所有层，数据采集不修改请求/响应体。

---

## Chapter 9: Extension System

### 9.1 四个扩展点

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  MIDDLEWARE │  │   PLUGIN    │  │   POLICY    │  │   ROUTER    │
│  请求/响应   │  │  独立功能    │  │  声明式规则  │  │  路由策略    │
│  拦截器      │  │  模块        │  │  引擎       │  │  实现        │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### 9.2 Middleware 接口

```python
class Middleware:
    async def on_request(self, context: RequestContext) -> RequestContext: ...
    async def on_response(self, context, response: Response) -> Response: ...
    async def on_stream_event(self, context, event: StreamEvent) -> StreamEvent: ...
    async def on_error(self, context, error: Exception) -> None: ...
```

### 9.3 Policy 声明式规则

```yaml
policies:
  - name: "high-cost-model-rate-limit"
    match:
      model: ["gpt-5", "claude-opus-5"]
    action:
      rate_limit:
        requests_per_minute: 10
```

### Chapter 9 Summary

AGRA 通过 Middleware、Plugin、Policy、Router 四个扩展点实现功能扩展。核心引擎保持稳定，所有能力通过扩展实现。

---

# Part III: Reference Patterns

## Chapter 10: Transparent Gateway (TLG)

### 10.1 模式描述

```
Client SDK → Gateway → Provider
              │
              ├── Governance Layer (认证、限流、路由、计费)
              └── Observability Layer (日志、指标、追踪)
              
              [不修改请求体和响应体，原样透传]
```

TLG 是 AGRA 的核心参考模式，完整体现 Protocol Preservation 原则。

### 10.2 兼容性等级

**PC-5 (Protocol Native)** — 保证协议全部原生扩展能力。

### 10.3 适用场景

- 客户端和 Provider 使用相同协议
- 需要统一治理但不想牺牲协议原生能力
- 对透明性和低延迟有高要求

### 10.4 限制

客户端必须使用与 Provider 匹配的协议。

---

## Chapter 11: Protocol Translation Gateway

### 11.1 模式描述

```
Client (OpenAI SDK) → Gateway → Provider (Anthropic)
                        │
                        ├── Protocol Layer (协议翻译)
                        └── Governance Layer (治理)
```

### 11.2 关键约束

> **转换规则必须显式声明，不得静默丢弃字段。**

```yaml
translation:
  source: openai
  target: anthropic
  field_mapping:
    - source: "messages"
      target: "messages"
  dropped_fields:
    - "frequency_penalty"  # 显式声明丢弃
  passthrough_fields:
    - "thinking"           # 原样透传
```

### 11.3 兼容性等级

PC-2 ~ PC-4，取决于转换完整度。

---

## Chapter 12: OpenAI-Compatible Gateway

### 12.1 模式描述

对外暴露标准 OpenAI API，内部适配各 Provider。这是目前行业最常见的模式。

### 12.2 风险

> **AGRA 认为风险最高的模式。**

1. 参数丢失：白名单过滤新参数
2. 能力退化：Provider 特有能力无法通过 OpenAI 格式表达
3. 维护成本：每新增能力需更新所有 Adapter
4. 语义失真：不同 Provider 参数语义不可完全映射

### 12.3 缓解措施

1. 改白名单为黑名单
2. 支持 `extra_body` 透传
3. 声明兼容等级
4. 提供逃逸通道（允许直接访问原生协议端点）

---

# Part IV: Protocol Analysis

## Chapter 13: OpenAI API Protocol

### 13.1 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/chat/completions` | POST | Chat Completions |
| `/v1/responses` | POST | Responses API（新一代） |
| `/v1/embeddings` | POST | 文本嵌入 |
| `/v1/models` | GET | 模型列表 |

### 13.2 协议特征

- JSON 请求/响应
- SSE 流式传输（`data: [DONE]` 终止）
- `Authorization: Bearer <key>` 认证
- **`extra_body` 支持非标准参数透传**（AGRA 友好特性）
- Responses API 统一文本、图片、音频、工具调用

### 13.3 关键字段

```json
{
  "model": "gpt-5",
  "messages": [{"role": "user", "content": "..."}],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": true,
  "stream_options": {"include_usage": true},
  "tools": [...],
  "tool_choice": "auto"
}
```

---

## Chapter 14: Anthropic Messages API

### 14.1 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/messages` | POST | Messages API |
| `/v1/messages/count_tokens` | POST | Token 计数 |

### 14.2 协议特征

- `x-api-key` Header 认证
- `anthropic-version` Header 指定 API 版本
- SSE 流式，事件类型丰富
- 扩展能力：Thinking、Prompt Cache、Computer Use、Citations

### 14.3 关键字段

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 4096,
  "thinking": {
    "type": "enabled",
    "budget_tokens": 4000
  },
  "system": [
    {"type": "text", "text": "You are helpful."},
    {"type": "text", "text": "Guideline...", "cache_control": {"type": "ephemeral"}}
  ]
}
```

> **重要：** Anthropic 的 `system` 是数组形式，每个元素可设置独立 `cache_control`。与 OpenAI 的 `system`（字符串）完全不同，强行转换会丢失功能。

---

## Chapter 15: Gemini API

### 15.1 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1beta/models/{model}:generateContent` | POST | 内容生成 |
| `/v1beta/models/{model}:streamGenerateContent` | POST | 流式生成 |

### 15.2 协议特征

- `x-goog-api-key` 或 OAuth 2.0 认证
- SSE 或 gRPC 流式
- 扩展能力：Grounding、Code Execution、Live API
- `contents`/`parts` 结构不同于 OpenAI 的 `messages`

### 15.3 关键字段

```json
{
  "contents": [{
    "role": "user",
    "parts": [{"text": "..."}]
  }],
  "generationConfig": {
    "temperature": 0.7,
    "maxOutputTokens": 4096
  },
  "tools": [{"googleSearch": {}}]
}
```

---

## Chapter 16: Protocol Comparison Matrix

| 能力 | OpenAI | Anthropic | Gemini |
|------|--------|-----------|--------|
| 文本对话 | ✓ | ✓ | ✓ |
| 流式响应 | SSE | SSE | SSE + gRPC |
| 工具调用 | Function Calling | Tool Use | Function Calling |
| 多模态 | 图片、音频 | 图片、PDF | 图片、视频、音频 |
| 推理/思考 | o-series（独立模型） | Thinking（参数控制） | Thinking（参数控制） |
| 缓存 | Prompt Caching（自动） | Prompt Cache（显式） | Context Caching |
| 搜索增强 | Responses API 内置 | 无原生支持 | Grounding |
| 代码执行 | Responses API 内置 | Computer Use | Code Execution |
| 实时通信 | Realtime API | 无 | Live API |
| 参数透传 | `extra_body` | 无（需 SDK 支持） | 无（需 SDK 支持） |
| system 格式 | 字符串 | 数组（支持 cache_control） | systemInstruction |
| 认证方式 | Bearer Token | x-api-key + version | x-goog-api-key |

### 对 AGRA 设计的启示

1. **`extra_body` 是关键能力**：AGRA 应优先支持并保护该机制
2. **认证方式不统一**：需独立的 Auth Middleware 抽象
3. **Streaming 事件格式不统一**：TLG 模式下不需要转换
4. **协议字段语义不可通约**：Anthropic 的 `system`（数组）和 OpenAI 的 `system`（字符串）本质不同，强行映射会丢失信息。这强化了 Protocol Preservation 原则。

---

# Part V: Implementation Analysis

## Chapter 17: LiteLLM Architecture Analysis

### 17.1 概述

LiteLLM 是目前最流行的开源 AI Gateway 之一，也是 Protocol Translation 架构的典型代表。

### 17.2 架构

```
Client → LiteLLM Proxy (FastAPI)
           ├── Router (路由层)
           ├── Proxy Server (代理层)
           └── LLM Translation (翻译层)
                 ├── OpenAI Adapter
                 ├── Anthropic Adapter
                 ├── Gemini Adapter
                 └── ... (100+ Provider Adapters)
```

### 17.3 核心流程

```
1. 接收请求 (FastAPI Endpoint)
2. 解析请求体 → 标准化 OpenAI 格式
3. 提取参数映射表 (param_mapping)
4. 过滤未识别参数 (白名单机制)
5. 转换为目标 Provider 格式
6. 发送请求到 Provider
7. 解析 Provider 响应
8. 转换为 OpenAI 格式
9. 返回给客户端
```

### 17.4 参数处理分析

```python
# 概念性伪代码（简化自 LiteLLM 源码）
def get_optional_params_anthropic(model, drop_params=False, **kwargs):
    optional_params = {}

    # 已知参数：显式映射
    if "temperature" in kwargs:
        optional_params["temperature"] = kwargs["temperature"]
    if "max_tokens" in kwargs:
        optional_params["max_tokens"] = kwargs["max_tokens"]

    # Anthropic 特有参数
    if "thinking" in kwargs:
        optional_params["thinking"] = kwargs["thinking"]

    # 未识别参数取决于 drop_params 配置
    # drop_params=True → 未知参数被丢弃
    # drop_params=False → 未知参数可能被传递

    return optional_params
```

**问题：**

1. 参数白名单机制：新增参数需手动添加
2. `drop_params` 配置：默认可能丢弃未识别参数
3. 维护成本：每新增参数需更新所有 Adapter

### 17.5 LiteLLM 与 AGRA 对比

| 维度 | LiteLLM | AGRA |
|------|---------|------|
| 核心设计 | 统一到 OpenAI 协议 | 保持协议原生能力 |
| 新增 Provider 成本 | 编写完整 Adapter | Protocol Handler（透传为主） |
| 新增参数成本 | 更新所有 Adapter 映射 | 无需修改（透传） |
| 协议能力保留 | 取决于 Adapter 覆盖度 | PC-5 级别 |
| 治理能力 | 通过 Proxy 提供 | 独立 Governance Layer |
| 扩展性 | 通过 Callbacks | Middleware + Plugin + Policy |

### 17.6 迁移路径

从 LiteLLM 到 AGRA 架构：

1. **分离协议层和治理层**：参数映射移到 Protocol Layer，治理移到 Governance Layer
2. **引入透传模式**：相同协议请求绕过 Adapter
3. **白名单改黑名单**：默认保留所有参数
4. **扩展点标准化**：Callbacks 升级为 Middleware Chain

---

# Part VI: Appendices

## Appendix A: Glossary

| 术语 | 定义 |
|------|------|
| AGRA | AI Gateway Reference Architecture |
| TLG | Transparent Gateway，透明网关 |
| Protocol Preservation | 协议保持，AGRA 第一原则 |
| Governance over Translation | 治理优先于转换，AGRA 第二原则 |
| Transport Transparency | 传输透明，AGRA 第三原则 |
| Extensible by Design | 原生可扩展，AGRA 第四原则 |
| PC-N | 协议兼容性等级 N（0-5） |
| Provider Adapter | 提供方适配器 |
| Middleware Chain | 中间件链 |
| Usage Extractor | 用量提取器 |
| ADR | 架构决策记录 |
| SSE | Server-Sent Events |
| TTFT | Time to First Token |

## Appendix B: Document Index

| 文档 | 标题 | 类型 |
|------|------|------|
| AGRA-0000 | Vision | Specification |
| AGRA-0001 | Architecture | Specification |
| AGRA-0002 | Terminology | Specification |
| AGRA-0003 | Compatibility Model | Specification |
| AGRA-0004 | Governance Model | Specification |
| AGRA-0005 | Observability | Specification |
| AGRA-0006 | Reference Patterns | Specification |
| AGRA-BOOK | White Paper | Book |

## Appendix C: ADR Index

| ADR | 标题 | 状态 |
|-----|------|------|
| ADR-001 | 选择透传作为默认行为 | Accepted |
| ADR-002 | Protocol Layer 与 Governance Layer 解耦 | Accepted |

## Appendix D: Roadmap

### v0.1 — Foundation (Current)

- [x] Vision (AGRA-0000)
- [x] Architecture (AGRA-0001)
- [x] Terminology (AGRA-0002)
- [x] Compatibility Model (AGRA-0003)
- [x] Governance Model (AGRA-0004)
- [x] Observability (AGRA-0005)
- [x] Reference Patterns (AGRA-0006)
- [x] White Paper Chapters 1-17

### v0.2 — Deep Dive

- [ ] Protocol Translation 规范（AGRA-0007）
- [ ] Routing 策略规范（AGRA-0008）
- [ ] Extension 接口规范（AGRA-0009）
- [ ] Conformance Test Suite 规范（AGRA-0010）
- [ ] LiteLLM 源码深度分析（250+ 函数）
- [ ] Provider Matrix（100+ 能力）

### v0.3 — Reference Implementation

- [ ] agra-reference 参考实现
- [ ] agra-tests 兼容性测试套件
- [ ] 性能基准测试

### v1.0 — Stable

- [ ] 所有规范达到 Active 状态
- [ ] 至少两个独立实现通过 Conformance Test
- [ ] 社区治理流程建立

---

## Afterword

AGRA 试图回答一个行业中的根本问题：**在协议多元化的时代，AI Gateway 应该如何设计？**

答案不是「统一所有协议」，也不是「维护无限多的 Adapter」。而是：

> **在保持协议原生能力的基础上，统一治理。**

本书从危机分析出发，定义了四条核心原则、五层架构模型、六级兼容性体系和三种参考模式。它不是一份静态文档，而是一套活的参考架构——它定义的是设计原则和架构边界，而不是某一个具体实现。

AGRA 将继续演进。欢迎贡献。

---

*AGRA Specification License | Version 0.1-draft | Last Updated: 2026-06-26*
