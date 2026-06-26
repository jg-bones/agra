# AGRA（AI Gateway Reference Architecture）

> **Document ID:** AGRA-0000
> **Version:** 0.1-draft
> **Status:** Draft
> **Title:** AI Gateway Reference Architecture (AGRA)
> **Subtitle:** A Reference Architecture for Building Multi-Protocol AI Gateways

---

## 项目起源

> 以下内容完整还原了与 ChatGPT 的对话过程，包括 ChatGPT 给出的所有建议和方案。

ChatGPT 认为 **AGRA（AI Gateway Reference Architecture）** 比 TLG 更有生命力。TLG 可以是 AGRA 的第一个 Reference Pattern，就像 MVC 是一种架构模式，而不是整个软件工程。

---

## AGRA 项目定义

> A reference architecture for building multi-protocol, provider-independent AI gateways.

**一句话使命（Mission）：**

> AGRA defines how to build AI gateways that preserve protocol-native capabilities while providing unified governance, observability, and operational control.

**中文版：**

> AGRA 定义了一套构建多协议、Provider 无关 AI Gateway 的参考架构，在保持协议原生能力的前提下，实现统一治理、可观测性和运营能力。

---

## AGRA 的边界（Scope）

> 这是整个项目最重要的部分之一。

### AGRA 要解决的问题

- 多协议接入（OpenAI、Anthropic、Gemini 等）
- 多 Provider 路由
- 认证与授权
- 限流与配额
- 成本统计与计费
- 可观测性（Logging、Metrics、Tracing）
- 请求生命周期管理
- 插件扩展机制
- 协议兼容性评估

### AGRA 不解决的问题

- 不重新设计模型 API
- 不统一所有 Provider 的参数
- 不隐藏 Provider 的原生能力
- 不替代 SDK
- 不规定模型推理实现

> 这点非常重要，因为它让 AGRA 保持在 **架构层**，而不是协议层。

---

## AGRA 的核心理念

> ChatGPT 建议把它凝练为四条原则，而不是很多零散原则。

### Principle 1：Protocol Preservation

> **协议是能力，不是兼容负担。**

AI Gateway 应尽可能保留协议原生能力，而不是把所有协议转换成另一种协议。

### Principle 2：Governance over Translation

> **网关应该统一治理，而不是统一协议。**

统一的是：

- Authentication
- Authorization
- Routing
- Rate Limiting
- Billing
- Observability

而不是：

- thinking
- cache_control
- grounding
- MCP

### Principle 3：Transport Transparency

Transport 应尽可能保持透明。

默认原则：

- 不修改 Request Body
- 不修改 Response Body
- 保持 Streaming 透明
- 最小化 Header 修改

只有在明确需要时（例如认证、追踪、路由）才进行有限修改。

### Principle 4：Extensible by Design

所有能力都应通过扩展点实现，而不是修改核心。

例如：

- Middleware
- Plugin
- Policy
- Router
- Usage Extractor

---

## AGRA 的五层模型

> 这是整本书最核心的架构图。

```
Application
│
SDK / HTTP Client
│
Protocol Layer
┌────────────┬────────────┬────────────┐
│            │            │
OpenAI    Anthropic     Gemini
│            │            │
└────────────┴────────────┘
│
Transport Layer
│
Governance Layer
┌──────────┬──────────┬──────────┬──────────┐
│  Auth    │ Routing  │ Billing  │ Metrics  │
└──────────┴──────────┴──────────┴──────────┘
│
Provider Layer
│
Model API
```

> 这里有一个关键思想：
>
> **Protocol Layer 和 Governance Layer 是解耦的。**
>
> 这是我认为区别于很多现有网关的重要设计点。

---

## AGRA 文档体系

> ChatGPT 建议采用类似 RFC 的编号体系。

| 文档编号 | 标题 | 说明 |
|----------|------|------|
| AGRA-0000 | Vision | 为什么需要 AI Gateway Reference Architecture |
| AGRA-0001 | Architecture | 整体架构 |
| AGRA-0002 | Terminology | 统一术语 |
| AGRA-0003 | Compatibility Model | 定义兼容性等级 |
| AGRA-0004 | Governance Model | 统一治理能力 |
| AGRA-0005 | Observability | 日志、指标、Tracing |
| AGRA-0006 | Reference Patterns | 包括：Transparent Gateway（TLG）、Protocol Translation Gateway、OpenAI-Compatible Gateway |

---

## 原创内容：Compatibility Levels（兼容性分级模型）

> ChatGPT 认为：这是 AGRA 最有机会形成行业价值的部分。
>
> 目前行业里说 "OpenAI Compatible"，实际上缺乏统一定义。

AGRA 提出一个 **兼容性分级模型**：

