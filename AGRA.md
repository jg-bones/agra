
# AGRA（AI Gateway Reference Architecture）

> **Document ID:** AGRA-0000
> **Version:** 0.1-draft
> **Status:** Draft
> **Title:** AI Gateway Reference Architecture (AGRA)
> **Subtitle:** A Reference Architecture for Building Multi-Protocol AI Gateways

---

## 前言

AGRA（AI Gateway Reference Architecture）是一套构建多协议、Provider 无关 AI Gateway 的参考架构。它的目标不是在协议之上再加一层抽象，而是在保持协议原生能力的前提下，实现统一治理、可观测性和运营控制。

本文档既是设计规范，也是技术白皮书。它定义了一套完整的参考架构，包括设计原则、分层模型、兼容性分级、治理框架、可观测性模型和参考实现模式。

---

# 第一部分：基础

## 第一章 AI Gateway 危机

### 1.1 引言

过去两年，大语言模型（Large Language Model, LLM）的 API 生态发生了根本性变化。

2023 年以前，绝大多数 AI 应用只需要调用单一 Provider，例如 OpenAI 的 Chat Completions API。API 网关（Gateway）的职责也相对简单：统一认证、记录日志、控制流量，并将请求转发给上游模型。

随着越来越多模型厂商进入市场，这种单一 Provider 的模式逐渐演变为多 Provider 接入。为了降低应用开发成本，行业开始采用一种新的架构模式：**Protocol Translation（协议转换）**。

其基本思想是：

> 将所有 Provider 的 API 转换为一种统一协议，通常是 OpenAI Chat Completions API。

在这一阶段，大量 AI Gateway 项目采用了相同的设计思路：

```
Client SDK → Gateway（协议转换） → Provider A（OpenAI 格式）
                                  → Provider B（转为 OpenAI 格式）
                                  → Provider C（转为 OpenAI 格式）
```

这种架构极大降低了多模型接入成本，也推动了 "OpenAI Compatible" 成为事实上的行业标准。

然而，随着模型能力快速演进，这种架构开始暴露越来越多的问题。

### 1.2 协议开始分化

今天的大模型 API 已不再只是「聊天接口」。

不同 Provider 已经开始围绕自身能力设计协议，而不是围绕 OpenAI Chat Completions 兼容。例如：

- **OpenAI** 推出了 Responses API，将文本、图片、音频、工具调用、多轮推理统一到新的响应模型中。
- **Anthropic** 在 Messages API 中引入了 Thinking、Prompt Cache、Computer Use 等原生能力。
- **Gemini** 则围绕 Grounding、Live API、多模态内容组织方式建立了不同于 OpenAI 的协议体系。

这些能力并不是简单增加几个 JSON 字段，而是：**协议本身正在演进。**

协议已经开始承担 Provider 产品能力的表达职责。这意味着：

> **Protocol is Product.**
>
> 协议不再只是网络通信格式，而是模型能力的一部分。

### 1.3 Provider Adapter 的困境

大多数现有 AI Gateway 都采用 Provider Adapter 架构。其生命周期通常如下：

```
新 Provider 能力出现
  → Provider SDK 更新
    → Gateway 发现新能力
      → Gateway 更新参数白名单
        → Gateway 更新 Adapter
          → Gateway 更新 Streaming 处理
            → Gateway 更新 Usage 计算
              → Gateway 更新测试
```

Provider Adapter 的职责通常包括：

- 参数映射：将 Provider 特定参数映射到规范格式
- 参数过滤：根据白名单过滤未知参数
- 默认值填充：补全缺失的默认参数
- Provider 特殊参数转换：处理 Provider 特有的参数语义
- Streaming 转换：统一流式事件格式
- Usage 转换：统一 Token 用量计算
- Error 转换：统一错误码和错误信息

这种设计在 Provider 数量较少、协议变化缓慢时非常有效。但是随着协议持续演进，Gateway 必须不断更新 Adapter 才能支持新的 Provider 能力。

每一次新增协议字段，都意味着：SDK 更新 → Gateway 更新 → Provider Adapter 更新 → 参数白名单更新 → Streaming 更新 → Usage 更新 → 测试更新。

**协议越快演进，Gateway 的维护成本越高。**

### 1.4 一个真实案例：Thinking 参数丢失

下面来看一个真实的问题。客户端使用 OpenAI Python SDK：

```python
from openai import OpenAI

client = OpenAI(base_url="https://my-gateway.example.com/v1")

response = client.chat.completions.create(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": "解释量子计算"}],
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
  "messages": [{"role": "user", "content": "解释量子计算"}],
  "thinking": {
    "type": "enabled",
    "budget_tokens": 4000
  }
}
```

如果该请求直接发送到支持 `thinking` 的 Provider，参数能够正常生效。

然而，当请求经过某些采用 Provider Adapter 的 Gateway 时，Gateway 会根据自身维护的参数白名单重新构造请求对象。如果当前 Gateway 尚未认识 `thinking` 参数，那么该字段可能在请求生命周期中被过滤掉。

最终发送给上游 Provider 的请求变成：

```json
{
  "model": "claude-sonnet-4-5",
  "messages": [{"role": "user", "content": "解释量子计算"}]
}
```

整个过程中：

- HTTP 没有问题；
- SDK 没有问题；
- Provider 也支持该能力；

**问题发生在 Gateway 内部的协议转换阶段。**

这类问题并非某一个项目的缺陷，而是 **Protocol Translation 架构** 在面对快速演进协议时的普遍挑战。

### 1.5 危机的根源

过去几年，AI Gateway 一直围绕一个目标构建：

> **统一协议。**

但今天我们认为，这个目标值得重新审视。

协议越来越多样化，且越来越承载 Provider 的独特能力。如果强行将所有协议压缩到同一个抽象层，Gateway 将不断面临以下矛盾：

1. 新协议能力出现，需要等待 Gateway 适配
2. 不同 Provider 的语义无法完全映射
3. 协议转换逻辑越来越复杂
4. 网关升级速度难以跟上模型能力演进速度

问题并不是 Provider 太多，而是：

> **协议已经成为产品能力的一部分，而不是可以被完全抽象掉的细节。**

因此，AGRA 提出一个新的设计方向：

> AI Gateway 应优先保持协议原生能力（Protocol Preservation），统一治理能力（Governance），而不是统一协议本身。

这一观点构成了 AGRA 的核心设计哲学，也是后续章节提出参考架构的理论基础。

---

## 第二章 AGRA 设计原则

AGRA 凝练为四条核心原则。这四条原则相互关联，共同构成了 AGRA 不同于传统 AI Gateway 的设计哲学。

### Principle 1：Protocol Preservation（协议保持）

> **协议是能力，不是兼容负担。**

AI Gateway 应尽可能保留协议原生能力，而不是把所有协议转换成另一种协议。

这并不意味着 Gateway 不能做任何转换——当客户端和 Provider 使用不同协议时，转换是必要的。但 AGRA 的原则是：**以保持协议原生能力为默认行为，仅在必要时做最小化转换。**

具体实践：

- Gateway 的默认行为是**透传**（pass-through），而不是转换
- 当客户端请求 Anhotropic Messages API 时，Gateway 不应将其转换为 OpenAI 格式后再转回来
- 协议特有的字段（如 `thinking`、`cache_control`、`grounding`）应原样保留，而不是被白名单过滤
- 如果必须做协议转换，应在明确的 Reference Pattern 中定义转换规则（参见 AGRA-0006）

### Principle 2：Governance over Translation（治理优先于转换）

> **网关应该统一治理，而不是统一协议。**

这是 AGRA 区别于现有 AI Gateway 的根本设计选择。

统一的是治理能力：

- Authentication（认证）
- Authorization（授权）
- Routing（路由）
- Rate Limiting（限流）
- Billing（计费）
- Observability（可观测性）

而不是协议细节：

- `thinking` 参数
- `cache_control` 语义
- `grounding` 配置
- MCP 协议交互

治理层（Governance Layer）和协议层（Protocol Layer）是解耦的。这意味着：

- 治理能力的提升不应需要修改协议适配代码
- 协议演进不应影响治理逻辑
- 新增一个 Provider 只需要关注协议适配，不需要重写治理逻辑

### Principle 3：Transport Transparency（传输透明）

> Transport 应尽可能保持透明。

默认原则：

- **不修改 Request Body**：客户端发送的请求体应原样到达 Provider，除非需要在 HTTP Header 层添加追踪信息
- **不修改 Response Body**：Provider 返回的响应体应原样返回给客户端
- **保持 Streaming 透明**：SSE（Server-Sent Events）流应逐帧透传，Gateway 仅做必要的转发和观测
- **最小化 Header 修改**：只在明确需要时（例如认证 Token 注入、Request ID 追踪）才修改 HTTP Header

只有在明确需要时（例如认证、追踪、路由）才进行有限修改。

### Principle 4：Extensible by Design（原生可扩展）

> 所有能力都应通过扩展点实现，而不是修改核心。

AGRA 将 Gateway 的所有增值能力设计为可插拔的扩展点：

- **Middleware**：请求/响应生命周期中的拦截器（如日志、认证）
- **Plugin**：独立的功能模块（如缓存、内容审核）
- **Policy**：声明式规则引擎（如限流策略、路由规则）
- **Router**：可插拔的路由策略（如轮询、权重、延迟优先）
- **Usage Extractor**：可扩展的用量提取器（不同 Provider 的 Token 计数逻辑不同）

核心引擎本身保持简洁和稳定，所有功能通过扩展实现。

---

## 第三章 AGRA 五层模型

这是 AGRA 最核心的架构图。五层模型将 Gateway 的职责清晰地分层，每层有明确的职责边界。

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│  OpenAI SDK · Anthropic SDK · Gemini SDK · REST Client     │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     TRANSPORT LAYER                         │
│  HTTP/2 · gRPC · WebSocket · Server-Sent Events            │
│  Request/Response Passthrough · Streaming Forward           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     PROTOCOL LAYER                          │
│  Protocol Detection · Header Routing · Capability Mapping   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ OpenAI   │  │Anthropic │  │ Gemini   │  ...             │
│  │ Protocol │  │ Protocol │  │ Protocol │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    GOVERNANCE LAYER                         │
│  Auth · Rate Limit · Routing · Billing · Audit             │
│  Middleware Chain · Policy Engine · Plugin System          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   OBSERVABILITY LAYER                       │
│  Logging · Metrics · Tracing · Alerting · Reporting        │
│  Request Lifecycle Tracking · Cost Attribution             │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Client Layer（客户端层）

这是 Gateway 的外部接口。客户端可以使用任何协议对应的官方 SDK 来访问 Gateway。

AGRA 的设计假设是：**客户端不需要引入新的 SDK 或中间件**。开发者继续使用他们熟悉的 OpenAI SDK、Anthropic SDK 或 Gemini SDK，只需将 `base_url` 指向 Gateway。

### 3.2 Transport Layer（传输层）

负责网络传输，核心职责是：

- 接收客户端请求，建立 HTTP/2、gRPC 或 WebSocket 连接
- 管理 SSE（Server-Sent Events）流式传输
- 保持请求体和响应体的完整性
- 在 Header 层注入必要的追踪信息（如 `X-Request-ID`、`X-Trace-ID`）
- 管理连接池和后端连接复用