| 等级 | 名称 | 含义 |
|------|------|------|
| PC-0 | HTTP Compatible | 支持 HTTP 与基本 REST 访问 |
| PC-1 | Endpoint Compatible | 兼容 API 路径与请求方式 |
| PC-2 | Schema Compatible | 请求/响应结构兼容 |
| PC-3 | Streaming Compatible | 流式事件兼容 |
| PC-4 | SDK Compatible | 官方 SDK 可直接使用 |
| PC-5 | Protocol Native | 保留协议原生扩展能力 |

这样，任何 Gateway 或 Provider 都可以声明自己的兼容等级，而不是笼统地说"兼容 OpenAI"。

---

## 第一阶段的里程碑

> ChatGPT 建议接下来先完成 **AGRA Foundation v0.1**，包括：

- Project Charter（项目章程）
- Mission & Scope（使命与边界）
- Terminology（术语）
- Design Principles（设计原则）
- Layered Architecture（分层架构）
- Compatibility Model（兼容性模型）
- Governance Model（治理模型）

> 完成这一部分后，再进入正文（行业分析、LiteLLM 源码分析、Transparent Gateway 模式等）。这样整个项目的基础会非常稳固，也便于后续持续扩展。

---

# 第一章 AI Gateway Crisis（AI Gateway 危机）

> 以下为 ChatGPT 正式开始写作的第一章内容。
>
> ChatGPT 表示："好，我们从现在开始 **不讨论**，**开始写**。"
>
> "我不会一章一章在聊天里零散输出。这样最后一定会风格不一致、术语混乱、前后矛盾。我们按真正写书的方式来。"

---

**Document ID:** AGRA-0000
**Version:** 0.1-draft
**Status:** Draft

**Title**

> AI Gateway Reference Architecture (AGRA)

**Subtitle**

> A Reference Architecture for Building Multi-Protocol AI Gateways

---

## 1.1 引言