关键设计决策：**Transport Layer 不解析请求体内容**。它只关心 HTTP 层的元数据。

### 3.3 Protocol Layer（协议层）

负责协议识别和路由。核心职责：

- 根据请求路径和 Header 自动检测协议类型（如 `/v1/chat/completions` → OpenAI 协议，`/v1/messages` → Anthropic 协议）
- 将请求路由到对应的 Protocol Handler
- 维护协议兼容性元数据（参见第四章的兼容性等级）

Protocol Layer 可以包含多个 Protocol Handler，每个 Handler 知道如何处理特定协议的请求。但关键区别在于：**Protocol Handler 的默认行为是透传，而不是转换**。

### 3.4 Governance Layer（治理层）

这是 AGRA 统一治理能力的实现层。所有跨协议的管理功能都在这里实现：

- **Authentication**：验证客户端身份，注入 Provider API Key
- **Authorization**：基于角色或组织的细粒度权限控制
- **Rate Limiting**：多维度限流（用户级、组织级、模型级、Provider 级）
- **Routing**：根据策略选择目标 Provider（轮询、权重、延迟优先、成本优先）
- **Billing**：统一计费和成本归属
- **Audit**：完整的操作审计日志

Governance Layer 通过 Middleware Chain 实现。每个 Middleware 是一个独立的处理单元，可以在请求前、请求后或两者都执行逻辑。

### 3.5 Observability Layer（可观测性层）

贯穿所有层的横切关注点，提供：

- **Logging**：请求和响应的结构化日志
- **Metrics**：延迟、吞吐量、错误率、Token 用量等核心指标
- **Tracing**：分布式追踪，从客户端到 Provider 的完整链路
- **Alerting**：异常检测和自动告警
- **Reporting**：成本报告、用量趋势、SLA 看板

### 3.6 关键设计思想

五层模型最核心的设计思想是：

> **Protocol Layer 和 Governance Layer 是解耦的。**

这意味着：

- 协议演进不影响治理逻辑
- 新增治理能力不需要调整协议适配
- 每一层可以独立演化、独立测试、独立替换
- 新的 Reference Pattern（如 Protocol Translation Gateway）只需要在 Protocol Layer 添加转换逻辑，Governance Layer 完全不变

---

## 第四章 兼容性分级模型

这是 AGRA 最有机会形成行业价值的部分。

### 4.1 问题的本质

目前行业里说「OpenAI Compatible」，实际上缺乏统一定义。

- 有的 Gateway 只兼容了 `/v1/chat/completions` 这一个 Endpoint（Endpoint Compatible）
- 有的兼容了请求/响应结构（Schema Compatible）
- 有的连 Streaming 事件格式都对齐了（Streaming Compatible）
- 有的可以让 OpenAI SDK 无缝替换 base_url（SDK Compatible）
- 但几乎没有 Gateway 能完整保留协议的原生扩展能力（Protocol Native）

这种模糊性导致开发者选型时无法准确评估兼容程度，也无法在 Gateway 之间做横向比较。

### 4.2 AGRA 兼容性等级

AGRA 提出一套 **六级兼容性分级模型**：

| 等级 | 名称 | 含义 |
|------|------|------|
| **PC-0** | HTTP Compatible | 支持 HTTP 与基本 REST 访问 |
| **PC-1** | Endpoint Compatible | 兼容 API 路径与请求方式 |
| **PC-2** | Schema Compatible | 请求/响应结构兼容 |
| **PC-3** | Streaming Compatible | 流式事件兼容 |
| **PC-4** | SDK Compatible | 官方 SDK 可直接使用 |
| **PC-5** | Protocol Native | 保留协议原生扩展能力 |

### 4.3 各级详解

#### PC-0：HTTP Compatible

最低的兼容级别。Gateway 只需提供 HTTP/HTTPS 接口，接受 Web 请求并返回响应。不保证路径、参数或响应格式与任何特定 Provider 一致。

**适用场景：** 自建模型服务的简单代理。

#### PC-1：Endpoint Compatible

兼容特定 Provider 的 API 路径和方法。例如，Gateway 接受 `POST /v1/chat/completions` 请求，但可能不保证请求体或响应体结构与 OpenAI 完全一致。

**适用场景：** 简单的负载均衡代理，客户端需要自行处理参数映射。

#### PC-2：Schema Compatible

请求体和响应体结构与目标 Provider 一致。例如，Gateway 接受符合 OpenAI Chat Completions 格式的请求，返回符合该格式的响应。但可能：

- 不支持 Streaming
- 不支持 `stream_options`
- 不支持 `n > 1`
- 不支持 Function Calling 的完整语义

**适用场景：** 基本的 Chat 场景，不需要流式响应。

#### PC-3：Streaming Compatible

在 PC-2 的基础上，完整支持 SSE（Server-Sent Events）流式响应，流事件格式与目标 Provider 一致。包括：

- `data: [DONE]` 终止标记
- 所有流事件类型（`content_block_start`、`content_block_delta` 等）
- Usage 信息在流结束时的返回

**适用场景：** 需要流式响应的 Chat 和 Completion 场景。

#### PC-4：SDK Compatible

官方 SDK 可以直接使用，只需修改 `base_url`。这意味着：

- 所有标准的 API Endpoint 都兼容
- 请求/响应结构与官方文档一致
- Streaming 完全兼容
- Error 格式一致
- 认证方式兼容（API Key Header）

**适用场景：** 希望无缝替换 Provider Endpoint 的生产环境。

#### PC-5：Protocol Native

最高兼容等级。在 PC-4 的基础上，保留协议的原生扩展能力，包括：

- Provider 特有的参数不会被过滤
- 协议扩展字段（如 `thinking`、`cache_control`、`grounding`）原样透传
- 非标准响应字段保留
- 流式扩展事件保留
- 支持 Provider 特有的 API Endpoint（不仅仅是 Chat Completions）

**适用场景：** 需要完整利用 Provider 所有能力的生产环境，对 Gateway 的透明性有最高要求。

### 4.4 兼容性等级的使用

任何 Gateway 或 Provider 都可以声明自己的兼容等级。例如：

```
MyGateway v2.3.1
- OpenAI Compatibility: PC-4（SDK Compatible）
- Anthropic Compatibility: PC-2（Schema Compatible）
- Gemini Compatibility: PC-1（Endpoint Compatible）
```

这样，开发者可以准确了解 Gateway 对每个 Provider 的支持程度，而不是笼统地说「兼容 OpenAI」。

---

## 第五章 治理模型

### 5.1 治理层架构

AGRA 的 Governance Layer 采用 Middleware Chain（中间件链）模式。每个请求经过 Protocol Layer 识别协议后，进入治理层的处理链：

```
Request → [Auth Middleware] → [Rate Limit Middleware] → [Router Middleware] → [Billing Middleware] → Provider
                                                                                    ↓
Response ← [Audit Middleware] ← [Billing Middleware] ← [Usage Extract Middleware] ← Provider
```

关键原则：

- **每个 Middleware 是独立的**，不依赖其他 Middleware 的内部状态
- **Middleware 可以配置为跳过**（例如内部服务调用跳过 Rate Limit）
- **Middleware 可以按路由规则差异化配置**（例如不同模型的限流策略不同）

### 5.2 认证与授权

#### 认证（Authentication）

AGRA 支持多种认证方式：

- **API Key**：最简单的认证方式，通过 `Authorization: Bearer <key>` Header
- **JWT Token**：用于组织级认证，支持过期和刷新
- **OAuth 2.0**：用于第三方集成
- **mTLS**：用于服务间通信

Gateway 接收到客户端请求后，通过 Auth Middleware 验证客户端身份，然后根据路由规则注入目标 Provider 的 API Key。

```
Client API Key (面向用户)  →  Gateway（Auth Middleware）  →  Provider API Key（面向上游）
```

#### 授权（Authorization）

AGRA 的授权模型基于 RBAC（Role-Based Access Control），核心实体包括：

- **Organization**：组织，拥有多个 API Key
- **User**：用户，属于一个或多个 Organization
- **API Key**：归属于 Organization
- **Role**：角色（Admin、Developer、Viewer）
- **Permission**：细粒度权限（`model:access`、`billing:view`、`rate_limit:override`）

### 5.3 路由策略

AGRA 的路由器（Router）支持多种策略：

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| **Round Robin** | 轮询 | 均衡加载 |
| **Weighted** | 按权重分配 | 部分 Provider 容量更大 |
| **Latency-Aware** | 优先选择低延迟 Provider | 对响应时间敏感 |
| **Cost-Aware** | 优先选择低成本 Provider | 成本控制场景 |
| **Fallback** | 主 Provider 不可用时切换备用 | 高可用 |
| **Capability-Aware** | 根据请求需要的特性选择 Provider | Thinking、Grounding 等特性路由 |

### 5.4 限流模型

AGRA 支持多维度限流：

```
┌──────────────────────────────────────────────┐
│              Rate Limiting Model             │
├──────────────┬───────────┬───────────────────┤
│   Dimension  │  Window   │  Strategy         │
├──────────────┼───────────┼───────────────────┤
│  User        │  Per min  │  Token Bucket     │
│  Org         │  Per day  │  Sliding Window   │
│  Model       │  Per min  │  Leaky Bucket     │
│  Provider    │  Per min  │  Fixed Window     │
│  IP          │  Per sec  │  Token Bucket     │
│  Endpoint    │  Per min  │  Sliding Window   │
└──────────────┴───────────┴───────────────────┘
```

### 5.5 计费与成本

AGRA 的成本模型分为两个层面：

**计费（面向用户）：**

- 按 Token 用量计费
- 按模型差异化定价
- 支持预付费和后付费
- 支持配额管理

**成本追踪（面向运营）：**

- 每个请求的实际 Provider 成本
- 按 Organization / User / Model 维度汇总
- 实时成本看板
- 成本异常告警

---

## 第六章 传输透明性

### 6.1 透明的必要性

在 AGRA 的设计中，Transport Transparency 不是技术偏好，而是架构要求。

当 Gateway 成为系统中唯一接触请求体和响应体的组件时，它对数据完整性的任何假设都可能在未来失效。Provider 随时可能引入新的协议字段，而 Gateway 不应成为这些字段的瓶颈。

### 6.2 实现原则

#### 请求处理

```
Client Request Body → Gateway（不解析） → Provider
                      ↓
             仅提取 HTTP Headers：
               - Authorization
               - Content-Type
               - X-Request-ID
               - 路由相关 Header
```

Gateway 在请求阶段只读取 HTTP Header，不解析 JSON Body。Body 以字节流形式透传。

**例外情况：**

- 需要在 Body 中注入额外字段时（如追踪 ID），仅在明确的配置下执行
- 需要做协议转换时（Protocol Translation Pattern），在 Protocol Layer 中处理
- 需要做内容审核时，通过 Plugin 机制处理，不影响主链路

#### 响应处理

```
Provider Response Body → Gateway（不修改） → Client
                          ↓
                 提取 Observability 数据：
                   - Response Status Code
                   - Response Headers
                   - Latency
                   - Token Usage（from Stream/Response）
```