过去两年，大语言模型（Large Language Model，LLM）的 API 生态发生了根本性的变化。

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
▼
Anthropic    Gemini    DeepSeek    Azure OpenAI    ...
```

这种架构极大降低了多模型接入成本，也推动了 "OpenAI Compatible" 成为事实上的行业标准。

然而，随着模型能力快速演进，这种架构开始暴露越来越多的问题。

## 1.2 协议开始分化

今天的大模型 API 已不再只是 "聊天接口"。

不同 Provider 已经开始围绕自身能力设计协议，而不是围绕 OpenAI Chat Completions 兼容。例如：

OpenAI 推出了 Responses API，将文本、图片、音频、工具调用、多轮推理统一到新的响应模型中。

Anthropic 在 Messages API 中引入了 Thinking、Prompt Cache、Computer Use 等原生能力。

Gemini 则围绕 Grounding、Live API、多模态内容组织方式建立了不同于 OpenAI 的协议体系。

这些能力并不是简单增加几个 JSON 字段，而是：

**协议本身正在演进。**

协议已经开始承担 Provider 产品能力的表达职责。这意味着：

> **Protocol is Product.**

协议不再只是网络通信格式，而是模型能力的一部分。

## 1.3 Provider Adapter 的困境

大多数现有 AI Gateway 都采用 Provider Adapter 架构。其生命周期通常如下：

```
HTTP Request
│
▼
Gateway
│
▼
Parse Request
│
▼
Normalize Parameters
│
▼
Provider Adapter
│
▼
Provider Request
```

Provider Adapter 的职责通常包括：

- 参数映射
- 参数过滤
- 默认值填充
- Provider 特殊参数转换
- Streaming 转换
- Usage 转换
- Error 转换

这种设计在 Provider 数量较少、协议变化缓慢时非常有效。

但是随着协议持续演进，Gateway 必须不断更新 Adapter 才能支持新的 Provider 能力。每一次新增协议字段，都意味着：

- SDK 更新
- Gateway 更新
- Provider Adapter 更新
- 参数白名单更新
- Streaming 更新
- Usage 更新
- 测试更新

协议越快演进，Gateway 的维护成本越高。

## 1.4 一个真实案例：Thinking 参数丢失

下面来看一个真实的问题。客户端使用 OpenAI Python SDK：

```python
client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[
        {
            "role": "user",
            "content": "9.11 和 9.8 哪个更大？"
        }
    ],
    extra_body={
        "thinking": {
            "type": "disabled"
        }
    }
)
```

OpenAI SDK 会将 `extra_body` 展开到请求体顶层，因此实际发送的 HTTP Body 为：

```json
{
    "model": "deepseek-v4-pro",
    "messages": [
        {
            "role": "user",
            "content": "9.11 和 9.8 哪个更大？"
        }
    ],
    "thinking": {
        "type": "disabled"
    }
}
```

如果该请求直接发送到支持 `thinking` 的 Provider，参数能够正常生效。

然而，当请求经过某些采用 Provider Adapter 的 Gateway 时，Gateway 会根据自身维护的参数白名单重新构造请求对象。如果当前 Gateway 尚未认识 `thinking` 参数，那么该字段可能在请求生命周期中被过滤掉。

最终发送给上游 Provider 的请求变成：

```json
{
    "model": "deepseek-v4-pro",
    "messages": [
        {
            "role": "user",
            "content": "9.11 和 9.8 哪个更大？"
        }
    ]
}
```

整个过程中：

- HTTP 没有问题；
- SDK 没有问题；
- Provider 也支持该能力；

问题发生在 Gateway 内部的协议转换阶段。

这类问题并非某一个项目的缺陷，而是 **Protocol Translation 架构** 在面对快速演进协议时的普遍挑战。

## 1.5 危机的根源

过去几年，AI Gateway 一直围绕一个目标构建：

> **统一协议。**

但今天我们认为，这个目标值得重新审视。

协议越来越多样化，且越来越承载 Provider 的独特能力。如果强行将所有协议压缩到同一个抽象层，Gateway 将不断面临以下矛盾：

- 新协议能力出现，需要等待 Gateway 适配；
- 不同 Provider 的语义无法完全映射；
- 协议转换逻辑越来越复杂；
- 网关升级速度难以跟上模型能力演进速度。

问题并不是 Provider 太多，而是：

> **协议已经成为产品能力的一部分，而不是可以被完全抽象掉的细节。**

因此，AGRA 提出一个新的设计方向：

> **AI Gateway 应优先保持协议原生能力（Protocol Preservation），统一治理能力（Governance），而不是统一协议本身。**

这一观点构成了 AGRA 的核心设计哲学，也是后续章节提出参考架构的理论基础。

> **这是我们这本书的第一章。**

---

## 写作标准（ChatGPT 的建议）

> ChatGPT 建议以后按以下标准推进：

- **每章 3000～6000 字**
- **不是聊天，而是出版质量**
- **有完整论证**
- **有架构图**
- **有真实案例（包括我们之前讨论的 LiteLLM、thinking、extra_body 等）**
- **引用官方协议和源码作为事实依据**
- **最后每章都有 ADR（Architecture Decision Record）和本章总结**

> 按照这个节奏，大约 **30～40 章**，最终会形成一本约 **10 万字** 的完整 AGRA 白皮书。

---

## 整体写作方案（ChatGPT 的建议）

> 当用户问"直接写完可以吗，写到一个文档里也行"时，ChatGPT 给出了以下方案。

可以，但是 **不能一次性完成**，原因是模型单次输出长度有限，而不是文档形式的问题。

你要的内容规模大约是：

- **30~40 章**
- **100,000~150,000 字**
- Mermaid 架构图约 80~100 张
- 协议矩阵约 50 张
- LiteLLM 源码分析约 200 多个函数
- OpenAI / Anthropic / Gemini 协议分析
- ADR / RFC / Appendix

这个体量远远超过一次回复能生成的 Token 上限。

### 建议的方式：一次聊天，持续生成一个完整文档

也就是说，不是零散的聊天，而是维护一个 `AGRA.md`，一直往里面写，最终得到十几万字。

然后导出为 PDF、DOCX、GitBook、MkDocs。

### 效率最高的做法

整个项目维护一份文档：

```
AGRA.md
```

目录例如：

```markdown
# AI Gateway Reference Architecture
## Preface
## Chapter 1
...
## Chapter 35
...
## Appendix A
...
## Appendix I
```

以后每次都是：

> 继续写 AGRA.md

而不是：

> 再来一章。

这样：

- 风格一致
- 章节自动编号
- 自动引用
- 前后术语统一
- 后面可以统一排版

这也是写技术书最常见的方式。

---

## 交付物升级建议（ChatGPT 的建议）

> ChatGPT 表示："我不想只给你 Markdown。我建议最终直接交付一个完整的项目目录。"

```
AGRA/
├── README.md
├── book/
│   └── AGRA.md          （完整版）
├── diagrams/
│   └── *.mmd
├── tables/
│   ├── provider_matrix.csv
│   └── sdk_matrix.csv
├── appendix/
│   └── protocol_matrix.csv
└── references/
    └── bibliography.md