响应体同样以字节流形式透传。Gateway 通过解析 Stream 事件或响应 Header 来提取观测数据，而不修改响应体本身。

### 6.3 SSE Streaming 的透明传输

SSE（Server-Sent Events）是 AI API 中最常用的流式传输方式。AGRA 对 SSE 的透明传输要求：

1. **逐帧转发**：Provider 发出的每个 SSE 事件，Gateway 都应原样转发给客户端
2. **不缓冲**：不应将多个 SSE 事件合并后再发送（会增加首字延迟）
3. **不修改事件内容**：即使 Gateway 不理解某个事件类型，也应保持原样转发
4. **正确处理 `[DONE]`**：Provider 发出的流结束标记应正确转发

### 6.4 最小化修改原则

AGRA 允许 Gateway 在以下情况修改请求或响应：

| 修改类型 | 何时允许 | 如何修改 |
|---------|---------|---------|
| **注入 Request ID** | 始终 | 添加到 HTTP Header `X-Request-ID` |
| **注入 Trace ID** | 开启 Tracing 时 | 添加到 HTTP Header `X-Trace-ID` |
| **替换 API Key** | 需要 Provider 认证时 | 修改 `Authorization` Header |
| **注入追踪字段到 Body** | 明确配置时 | 在 JSON Body 顶层添加 `_gateway` 字段 |
| **协议转换** | 使用 Translation Pattern 时 | 完整协议映射 |

---

## 第七章 可观测性

### 7.1 可观测性支柱

AGRA 定义了三根可观测性支柱：

```
┌──────────────────────────────────────────────────────┐
│                  OBSERVABILITY                       │
├───────────────┬──────────────────┬──────────────────┤
│    LOGGING    │     METRICS      │     TRACING      │
│   Request/    │  Throughput      │  Distributed     │
│   Response    │  Latency         │  Trace Context   │
│   Audit       │  Error Rate      │  Span Hierarchy  │
│   Structured  │  Token Usage     │  Baggage         │
└───────────────┴──────────────────┴──────────────────┘
```

### 7.2 日志模型

AGRA 的结构化日志包含以下核心字段：

```
{
  "timestamp": "2026-06-26T14:30:00.000Z",
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
    "content_type": "application/json"
  },
  "response": {
    "status_code": 200,
    "latency_ms": 1234,
    "stream": true
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
    "cost_usd": 0.015
  },
  "governance": {
    "route_strategy": "latency-aware",
    "rate_limit_consumed": 1,
    "rate_limit_remaining": 999
  }
}
```

### 7.3 核心指标

| 指标类别 | 指标名称 | 类型 | 说明 |
|---------|---------|------|------|
| **请求** | `gateway_requests_total` | Counter | 总请求数 |
| **请求** | `gateway_requests_by_model` | Counter | 按模型分组 |
| **请求** | `gateway_requests_by_provider` | Counter | 按 Provider 分组 |
| **延迟** | `gateway_latency_ms` | Histogram | 请求总延迟 |
| **延迟** | `gateway_provider_latency_ms` | Histogram | Provider 延迟 |
| **延迟** | `gateway_ttft_ms` | Histogram | Time to First Token |
| **错误** | `gateway_errors_total` | Counter | 错误总数 |
| **错误** | `gateway_provider_errors_total` | Counter | Provider 错误 |
| **用量** | `gateway_tokens_total` | Counter | Token 总量 |
| **用量** | `gateway_cost_usd_total` | Counter | 总成本（美元） |
| **限流** | `gateway_rate_limited_total` | Counter | 被限流次数 |

### 7.4 分布式追踪

AGRA 采用 W3C Trace Context 标准进行分布式追踪：

```
Client → Gateway（创建 Root Span） → Provider（创建 Child Span）
         ├── Span: auth
         ├── Span: rate_limit
         ├── Span: route
         ├── Span: provider_call
         │   ├── Event: request_sent
         │   ├── Event: first_token (for streaming)
         │   └── Event: response_received
         └── Span: billing
```

每个 Span 携带的 Attributes：

- `gateway.protocol`: 使用的协议（openai / anthropic / gemini）
- `gateway.model`: 请求的模型名称
- `gateway.provider`: 上游 Provider
- `gateway.route_strategy`: 路由策略
- `gateway.organization`: 组织 ID
- `ai.model`: Semantic Convention 标准的模型名称
- `ai.usage.input_tokens`: 输入 Token 数
- `ai.usage.output_tokens`: 输出 Token 数

---

## 第八章 扩展系统

### 8.1 扩展点设计

AGRA 通过四个核心扩展点实现功能扩展：

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  MIDDLEWARE │  │   PLUGIN    │  │   POLICY    │  │   ROUTER    │
│  请求/响应   │  │  独立功能    │  │  声明式规则  │  │  路由策略    │
│  拦截器      │  │  模块        │  │  引擎       │  │  实现        │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### 8.2 Middleware 接口

```python
class Middleware:
    """中间件基类"""

    async def on_request(self, context: RequestContext) -> RequestContext:
        """在请求发送到 Provider 之前调用"""
        return context

    async def on_response(self, context: RequestContext, response: Response) -> Response:
        """在响应返回给客户端之前调用"""
        return response

    async def on_error(self, context: RequestContext, error: Exception) -> None:
        """当请求处理出错时调用"""
        pass
```

### 8.3 Plugin 接口

```python
class Plugin:
    """插件基类"""

    name: str
    version: str

    async def setup(self, gateway: Gateway) -> None:
        """插件初始化，注册中间件、路由等"""
        pass

    async def teardown(self) -> None:
        """插件清理"""
        pass
```

### 8.4 Policy 接口

Policy 采用声明式配置，不编写代码：

```yaml
policies:
  - name: "high-cost-model-rate-limit"
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
```

### 8.5 Usage Extractor 接口

不同 Provider 的 Token 计数方式不同，AGRA 将此设计为可扩展的接口：

```python
class UsageExtractor:
    """用量提取器基类"""

    protocol: str  # 协议标识：openai、anthropic、gemini

    def extract_from_response(self, response_body: dict) -> Usage:
        """从非流式响应中提取用量"""
        pass

    def extract_from_stream_event(self, event: dict) -> Optional[Usage]:
        """从流式事件中提取用量"""
        pass

    def calculate_cost(self, usage: Usage, model: str) -> float:
        """计算成本"""
        pass
```

---

## 第九章 参考模式

AGRA 定义了三种参考模式（Reference Patterns）：

### 9.1 Transparent Gateway（TLG，透明网关）

```
Client SDK → Gateway → Provider
              ↓ (透传，不做转换)
           Governance Layer（认证、限流、路由、计费）
           Observability Layer（日志、指标、追踪）
```

TLG 是 AGRA 的核心参考模式，也是推荐的默认模式。它体现了 Protocol Preservation 原则：

- 客户端使用官方 SDK，直接将请求发送到 Gateway
- Gateway 只做治理和观测，不修改协议内容
- 请求体和响应体原样透传
- 协议兼容性等级：**PC-5（Protocol Native）**

**适用场景：**

- 客户端和 Provider 使用相同协议
- 需要统一治理但不想牺牲协议原生能力
- 对透明性和低延迟有高要求

### 9.2 Protocol Translation Gateway（协议转换网关）

```
Client（OpenAI SDK） → Gateway → Provider（Anthropic）
                        ↓
                   Protocol Layer（协议翻译）
                   Governance Layer（治理）
```

当客户端使用的协议与 Provider 不一致时，Gateway 在 Protocol Layer 中进行协议转换：

- 将 OpenAI Chat Completions 请求转换为 Anthropic Messages 请求
- 将 Anthropic 响应转换为 OpenAI Chat Completions 格式
- 协议兼容性等级取决于转换的完整度（PC-1 到 PC-4）

**适用场景：**

- 客户端使用 OpenAI 兼容的 SDK，但后端是 Anthropic 或 Gemini
- 需要平滑迁移 Provider
- 多协议环境中的兼容层

### 9.3 OpenAI-Compatible Gateway（OpenAI 兼容网关）

```
Client（OpenAI SDK） → Gateway → Provider（任何）
                        ↓
                   Protocol Layer（模拟 OpenAI 协议）
                   Governance Layer（治理）
```

这是目前行业中最常见的模式。Gateway 对外暴露标准的 OpenAI API 接口，内部适配各种 Provider：

- 对外：完全兼容 OpenAI Chat Completions API
- 对内：将请求转换为各 Provider 的原生格式
- 风险：参数丢失、能力退化（参见第一章的 Thinking 案例）

**适用场景：**

- 现有应用已经基于 OpenAI SDK 构建
- 需要快速接入多 Provider 但不希望修改应用代码
- 对 Provider 特有能力的依赖较低

### 9.4 模式选择指南

| 场景 | 推荐模式 | 协议兼容等级 |
|------|---------|-------------|
| 使用 Provider 全部能力 | TLG | PC-5 |
| 混合使用多 Provider | TLG（多端点） | PC-5 |
| 迁移 Provider | Protocol Translation | PC-2 ~ PC-4 |
| 统一多 Provider 接口 | OpenAI-Compatible | PC-2 ~ PC-4 |
| 内部工具链 | TLG | PC-5 |

---

## 第十章 LiteLLM 源码分析

### 10.1 概述

LiteLLM 是目前最流行的开源 AI Gateway 之一，也是 Protocol Translation 架构的典型代表。本节分析其核心架构和设计选择，并与 AGRA 的原则进行对比。

### 10.2 LiteLLM 架构概览

LiteLLM 采用典型的 Provider Adapter 架构：

```
Client → LiteLLM Proxy（FastAPI）
           ├── Router（路由层）
           ├── Proxy Server（代理层）
           └── LLM Translation（翻译层）
                 ├── OpenAI Adapter
                 ├── Anthropic Adapter
                 ├── Gemini Adapter
                 └── ... (100+ Provider Adapters)
```

### 10.3 核心流程

**请求处理流程：**

```
1. 接收请求（FastAPI Endpoint）
2. 解析请求体 → 标准化的 OpenAI 格式
3. 提取参数映射表（param_mapping）
4. 过滤未识别参数（白名单机制）
5. 转换为目标 Provider 格式
6. 发送请求到 Provider
7. 解析 Provider 响应
8. 转换为 OpenAI 格式
9. 返回给客户端
```

### 10.4 关键代码分析：参数处理

LiteLLM 使用 `get_optional_params` 系列函数处理参数：

```python
# 概念性伪代码（简化自 LiteLLM 源码）
def get_optional_params_anthropic(
    model: str,
    drop_params: bool = False,
    **kwargs
) -> dict:
    """转换 OpenAI 格式参数到 Anthropic 格式"""

    optional_params = {}

    # 已知参数：显式映射
    if "temperature" in kwargs:
        optional_params["temperature"] = kwargs["temperature"]
    if "max_tokens" in kwargs:
        optional_params["max_tokens"] = kwargs["max_tokens"]
    if "top_p" in kwargs:
        optional_params["top_p"] = kwargs["top_p"]

    # Anthropic 特有参数
    if "thinking" in kwargs:
        optional_params["thinking"] = kwargs["thinking"]

    # 未识别的参数取决于 drop_params 配置
    # 如果 drop_params=True，未知参数会被丢弃
    # 如果 drop_params=False，未知参数可能被传递给 Provider

    return optional_params
```