```

以后：GitHub、GitBook、MkDocs 全部自动生成。

---

## 开发模式（ChatGPT 的建议）

以后你只需要一句话：

> **继续 AGRA**

我就继续往同一个文档写。

不用重复提示。不用重新规划。不用重新起草。直到写完。

---

## 最终目标（ChatGPT 的建议）

ChatGPT 希望把它做到这样的规模：

| 内容 | 预计规模 |
|------|----------|
| 正文 | 10~12 万字 |
| Mermaid 图 | 100+ |
| 架构图 | 50+ |
| 协议矩阵 | 60+ |
| SDK 对照 | 20+ |
| LiteLLM 源码分析 | 250+ 个函数 |
| Provider Matrix | 100+ 项能力 |
| ADR | 20+ |
| RFC | 15+ |
| Appendix | 10 个 |

> **这已经不是一本普通电子书，而是一套完整的 AI Gateway 参考架构文档。**

---

## 工程目标：GitHub 仓库结构（ChatGPT 的建议）

> ChatGPT 建议增加一个工程目标：不要只写文档，而是同步建立一个 GitHub 仓库结构。

- `agra-spec`：规范（Specification）
- `agra-book`：白皮书（Book）
- `agra-reference`：参考实现（Reference Implementation）
- `agra-tests`：协议兼容测试（Conformance Test Suite）

> 这样文档和代码同步演进，最终形成一个真正的开源项目，而不仅是一份静态报告。我认为，这样投入的时间会更值得，也更容易持续维护和吸引社区参与。

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| **AGRA** | AI Gateway Reference Architecture，AI 网关参考架构 |
| **TLG** | Transparent Gateway，透明网关，AGRA 的第一个 Reference Pattern |
| **Protocol Preservation** | 协议保持，AGRA 的第一原则：协议是能力，不是兼容负担 |
| **Governance over Translation** | 治理优先于转换，AGRA 的第二原则：统一治理，而不是统一协议 |
| **Transport Transparency** | 传输透明，AGRA 的第三原则：不修改请求/响应体 |
| **Extensible by Design** | 原生可扩展，AGRA 的第四原则：通过扩展点实现能力 |
| **Protocol Layer** | 协议层，五层模型中的协议处理层 |
| **Governance Layer** | 治理层，五层模型中的统一治理层 |
| **PC-N** | Protocol Compatibility Level N，协议兼容性等级（PC-0 到 PC-5） |
| **Provider Adapter** | 提供方适配器，传统 AI Gateway 中负责协议转换的组件 |
| **Protocol Translation** | 协议转换，将所有 Provider API 转换为统一协议的架构模式 |
| **SSE** | Server-Sent Events，服务器推送事件 |
| **ADR** | Architecture Decision Record，架构决策记录 |

### B. 文档体系

| 文档编号 | 标题 | 说明 |
|----------|------|------|
| AGRA-0000 | Vision | 为什么需要 AI Gateway Reference Architecture |
| AGRA-0001 | Architecture | 整体架构 |
| AGRA-0002 | Terminology | 统一术语 |
| AGRA-0003 | Compatibility Model | 定义兼容性等级 |
| AGRA-0004 | Governance Model | 统一治理能力 |
| AGRA-0005 | Observability | 日志、指标、Tracing |
| AGRA-0006 | Reference Patterns | TLG / Protocol Translation / OpenAI-Compatible |

### C. GitHub 仓库结构（ChatGPT 建议的最终形态）

```
agra/
├── agra-spec/          # 规范（Specification）
│   ├── AGRA-0000-vision.md
│   ├── AGRA-0001-architecture.md
│   ├── AGRA-0002-terminology.md
│   ├── AGRA-0003-compatibility.md
│   ├── AGRA-0004-governance.md
│   ├── AGRA-0005-observability.md
│   └── AGRA-0006-reference-patterns.md
├── agra-book/          # 白皮书（Book）
│   ├── book/
│   │   └── AGRA.md     # 完整版
│   ├── diagrams/
│   │   └── *.mmd
│   ├── tables/
│   │   ├── provider_matrix.csv
│   │   └── sdk_matrix.csv
│   ├── appendix/
│   │   └── protocol_matrix.csv
│   └── references/
│       └── bibliography.md
├── agra-reference/     # 参考实现（Reference Implementation）
└── agra-tests/         # 协议兼容测试（Conformance Test Suite）
```

### D. AGRA Foundation v0.1 里程碑清单

> ChatGPT 建议的第一阶段交付物：

- [ ] Project Charter（项目章程）
- [ ] Mission & Scope（使命与边界）
- [ ] Terminology（术语）
- [ ] Design Principles（设计原则）
- [ ] Layered Architecture（分层架构）
- [ ] Compatibility Model（兼容性模型）
- [ ] Governance Model（治理模型）

### E. 对话来源

本文档还原自与 ChatGPT 的对话：
https://chatgpt.com/share/6a3df6d3-7354-83ec-94d3-c40f93e08668

---

*Version: 0.1-draft | Last Updated: 2026-06-26*