**问题分析：**

1. **参数白名单机制**：每个 Provider 维护自己的参数映射表。新增参数需要手动添加。
2. **drop_params 配置**：默认行为可能是丢弃未识别参数，导致上一章描述的 Thinking 参数丢失问题。
3. **维护成本**：每新增一个参数，需要在所有 Adapter 中添加映射逻辑。

### 10.5 LiteLLM 与 AGRA 的对比

| 维度 | LiteLLM | AGRA |
|------|---------|------|
| **核心设计** | 统一到 OpenAI 协议 | 保持协议原生能力 |
| **新增 Provider 成本** | 编写完整 Adapter | Protocol Handler（透传为主） |
| **新增参数成本** | 更新所有 Adapter 映射 | 无需修改（透传） |
| **协议能力保留** | 取决于 Adapter 覆盖度 | PC-5 级别 |
| **治理能力** | 通过 LiteLLM Proxy 提供 | 独立的 Governance Layer |
| **扩展性** | 通过 Callbacks | Middleware + Plugin + Policy |
| **适用规模** | 中小规模多 Provider | 大规模企业级 |

### 10.6 从 LiteLLM 到 AGRA 的迁移路径

如果要将 LiteLLM 改造为符合 AGRA 架构：

1. **分离协议层和治理层**：将参数映射移到 Protocol Layer，将认证、限流、计费移到 Governance Layer
2. **引入透传模式**：为使用相同协议的请求提供透传路径，绕过 Adapter
3. **参数白名单改为黑名单**：默认保留所有参数，只在明确需要时过滤特定参数
4. **扩展点标准化**：将 Callbacks 升级为 Middleware Chain

---

## 第十一章 协议深度分析

### 11.1 概述

本章深入分析三大主流 Provider 的 API 协议特征，为 AGRA 的协议处理层提供设计依据。

### 11.2 OpenAI API 协议

**核心端点：**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/chat/completions` | POST | Chat Completions |
| `/v1/responses` | POST | Responses API（新一代） |
| `/v1/embeddings` | POST | 文本嵌入 |
| `/v1/models` | GET | 模型列表 |

**协议特征：**

- 请求/响应采用 JSON 格式
- Streaming 采用 SSE（`data: [DONE]` 终止）
- 通过 `Authorization: Bearer <key>` 认证
- 通过 `extra_body` 支持非标准参数透传（重要：这是 AGRA 友好特性）
- Responses API 统一了文本、图片、音频、工具调用

**关键字段：**

```json
{
  "model": "gpt-5",
  "messages": [{"role": "user", "content": "..."}],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": true,
  "stream_options": {"include_usage": true},
  "tools": [...],
  "tool_choice": "auto",
  "extra_body": {"custom_param": "value"}  // 透传字段
}
```

### 11.3 Anthropic Messages API

**核心端点：**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/messages` | POST | Messages API |
| `/v1/messages/count_tokens` | POST | Token 计数 |

**协议特征：**

- 请求/响应采用 JSON 格式
- 使用 `x-api-key` Header 认证
- 使用 `anthropic-version` Header 指定 API 版本
- Streaming 采用 SSE，事件类型丰富（`message_start`、`content_block_start`、`content_block_delta`、`message_delta`、`message_stop`）
- 扩展能力：Thinking、Prompt Cache、Computer Use、Citations

**关键字段：**

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 4096,
  "temperature": 0.7,
  "thinking": {
    "type": "enabled",
    "budget_tokens": 4000
  },
  "system": [
    {"type": "text", "text": "You are a helpful assistant."},
    {"type": "text", "text": "Guideline 2...", "cache_control": {"type": "ephemeral"}}
  ],
  "tools": [...],
  "stream": true
}
```

**重要设计：** Anthropic 的 `system` 参数是数组形式，每个元素可以设置独立的 `cache_control`。这与 OpenAI 的 `system` 字段（简单字符串）完全不同，强行转换会导致功能丢失。

### 11.4 Gemini API

**核心端点：**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1beta/models/{model}:generateContent` | POST | 内容生成 |
| `/v1beta/models/{model}:streamGenerateContent` | POST | 流式内容生成 |
| `/v1beta/models/{model}:countTokens` | POST | Token 计数 |

**协议特征：**

- 请求/响应采用 JSON 格式
- 使用 `x-goog-api-key` 或 OAuth 2.0 认证
- Streaming 采用 SSE 或 gRPC
- 扩展能力：Grounding（Google Search）、Code Execution、Live API、Controlled Generation
- `contents` 和 `parts` 结构不同于 OpenAI 的 `messages`

**关键字段：**

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
  "tools": [{
    "googleSearch": {}
  }],
  "safetySettings": [...]
}
```

### 11.5 协议差异矩阵

| 能力 | OpenAI | Anthropic | Gemini |
|------|--------|-----------|--------|
| 文本对话 | ✓ | ✓ | ✓ |
| 流式响应 | SSE | SSE | SSE + gRPC |
| 工具调用 | Function Calling | Tool Use | Function Calling |
| 多模态 | 图片、音频 | 图片、PDF | 图片、视频、音频 |
| 推理/思考 | o-series（独立模型） | Thinking（参数控制） | Thinking（参数控制） |
| 缓存 | Prompt Caching（自动） | Prompt Cache（显式） | Context Caching（显式） |
| 搜索增强 | 内置于 Responses API | 无原生支持 | Grounding（Google Search） |
| 代码执行 | 内置于 Responses API | Computer Use | Code Execution |
| 实时通信 | Realtime API（WebSocket） | 无原生支持 | Live API（WebSocket） |
| 参数透传 | `extra_body` | 无（需 SDK 支持） | 无（需 SDK 支持） |

### 11.6 对 AGRA 设计的启示

1. **`extra_body` 是关键能力**：OpenAI SDK 的 `extra_body` 机制是实现 Protocol Preservation 的重要工具。AGRA 应优先支持并保护该机制。
2. **认证方式不统一**：需要独立的 Auth Middleware 抽象不同 Provider 的认证方式。
3. **Streaming 事件格式不统一**：TLG 模式下不需要转换，但在 Protocol Translation 模式下需要完整的 SSE 事件映射。
4. **协议字段语义不可通约**：Anthropic 的 `system`（数组）和 OpenAI 的 `system`（字符串）本质不同，强行映射会丢失信息。这强化了 AGRA 的 Protocol Preservation 原则。

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| **AGRA** | AI Gateway Reference Architecture，AI 网关参考架构 |
| **TLG** | Transparent Gateway，透明网关，AGRA 的核心参考模式 |
| **Protocol Preservation** | 协议保持，AGRA 的第一原则：保持协议原生能力 |
| **Governance Layer** | 治理层，AGRA 五层模型中的第四层 |
| **Protocol Layer** | 协议层，AGRA 五层模型中的第三层 |
| **PC-N** | Protocol Compatibility Level N，协议兼容性等级 |
| **SSE** | Server-Sent Events，服务器推送事件，AI API 流式传输标准 |
| **Provider** | 模型服务提供方，如 OpenAI、Anthropic、Google 等 |
| **Provider Adapter** | 提供方适配器，传统 AI Gateway 中负责协议转换的组件 |
| **Middleware Chain** | 中间件链，AGRA 治理层的实现模式 |
| **Usage Extractor** | 用量提取器，从请求/响应中提取 Token 用量的组件 |
| **ADR** | Architecture Decision Record，架构决策记录 |

### B. 文档体系

| 文档编号 | 标题 | 说明 |
|----------|------|------|
| AGRA-0000 | Vision | 为什么需要 AI Gateway Reference Architecture |
| AGRA-0001 | Architecture | 整体架构（五层模型） |
| AGRA-0002 | Terminology | 统一术语 |
| AGRA-0003 | Compatibility Model | 兼容性分级模型（PC-0 到 PC-5） |
| AGRA-0004 | Governance Model | 统一治理能力 |
| AGRA-0005 | Observability | 日志、指标、Tracing |
| AGRA-0006 | Reference Patterns | TLG、Protocol Translation、OpenAI Compatible |

### C. GitHub 仓库结构

```
agra/
├── agra-spec/          # AGRA 规范文档
│   ├── AGRA-0000-vision.md
│   ├── AGRA-0001-architecture.md
│   ├── AGRA-0002-terminology.md
│   ├── AGRA-0003-compatibility.md
│   ├── AGRA-0004-governance.md
│   ├── AGRA-0005-observability.md
│   └── AGRA-0006-reference-patterns.md
├── agra-book/          # AGRA 技术白皮书
│   ├── AGRA.md
│   ├── diagrams/
│   └── appendices/
├── agra-reference/     # 参考实现
│   ├── gateway/        # Gateway 核心
│   ├── middleware/     # 内置 Middleware
│   ├── plugins/        # 内置 Plugin
│   └── protocols/      # Protocol Handler
└── agra-tests/         # 协议兼容性测试套件
    ├── conformance/    # 兼容性测试
    └── benchmarks/     # 性能基准测试
```

### D. ADR 记录

#### ADR-001：选择透传作为默认行为

**状态：** Accepted

**背景：** 传统 AI Gateway（如 LiteLLM）将协议转换作为默认行为。AGRA 面临一个关键架构决策：默认行为应该是转换还是透传。

**决策：** 采用透传作为默认行为。

**理由：**

1. 协议分化趋势不可逆，转换的维护成本持续增长
2. 透传保证了 PC-5 级别的协议兼容性
3. 透传的性能更好（无序列化/反序列化开销）
4. 转换可以在 Protocol Layer 中作为可选功能提供

**后果：**

- Protocol Handler 的默认实现更简单
- 降低了新增 Provider 的成本
- 转换模式需要显式配置，避免意外参数丢失

#### ADR-002：Protocol Layer 和 Governance Layer 解耦

**状态：** Accepted

**背景：** 传统架构中，治理逻辑（认证、限流、计费）和协议逻辑（参数映射、格式转换）耦合在一起。

**决策：** 将 Protocol Layer 和 Governance Layer 设计为独立的、解耦的层。

**理由：**

1. 协议演进不应影响治理逻辑
2. 治理能力增强不应需要修改协议适配
3. 独立测试和部署
4. 允许未来替换任何一个层而不影响另一个

**后果：**

- 架构增加了一层抽象
- 需要明确定义层间接口
- Governance Layer 不依赖协议细节

---

## 后记

AGRA 试图回答一个行业中的根本问题：**在协议多元化的时代，AI Gateway 应该如何设计？**

答案不是「统一所有协议」，也不是「维护无限多的 Adapter」。而是：

> 在保持协议原生能力的基础上，统一治理。

本书从危机分析出发，定义了四条核心原则、五层架构模型、六级兼容性体系和三种参考模式。它不是一份静态文档，而是一套活的参考架构——它定义的是设计原则和架构边界，而不是某一个具体实现。

AGRA 将继续演进。欢迎贡献。

---

*本文档采用 AGRA Specification License。*
*Version: 0.1-draft | Last Updated: 2026-06-26*
